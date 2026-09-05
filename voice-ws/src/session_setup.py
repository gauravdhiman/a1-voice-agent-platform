"""Prepare shared agent, prompt, tool, and speech state for a Pipecat call."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from pipecat.adapters.schemas.tools_schema import ToolsSchema
from src.speech.factory import build_speech_components
from src.tools.assembly import AssembledTools, assemble_agent_tools

from shared.organization.service import BaseOrganizationService
from shared.organization.timezone import resolve_organization_timezone
from shared.voice_agents.default_voice_rules import DEFAULT_VOICE_SYSTEM_PROMPT
from shared.voice_agents.key_resolver import resolve_api_keys
from shared.voice_agents.prompt_builder import (
    GENERIC_SYSTEM_GUARDRAILS,
    PromptBuilder,
    build_current_datetime_section,
)
from shared.voice_agents.service import voice_agent_service
from shared.voice_agents.speech_config import (
    PipelineSpeechConfig,
    default_realtime_config,
)
from shared.voice_agents.speech_config_resolver import resolve_speech_config_for_agent
from shared.voice_agents.tools.base.tool_context import ToolContext
from shared.voice_agents.voice_session_service import VoiceSessionClaims

logger = logging.getLogger(__name__)
organization_service = BaseOrganizationService()


@dataclass
class VoiceSessionBundle:
    """Resolved runtime state for a single authenticated voice session."""

    agent: Any
    organization: Any
    tools: AssembledTools
    speech_config: Any
    api_keys: dict[str, Any]
    instructions: str
    speech: Any


async def prepare_voice_session(claims: VoiceSessionClaims) -> VoiceSessionBundle:
    """Load and assemble all runtime state needed before a call starts.

    Args:
        claims: Verified short-lived WebSocket session claims.

    Returns:
        A bundle containing the agent, optional organization, assembled tools,
        resolved config and keys, full prompt, and configured speech services.

    Raises:
        ValueError: If the agent is absent.
        ValueError: If a selected speech provider cannot be configured.
    """
    agent_id = UUID(claims.agent_id)
    agent, agent_error = await voice_agent_service.get_agent_by_id(agent_id)
    if agent_error or agent is None:
        raise ValueError(f"Agent not found: {agent_error or agent_id}")

    org = None
    if agent.organization_id:
        org, _ = await organization_service.get_organization_by_id(
            agent.organization_id
        )
    session_timezone = resolve_organization_timezone(
        org,
        platform_default=os.getenv("AGENT_DEFAULT_TIMEZONE"),
    )
    tools = await assemble_agent_tools(
        agent.id,
        agent.organization_id,
        runtime_context=ToolContext(
            organization_id=(
                str(agent.organization_id) if agent.organization_id else None
            ),
            agent_id=str(agent.id),
            organization_timezone=session_timezone,
            session_id=claims.session_id,
            is_demo=bool(getattr(agent, "is_demo", False)),
            demo_slug=getattr(agent, "demo_slug", None),
        ),
        organization=org,
    )
    speech_config = await resolve_speech_config_for_agent(agent, agent.id)
    api_keys = resolve_api_keys(
        speech_config,
        org=org,
        use_platform_credits=bool(getattr(agent, "use_platform_credits", False)),
    )
    current_datetime = build_current_datetime_section(session_timezone)
    instructions = (
        PromptBuilder.build(
            org=org,
            agent=agent,
            default_rules=DEFAULT_VOICE_SYSTEM_PROMPT,
            agent_skills=tools.skill_summaries,
            current_datetime=current_datetime,
        )
        if org is not None
        else "\n\n".join(
            section
            for section in (
                current_datetime,
                DEFAULT_VOICE_SYSTEM_PROMPT,
                GENERIC_SYSTEM_GUARDRAILS,
            )
            if section
        )
    )
    logger.info(
        "Prepared voice session agent=%s timezone=%s functions=%s unavailable=%s",
        agent.id,
        session_timezone,
        [schema.name for schema in tools.schemas],
        tools.unavailable_tools,
    )
    tools_schema = ToolsSchema(standard_tools=tools.schemas) if tools.schemas else None
    try:
        speech = build_speech_components(
            speech_config,
            api_keys,
            instructions,
            tools=tools_schema,
        )
    except ValueError as exc:
        # Pipeline presets with missing direct-provider keys must not kill the
        # call — fall back to Gemini realtime the same way a bad preset falls
        # back elsewhere in voice-ws.
        if isinstance(speech_config, PipelineSpeechConfig):
            logger.error(
                "Agent %s: pipeline speech config could not be built (%s); "
                "falling back to realtime default.",
                agent.id,
                exc,
            )
            speech_config = default_realtime_config()
            api_keys = resolve_api_keys(
                speech_config,
                org=org,
                use_platform_credits=bool(
                    getattr(agent, "use_platform_credits", False)
                ),
            )
            speech = build_speech_components(
                speech_config,
                api_keys,
                instructions,
                tools=tools_schema,
            )
        else:
            raise
    return VoiceSessionBundle(
        agent=agent,
        organization=org,
        tools=tools,
        speech_config=speech_config,
        api_keys=api_keys,
        instructions=instructions,
        speech=speech,
    )
