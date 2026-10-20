"""Run Pipecat voice sessions for browser and Twilio WebSocket transports."""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import suppress
from typing import Optional

from fastapi import WebSocket
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.frames.frames import ErrorFrame, LLMRunFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.serializers.base_serializer import FrameSerializer
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)
from src.call_failure import CallFailureState, classify_pipeline_failure
from src.call_tracking import (
    end_call_tracking,
    mark_call_answered,
    renew_call_lease,
    start_call_tracking,
)
from src.recording import RecordingAudioTap, RecordingCoordinator
from src.recording_policy import should_record_agent_call
from src.serialization.browser_protobuf import BrowserWebSocketFrameSerializer
from src.session_setup import prepare_voice_session
from src.telemetry import VoiceTelemetryObserver

from shared.config import settings
from shared.observability.signals import correlation, event
from shared.observability.signals import failure as telemetry_failure
from shared.observability.signals import operation
from shared.observability.voice import (
    annotate_speech_configuration,
    observe_call,
    observe_tool,
)
from shared.voice_agents.voice_session_service import VoiceSessionClaims

logger = logging.getLogger(__name__)
_GREETING_INSTRUCTION = "Greet the user warmly and ask how you can help."


async def _cancel_pipeline_after(
    task: PipelineTask,
    duration_seconds: int,
    session_id: str,
) -> None:
    """Cancel a pipeline when a bounded demo call reaches its time limit."""
    try:
        await asyncio.sleep(duration_seconds)
    except asyncio.CancelledError:
        return
    logger.info(
        "Demo call duration limit reached session_id=%s duration_seconds=%s",
        session_id,
        duration_seconds,
    )
    await task.cancel()


async def _close_mcp_clients(clients: list[object]) -> None:
    """Close every session-owned MCP client without masking teardown errors."""
    for client in clients:
        try:
            await client.close()
        except Exception:  # noqa: BLE001 - cleanup must attempt all clients
            logger.exception("Failed to close MCP client")


async def _maintain_call_lease(
    task: PipelineTask,
    call_log_id: str,
    session_id: str,
    failure_state: CallFailureState,
) -> None:
    """Stop provider work promptly if its tracked lease can no longer be renewed."""
    while True:
        await asyncio.sleep(20)
        try:
            renewed = await asyncio.wait_for(
                renew_call_lease(call_log_id, session_id), timeout=8
            )
        except Exception:
            renewed = False
        if not renewed:
            failure_state.capture(classify_pipeline_failure("CALL_STORAGE_UNAVAILABLE"))
            await task.cancel()
            return


