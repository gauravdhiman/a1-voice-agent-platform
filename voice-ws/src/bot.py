"""Pipecat pipeline for Gemini Realtime over WebSocket transports.

Supports:
- Browser test calls (ProtobufFrameSerializer) — Phase 1
- Twilio Media Streams (TwilioFrameSerializer) — Phase 2

Tools / pipeline STT→LLM→TTS arrive in Phase 3.
"""

from __future__ import annotations

import logging
import os
from typing import Optional
from uuid import UUID

from fastapi import WebSocket
from pipecat.frames.frames import LLMRunFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
)
from pipecat.serializers.base_serializer import FrameSerializer
from pipecat.serializers.protobuf import ProtobufFrameSerializer
from pipecat.services.google.gemini_live.llm import GeminiLiveLLMService
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)

from shared.organization.service import BaseOrganizationService
from shared.voice_agents.key_resolver import resolve_api_keys
from shared.voice_agents.preset_service import preset_service
from shared.voice_agents.prompt_builder import (
    PromptBuilder,
    build_current_datetime_section,
)
from shared.voice_agents.service import voice_agent_service
from shared.voice_agents.speech_config import (
    RealtimeSpeechConfig,
    default_realtime_config,
    parse_speech_config,
)
from shared.voice_agents.voice_session_service import VoiceSessionClaims

from src.defaults import DEFAULT_VOICE_RULES
from src.recording import NoOpRecordingTee

logger = logging.getLogger(__name__)

organization_service = BaseOrganizationService()


def _normalize_gemini_model(model: str) -> str:
    """Ensure Gemini Live model ids include the ``models/`` prefix."""
    if model.startswith("models/"):
        return model
    return f"models/{model}"


async def _resolve_realtime_config(agent) -> RealtimeSpeechConfig:
    """Load realtime speech config for the agent (preset or default).

    Phase 1 only supports realtime. Pipeline configs fall back to the default
    realtime config with a warning until Phase 3.
    """
    if agent.preset_id:
        preset, preset_err = await preset_service.get_preset_by_id(agent.preset_id)
        if preset and not preset_err:
            try:
                cfg = parse_speech_config(preset.config)
                if isinstance(cfg, RealtimeSpeechConfig):
                    return cfg
                logger.warning(
                    "Agent %s has pipeline preset; Phase 1 uses realtime default",
                    agent.id,
                )
            except Exception as exc:  # noqa: BLE001 — fall back safely
                logger.error("Failed to parse preset config: %s", exc)

    return default_realtime_config()


async def _build_system_instruction(agent) -> tuple[str, Optional[object]]:
    """Build PromptBuilder system instruction and return (prompt, org)."""
    org = None
    if agent.organization_id:
        org, org_err = await organization_service.get_organization_by_id(
            agent.organization_id
        )
        if org_err:
            logger.warning(
                "Org lookup failed for agent %s: %s — using platform keys",
                agent.id,
                org_err,
            )

    current_dt = build_current_datetime_section(
        timezone_name=os.getenv("AGENT_DEFAULT_TIMEZONE", "UTC")
    )

    if org is None:
        instructions = f"{current_dt}\n\n{DEFAULT_VOICE_RULES}"
    else:
        instructions = PromptBuilder.build(
            org=org,
            agent=agent,
            default_rules=DEFAULT_VOICE_RULES,
            enabled_tools=None,  # Phase 3
            agent_skills=None,  # Phase 3
            current_datetime=current_dt,
        )
    return instructions, org


async def run_bot(
    websocket: WebSocket,
    claims: VoiceSessionClaims,
    *,
    serializer: Optional[FrameSerializer] = None,
) -> None:
    """Run a Gemini Realtime Pipecat session on an accepted WebSocket.

    Args:
        websocket: Accepted FastAPI WebSocket (browser or Twilio).
        claims: Verified ``voice_ws_session`` JWT claims.
        serializer: Frame serializer for the transport. Defaults to
            :class:`ProtobufFrameSerializer` (browser). Pass
            :class:`TwilioFrameSerializer` for Media Streams.
    """
    agent_id = UUID(claims.agent_id)
    frame_serializer: FrameSerializer = serializer or ProtobufFrameSerializer()
    logger.info(
        "Starting voice-ws bot session_id=%s agent_id=%s purpose=%s serializer=%s",
        claims.session_id,
        claims.agent_id,
        claims.purpose,
        type(frame_serializer).__name__,
    )

    agent, err = await voice_agent_service.get_agent_by_id(agent_id)
    if err or agent is None:
        raise ValueError(f"Agent not found: {err or agent_id}")

    instructions, org = await _build_system_instruction(agent)
    speech_config = await _resolve_realtime_config(agent)
    use_platform_credits = bool(getattr(agent, "use_platform_credits", False))

    api_keys = resolve_api_keys(
        speech_config,
        org=org,
        use_platform_credits=use_platform_credits,
    )
    gemini_key = api_keys.get("google") or os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        raise RuntimeError("No Gemini API key available for voice session")

    transport = FastAPIWebsocketTransport(
        websocket=websocket,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=False,
            serializer=frame_serializer,
        ),
    )

    llm = GeminiLiveLLMService(
        api_key=gemini_key,
        settings=GeminiLiveLLMService.Settings(
            model=_normalize_gemini_model(speech_config.model),
            voice=speech_config.voice,
            system_instruction=instructions,
            temperature=speech_config.temperature,
        ),
    )

    context = LLMContext()
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(context)
    recording_tee = NoOpRecordingTee(
        session_id=claims.session_id,
        enabled=os.getenv("VOICE_RECORDING_TEE", "false").lower() == "true",
    )

    pipeline = Pipeline(
        [
            transport.input(),
            user_aggregator,
            llm,
            recording_tee,
            transport.output(),
            assistant_aggregator,
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            allow_interruptions=True,
            enable_metrics=False,
        ),
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(_transport, _client) -> None:
        logger.info("Client connected session_id=%s — greeting", claims.session_id)
        await task.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(_transport, _client) -> None:
        logger.info("Client disconnected session_id=%s", claims.session_id)
        await task.cancel()

    runner = PipelineRunner(handle_sigint=False)
    await runner.run(task)
    logger.info("voice-ws session ended session_id=%s", claims.session_id)
