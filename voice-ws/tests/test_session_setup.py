"""Integration-style tests for prepare_voice_session fallback behavior."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from shared.voice_agents.speech_config import (
    LLMStageConfig,
    PipelineSpeechConfig,
    STTStageConfig,
    TTSStageConfig,
)
from shared.voice_agents.voice_session_service import VoiceSessionClaims
from src.session_setup import prepare_voice_session


def _claims(agent_id: str) -> VoiceSessionClaims:
    return VoiceSessionClaims(
        agent_id=agent_id,
        user_id=str(uuid4()),
        session_id=str(uuid4()),
        purpose="test_call",
    )


class TestPrepareVoiceSession:
    """Ensure session assembly degrades safely when pipeline config fails."""

    @pytest.mark.asyncio
    async def test_pipeline_build_failure_falls_back_to_realtime(self) -> None:
        """Missing pipeline keys must not block the call — fall back to Gemini."""
        agent_id = uuid4()
        agent = SimpleNamespace(
            id=agent_id,
            organization_id=uuid4(),
            use_platform_credits=False,
            instructions_markdown=None,
            name="Test Agent",
            persona=None,
            tone=None,
            mission=None,
            custom_instructions=None,
        )
        pipeline_cfg = PipelineSpeechConfig(
            stt=STTStageConfig(provider="deepgram"),
            llm=LLMStageConfig(provider="openai"),
            tts=TTSStageConfig(provider="cartesia"),
        )
        fallback_speech = MagicMock(mode="realtime")

        with (
            patch(
                "src.session_setup.voice_agent_service.get_agent_by_id",
                new=AsyncMock(return_value=(agent, None)),
            ),
            patch(
                "src.session_setup.organization_service.get_organization_by_id",
                new=AsyncMock(
                    return_value=(
                        SimpleNamespace(
                            id=agent.organization_id,
                            name="Test Org",
                            industry=None,
                            location=None,
                            business_details=None,
                        ),
                        None,
                    )
                ),
            ),
            patch(
                "src.session_setup.assemble_agent_tools",
                new=AsyncMock(
                    return_value=SimpleNamespace(
                        schemas=[],
                        handlers={},
                        mcp_clients=[],
                        enabled_tool_names=[],
                        unavailable_tools=[],
                        skill_summaries=[],
                    )
                ),
            ),
            patch(
                "src.session_setup.resolve_speech_config_for_agent",
                new=AsyncMock(return_value=pipeline_cfg),
            ),
            patch(
                "src.session_setup.resolve_api_keys",
                side_effect=[{"deepgram": "dg"}, {"google": "gem"}],
            ),
            patch(
                "src.session_setup.build_speech_components",
                side_effect=[ValueError("missing openai key"), fallback_speech],
            ) as build_mock,
        ):
            bundle = await prepare_voice_session(_claims(str(agent_id)))

        assert build_mock.call_count == 2
        assert bundle.speech is fallback_speech
        assert bundle.speech_config.engine_mode == "realtime"