@observe_call
async def run_bot(
    websocket: WebSocket,
    claims: VoiceSessionClaims,
    *,
    serializer: Optional[FrameSerializer] = None,
    max_call_duration_seconds: Optional[int] = None,
) -> None:
    """Run one authenticated Pipecat voice session.

    The selected agent preset determines whether this builds Google/OpenAI
    realtime speech or a modular Deepgram → OpenAI/Cerebras → Cartesia
    pipeline. Browser protobuf and Twilio serializers share the same transport
    and assembly path. A positive ``max_call_duration_seconds`` starts at
    transport connection time and cancels the pipeline when reached.
    """
    frame_serializer = serializer or BrowserWebSocketFrameSerializer()
    with operation("voice.setup"):
        bundle = await prepare_voice_session(claims)
        annotate_speech_configuration(bundle.speech_config)
    call_log_id = None
    try:
        if bundle.agent.organization_id:
            call_log_id = await start_call_tracking(
                session_id=claims.session_id,
                call_sid=claims.call_sid,
                organization_id=bundle.agent.organization_id,
                agent_id=bundle.agent.id,
                source_type=claims.source_type,
                source_url=claims.source_url,
                source_domain=claims.source_domain,
            )
        if not call_log_id:
            raise RuntimeError("CALL_STORAGE_UNAVAILABLE")
    finally:
        if not call_log_id:
            await _close_mcp_clients(bundle.tools.mcp_clients)
    transport = FastAPIWebsocketTransport(
        websocket=websocket,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=False,
            serializer=frame_serializer,
        ),
    )
    context = LLMContext(tools=ToolsSchema(standard_tools=bundle.tools.schemas))
    if bundle.speech.mode == "pipeline":
        user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
            context,
            user_params=LLMUserAggregatorParams(vad_analyzer=bundle.speech.vad),
        )
    else:
        user_aggregator, assistant_aggregator = LLMContextAggregatorPair(context)

    llm = bundle.speech.llm
    for name, handler in bundle.tools.handlers.items():
        llm.register_function(name, observe_tool(name, handler))

    recording_coordinator: Optional[RecordingCoordinator] = None
    caller_recording_tap: Optional[RecordingAudioTap] = None
    agent_recording_tap: Optional[RecordingAudioTap] = None
    correlation.set(
        {
            **correlation.get(),
            "call_id": call_log_id or "",
            "organization_id": str(bundle.agent.organization_id or ""),
        }
    )
    trace.get_current_span().set_attributes(correlation.get())
    event("call.tracking_started", outcome="success" if call_log_id else "error")

    recording_enabled = should_record_agent_call(
        bundle.agent,
        global_enabled=settings.voice_recording_enabled,
        tee_enabled=os.getenv("VOICE_RECORDING_TEE", "false").lower() == "true",
    )
    if recording_enabled and call_log_id and bundle.agent.organization_id:
        try:
            recording_coordinator = RecordingCoordinator(
                call_log_id=call_log_id,
                organization_id=bundle.agent.organization_id,
            )
            await recording_coordinator.prepare()
            caller_recording_tap = RecordingAudioTap(
                recording_coordinator,
                track="caller",
            )
            agent_recording_tap = RecordingAudioTap(
                recording_coordinator,
                track="agent",
            )

        except Exception:  # noqa: BLE001 - recording cannot block a call
            logger.exception(
                "Recording setup failed for session %s; continuing without audio",
                claims.session_id,
            )
            event("recording.setup_failed", outcome="error")
            recording_coordinator = None
            caller_recording_tap = None
            agent_recording_tap = None

    output_processor = transport.output()

    processors = [transport.input()]
    if caller_recording_tap:
        # Capture caller audio before it can be delayed by model processing or
        # output playback pacing.
        processors.append(caller_recording_tap)
    if bundle.speech.mode == "pipeline":
        processors.extend([bundle.speech.stt, user_aggregator, llm, bundle.speech.tts])
    else:
        processors.extend([user_aggregator, llm])
    if agent_recording_tap:
        # Capture generated agent audio before transport playback pacing.
        processors.append(agent_recording_tap)
    processors.extend([output_processor, assistant_aggregator])
    task = PipelineTask(
        Pipeline(processors),
        params=PipelineParams(
            allow_interruptions=True, enable_metrics=True, enable_usage_metrics=True
        ),
        observers=[VoiceTelemetryObserver()],
    )
    failure_state = CallFailureState()
    duration_task: Optional[asyncio.Task[None]] = None

    @task.event_handler("on_pipeline_error")
    def on_pipeline_error(_task: PipelineTask, frame: ErrorFrame) -> None:
        """Capture the first Pipecat pipeline error before teardown begins."""
        failure_state.capture(classify_pipeline_failure(frame))
        trace.get_current_span().set_status(Status(StatusCode.ERROR))
        event("call.pipeline_failed", failure_code=failure_state.failure.code)

    @transport.event_handler("on_client_connected")
    async def on_client_connected(_transport, _client) -> None:
        """Queue a first user instruction so the agent greets on connect."""
        nonlocal duration_task
        await mark_call_answered(call_log_id)
        event("call.answered")
        if bundle.speech.mode == "realtime" and bundle.speech.greeting:
            await bundle.speech.greeting(_GREETING_INSTRUCTION)
        else:
            context.add_message({"role": "user", "content": _GREETING_INSTRUCTION})
            await task.queue_frames([LLMRunFrame()])
        if (
            duration_task is None
            and max_call_duration_seconds
            and max_call_duration_seconds > 0
        ):
            duration_task = asyncio.create_task(
                _cancel_pipeline_after(
                    task,
                    max_call_duration_seconds,
                    claims.session_id,
                )
            )

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(_transport, _client) -> None:
        """Stop the active pipeline after its only participant leaves."""
        await task.cancel()

    lease_task = None
    try:
        lease_task = asyncio.create_task(
            _maintain_call_lease(task, call_log_id, claims.session_id, failure_state)
        )
        await PipelineRunner(handle_sigint=False).run(task)
    except Exception as exc:
        # Some provider failures surface as runner exceptions instead of an
        # ErrorFrame. Keep the call-log signal consistent for both paths.
        failure_state.capture(classify_pipeline_failure(exc))
        raise
    finally:
        if lease_task is not None:
            lease_task.cancel()
            with suppress(asyncio.CancelledError):
                await lease_task
        if duration_task is not None:
            duration_task.cancel()
            with suppress(asyncio.CancelledError):
                await duration_task
        if recording_coordinator:
            try:
                with operation("recording.persist"):
                    await recording_coordinator.persist()
            except Exception:  # noqa: BLE001 - cleanup must continue
                logger.exception("Failed to persist recording artifact")
        finalization_code = getattr(llm, "finalization_failure_code", None)
        if isinstance(finalization_code, str):
            failure_state.capture(classify_pipeline_failure(finalization_code))
        failure = failure_state.failure
        if failure:
            telemetry_failure(failure.code)
        await end_call_tracking(
            call_log_id,
            status="failed" if failure else "completed",
            failure_code=failure.code if failure else None,
            failure_message=failure.message if failure else None,
        )
        await _close_mcp_clients(bundle.tools.mcp_clients)
