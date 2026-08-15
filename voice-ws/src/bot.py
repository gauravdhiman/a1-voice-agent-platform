"""Run Pipecat voice sessions for browser and Twilio WebSocket transports."""

from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import WebSocket
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.frames.frames import LLMRunFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.processors.audio.audio_buffer_processor import AudioBufferProcessor
from pipecat.serializers.base_serializer import FrameSerializer
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)
from src.call_tracking import end_call_tracking, start_call_tracking
from src.recording import RecordingCoordinator
from src.recording_policy import should_record_agent_call
from src.serialization.browser_protobuf import BrowserWebSocketFrameSerializer
from src.session_setup import prepare_voice_session

from shared.config import settings
from shared.voice_agents.voice_session_service import VoiceSessionClaims

logger = logging.getLogger(__name__)
_GREETING_INSTRUCTION = "Greet the user warmly and ask how you can help."


async def _close_mcp_clients(clients: list[object]) -> None:
    """Close every session-owned MCP client without masking teardown errors."""
    for client in clients:
        try:
            await client.close()
        except Exception:  # noqa: BLE001 - cleanup must attempt all clients
            logger.exception("Failed to close MCP client")


async def run_bot(
    websocket: WebSocket,
    claims: VoiceSessionClaims,
    *,
    serializer: Optional[FrameSerializer] = None,
) -> None:
    """Run one authenticated Pipecat voice session.

    The selected agent preset determines whether this builds Gemini Live or a
    modular Deepgram → OpenAI/Cerebras → Cartesia pipeline. Browser protobuf and
    Twilio serializers share the same transport and assembly path.
    """
    frame_serializer = serializer or BrowserWebSocketFrameSerializer()
    bundle = await prepare_voice_session(claims)
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
        llm.register_function(name, handler)

    call_log_id = None
    recording_coordinator: Optional[RecordingCoordinator] = None
    audio_buffer: Optional[AudioBufferProcessor] = None
    if bundle.agent.organization_id:
        call_log_id = await start_call_tracking(
            session_id=claims.session_id,
            call_sid=claims.call_sid,
            organization_id=bundle.agent.organization_id,
            agent_id=bundle.agent.id,
        )

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
            audio_buffer = AudioBufferProcessor(
                auto_start_recording=True,
                num_channels=2,
            )

            @audio_buffer.event_handler("on_audio_data")
            async def on_audio_data(_buffer, audio, sample_rate, num_channels) -> None:
                """Forward Pipecat's final mixed PCM buffer to the coordinator."""
                if recording_coordinator:
                    recording_coordinator.capture_audio(
                        bytes(audio),
                        sample_rate=sample_rate,
                        num_channels=num_channels,
                    )

        except Exception:  # noqa: BLE001 - recording cannot block a call
            logger.exception(
                "Recording setup failed for session %s; continuing without audio",
                claims.session_id,
            )
            recording_coordinator = None
            audio_buffer = None

    output_processor = transport.output()
    if audio_buffer:
        # AudioBufferProcessor observes both inbound and outbound audio when it
        # follows transport.output(), matching Pipecat's mixed-call pattern.
        output_processor = Pipeline([output_processor, audio_buffer])

    processors = [transport.input()]
    if bundle.speech.mode == "pipeline":
        processors.extend([bundle.speech.stt, user_aggregator, llm, bundle.speech.tts])
    else:
        processors.extend([user_aggregator, llm])
    processors.extend([output_processor, assistant_aggregator])
    task = PipelineTask(
        Pipeline(processors),
        params=PipelineParams(allow_interruptions=True, enable_metrics=True),
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(_transport, _client) -> None:
        """Queue a first user instruction so the agent greets on connect."""
        context.add_message({"role": "user", "content": _GREETING_INSTRUCTION})
        await task.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(_transport, _client) -> None:
        """Stop the active pipeline after its only participant leaves."""
        await task.cancel()

    try:
        await PipelineRunner(handle_sigint=False).run(task)
    finally:
        if audio_buffer:
            try:
                await audio_buffer.stop_recording()
            except Exception:  # noqa: BLE001 - cleanup must continue
                logger.exception("Failed to stop recording buffer")
        if recording_coordinator:
            try:
                await recording_coordinator.persist()
            except Exception:  # noqa: BLE001 - cleanup must continue
                logger.exception("Failed to persist recording artifact")
        await end_call_tracking(call_log_id)
        await _close_mcp_clients(bundle.tools.mcp_clients)
