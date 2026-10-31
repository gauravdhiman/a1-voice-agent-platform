"""Integration-style tests for prepare_voice_session fallback behavior."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from src.session_setup import prepare_voice_session

from shared.voice_agents.prompt_builder import GENERIC_SYSTEM_GUARDRAILS
from shared.voice_agents.speech_config import (
    LLMStageConfig,
    PipelineSpeechConfig,
    RealtimeSpeechConfig,
    STTStageConfig,
    TTSStageConfig,
)
from shared.voice_agents.voice_session_service import VoiceSessionClaims


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
                "src.session_setup.resolve_speech_profile_for_agent",
                new=AsyncMock(return_value=(pipeline_cfg, "organization")),
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

    @pytest.mark.asyncio
    async def test_realtime_build_failure_is_not_fallback(self) -> None:
        """A selected OpenAI realtime failure must reach the caller unchanged."""
        agent_id = uuid4()
        agent = SimpleNamespace(
            id=agent_id,
            organization_id=None,
            use_platform_credits=False,
            instructions_markdown=None,
            name="Test Agent",
            persona=None,
            tone=None,
            mission=None,
            custom_instructions=None,
        )
        realtime_cfg = RealtimeSpeechConfig(provider="openai")

        with (
            patch(
                "src.session_setup.voice_agent_service.get_agent_by_id",
                new=AsyncMock(return_value=(agent, None)),
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
                "src.session_setup.resolve_speech_profile_for_agent",
                new=AsyncMock(return_value=(realtime_cfg, "organization")),
            ),
            patch(
                "src.session_setup.resolve_api_keys",
                return_value={"openai": "openai-key"},
            ),
            patch(
                "src.session_setup.build_speech_components",
                side_effect=ValueError("OpenAI Live unavailable"),
            ) as build_mock,
        ):
            with pytest.raises(ValueError, match="OpenAI Live unavailable"):
                await prepare_voice_session(_claims(str(agent_id)))

        build_mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_uses_organization_timezone_in_prompt(self, monkeypatch) -> None:
        """Org IANA timezone anchors the CURRENT DATE AND TIME section."""
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
        org = SimpleNamespace(
            id=agent.organization_id,
            name="Test Org",
            industry=None,
            location=None,
            business_details=None,
            timezone="America/Phoenix",
        )
        monkeypatch.setenv("AGENT_DEFAULT_TIMEZONE", "America/New_York")

        with (
            patch(
                "src.session_setup.voice_agent_service.get_agent_by_id",
                new=AsyncMock(return_value=(agent, None)),
            ),
            patch(
                "src.session_setup.organization_service.get_organization_by_id",
                new=AsyncMock(return_value=(org, None)),
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
                "src.session_setup.resolve_speech_profile_for_agent",
                new=AsyncMock(
                    return_value=(
                        __import__(
                            "shared.voice_agents.speech_config",
                            fromlist=["default_realtime_config"],
                        ).default_realtime_config(),
                        "platform",
                    )
                ),
            ),
            patch(
                "src.session_setup.resolve_api_keys",
                return_value={"google": "gem"},
            ),
            patch(
                "src.session_setup.build_speech_components",
                return_value=MagicMock(mode="realtime"),
            ),
            patch(
                "src.session_setup.build_current_datetime_section",
                wraps=__import__(
                    "shared.voice_agents.prompt_builder",
                    fromlist=["build_current_datetime_section"],
                ).build_current_datetime_section,
            ) as datetime_section,
        ):
            await prepare_voice_session(_claims(str(agent_id)))

        datetime_section.assert_called_once()
        assert datetime_section.call_args.args[0] == "America/Phoenix"
        assert datetime_section.call_args.kwargs.get("now") is None

    @pytest.mark.asyncio
    async def test_orgless_session_still_includes_platform_guardrails(self) -> None:
        """The fallback prompt must not bypass platform safety rules."""
        agent_id = uuid4()
        agent = SimpleNamespace(
            id=agent_id,
            organization_id=None,
            use_platform_credits=False,
            instructions_markdown=None,
            name="Test Agent",
            persona=None,
            tone=None,
            mission=None,
            custom_instructions=None,
        )

        with (
            patch(
                "src.session_setup.voice_agent_service.get_agent_by_id",
                new=AsyncMock(return_value=(agent, None)),
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
                "src.session_setup.resolve_speech_profile_for_agent",
                new=AsyncMock(return_value=(MagicMock(), "platform")),
            ),
            patch(
                "src.session_setup.resolve_api_keys",
                return_value={},
            ),
            patch(
                "src.session_setup.build_speech_components",
                return_value=MagicMock(mode="realtime"),
            ),
        ):
            bundle = await prepare_voice_session(_claims(str(agent_id)))

        assert GENERIC_SYSTEM_GUARDRAILS in bundle.instructions
