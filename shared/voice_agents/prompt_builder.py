"""Prompt builder service for constructing detailed system prompts for agents."""

import logging
from datetime import datetime, timezone
from typing import List, Optional
from zoneinfo import ZoneInfo

from shared.organization.models import Organization
from shared.voice_agents.models import VoiceAgent

logger = logging.getLogger(__name__)


# Generic system guardrails that apply to all agents
GENERIC_SYSTEM_GUARDRAILS = """# SYSTEM GUARDRAILS AND SECURITY POLICIES

## Data Privacy and Security
- Internal IDs, keys, access tokens, and technical identifiers are for YOUR use only
- NEVER expose internal IDs, file names, email addresses, or technical identifiers to callers
- The caller could be anyone including customers - protect sensitive business information
- Use internal data to inform your responses, but share only relevant, non-sensitive summaries

## Error Handling and Communication
For tool/API errors, follow these guidelines:

**Authentication/Authorization Errors (401, 403, 404):**
- DO NOT share error details with the caller
- Use an appropriate available administrative or communication tool, when configured,
  to notify the organization admin users
- Provide the owner with a brief reference like "Failed to access service because of authentication issue"
- To the caller, give a generic, helpful response without mentioning errors

**Server Errors (500, 502, 503):**
- DO NOT share technical error details with the caller
- Notify the organization admins AND platform admins through appropriate channels
- Provide generic response to caller: "I'm experiencing a temporary issue. Let me help you another way."

**Success Responses:**
- Formulate helpful responses based on internal data
- DO NOT reveal raw data sources, file names, IDs, or technical details
- Focus on answering the caller's need while maintaining privacy
- Never claim a tool-backed action completed before the matching tool returns a successful result
- If a required value or outcome was not returned, say that you do not know or make another appropriate tool call; do not infer success

## Communication Style and Best Practices
- Be professional, polite, helpful, and resourceful in all interactions
- Maintain a warm, conversational tone while remaining efficient
- Avoid extended periods of silence - if you need to make tool calls or retrieve information:
  - Acknowledge the request immediately with a brief response
  - Use conversational fillers like "Let me check that for you," "Okay, I'm pulling up that information," or "I appreciate your patience while I look this up" or something on similar lines
  - Keep the caller informed that you're actively working on their request
- Never leave the caller waiting in awkward silence - a brief acknowledgment is better than nothing"""


class PromptBuilder:
    """Service for building system prompts from organization and agent details.

    Supports two prompt building strategies:
    - **Field-based** (legacy): Assembles prompt from individual agent fields
      (persona, tone, mission, custom_instructions) via build_system_prompt().
    - **Markdown-based**: Uses agent's instructions_markdown directly, rendering
      template variables like {{org.name}}, via build_from_markdown().

    The build() method auto-selects the appropriate strategy based on
    whether instructions_markdown is set on the agent.
    """

    # Template variables supported in markdown instructions
    TEMPLATE_VARS = {
        "org.name": lambda org, agent: org.name or "",
        "org.industry": lambda org, agent: org.industry or "",
        "org.location": lambda org, agent: org.location or "",
        "org.business_details": lambda org, agent: org.business_details or "",
        "agent.name": lambda org, agent: agent.name or "",
    }

    @staticmethod
    def _build_skills_metadata_block(agent_skills: list) -> Optional[str]:
        """Build the AVAILABLE SKILLS section from skill summaries.

        Args:
            agent_skills: List of OrganizationSkillSummary objects with slug, name, description.

        Returns:
            Formatted skills block string, or None if no skills.
        """
        if not agent_skills:
            return None
        skill_lines = []
        for skill in agent_skills:
            desc = skill.description or skill.name
            skill_lines.append(f"- **{skill.slug}**: {desc}")
        return (
            "# AVAILABLE SKILLS\n\n"
            "You have access to the following skills. When the conversation requires "
            "a specific procedure, use the available skill-loading capability with "
            "the skill slug to load its full content.\n\n" + "\n".join(skill_lines)
        )

    @staticmethod
    def build(
        org: Organization,
        agent: VoiceAgent,
        default_rules: Optional[str] = None,
        agent_skills: Optional[list] = None,
        current_datetime: Optional[str] = None,
    ) -> str:
        """Build system prompt, auto-selecting markdown or field-based strategy.

        If the agent has instructions_markdown set, uses that as the primary
        prompt content with template variable rendering. Otherwise falls back
        to the field-based build_system_prompt() method.

        Args:
            org: Organization details for context injection.
            agent: Voice agent configuration.
            default_rules: Optional output rules to append.
            agent_skills: Optional list of skill summaries (slug, name, description)
                for progressive disclosure metadata injection.
            current_datetime: Optional pre-built current-date/time section (from
                :func:`build_current_datetime_section`) to prepend so the model
                has a temporal anchor for "today"/"tomorrow"/"now". ``None`` leaves
                the prompt unchanged (back-compat).

        Returns:
            Complete system prompt string.
        """
        if agent.instructions_markdown:
            return PromptBuilder.build_from_markdown(
                org,
                agent,
                agent.instructions_markdown,
                default_rules,
                agent_skills,
                current_datetime,
            )
        return PromptBuilder.build_system_prompt(
            org,
            agent,
            default_rules,
            agent_skills,
            current_datetime,
        )

    @staticmethod
    def build_from_markdown(
        org: Organization,
        agent: VoiceAgent,
        markdown: str,
        default_rules: Optional[str] = None,
        agent_skills: Optional[list] = None,
        current_datetime: Optional[str] = None,
    ) -> str:
        """Build system prompt from user-provided markdown with template variable rendering.

        Template variables like {{org.name}} are replaced with actual values.
        Skill metadata and system guardrails are appended after the user's content.

        Args:
            org: Organization details for template variable rendering.
            agent: Voice agent configuration.
            markdown: Raw markdown instructions with optional template variables.
            default_rules: Optional output rules to append.
            agent_skills: Optional list of skill summaries for progressive disclosure.
            current_datetime: Optional current-date/time section to prepend (see
                :func:`build_current_datetime_section`).

        Returns:
            Complete system prompt string with rendered variables and appended guardrails.
        """
        # Render template variables
        rendered = markdown
        for var_name, resolver in PromptBuilder.TEMPLATE_VARS.items():
            placeholder = "{{" + var_name + "}}"
            rendered = rendered.replace(placeholder, resolver(org, agent))

        sections: List[str] = []
        if current_datetime:
            sections.append(current_datetime)
        sections.append(rendered)

        # Append skill metadata (progressive disclosure — names only, not content)
        skills_block = PromptBuilder._build_skills_metadata_block(agent_skills)
        if skills_block:
            sections.append(skills_block)

        # Always append guardrails (safety net)
        sections.append(GENERIC_SYSTEM_GUARDRAILS)

        # Append output rules if provided
        if default_rules:
            sections.append(default_rules)

        return "\n\n".join(sections)

    @staticmethod
    def build_system_prompt(
        org: Organization,
        agent: VoiceAgent,
        default_rules: Optional[str] = None,
        agent_skills: Optional[list] = None,
        current_datetime: Optional[str] = None,
    ) -> str:
        """
        Builds a comprehensive system prompt by aggregating information from
        the organization and the agent (field-based strategy).

        Args:
            org: Organization details
            agent: Voice agent configuration
            default_rules: Optional default rules to include
            agent_skills: Optional list of skill summaries for progressive disclosure
            current_datetime: Optional current-date/time section to prepend (see
                :func:`build_current_datetime_section`).

        Returns:
            Complete system prompt string
        """
        sections: List[str] = []

        # 0. Current date/time anchor (so the model knows "today"/"now")
        if current_datetime:
            sections.append(current_datetime)

        # 1. Identity & Persona
        role = agent.persona or "a helpful AI voice assistant"
        identity_text = (
            role if role.lower().startswith("you are") else f"You are {role}"
        )
        if org.name:
            identity_text += f" representing {org.name}"

        if agent.tone:
            identity_text += f". Your communication style is {agent.tone}."

        sections.append(f"# IDENTITY AND PERSONA\n{identity_text}")

        # 2. Your Mission
        if agent.mission:
            sections.append(f"# YOUR MISSION\n{agent.mission}")

        # 3. Business Context
        business_info = []
        if org.industry:
            business_info.append(f"Industry: {org.industry}")

        if org.location:
            business_info.append(f"Location/Address: {org.location}")

        if org.business_details:
            business_info.append(f"Business Context:\n{org.business_details}")

        if business_info:
            sections.append("# BUSINESS CONTEXT\n" + "\n".join(business_info))

        # 4. Specific Instructions
        if agent.custom_instructions:
            sections.append(f"# ADDITIONAL INSTRUCTIONS\n{agent.custom_instructions}")

        # 5. Skill metadata (progressive disclosure — names only, not content)
        skills_block = PromptBuilder._build_skills_metadata_block(agent_skills)
        if skills_block:
            sections.append(skills_block)

        # 6. System Guardrails (Generic security and privacy rules)
        sections.append(GENERIC_SYSTEM_GUARDRAILS)

        # 7. Output Rules & Guardrails (Default rules from caller)
        if default_rules:
            sections.append(default_rules)

        return "\n\n".join(sections)


def build_current_datetime_section(
    timezone_name: Optional[str] = None,
    now: Optional[datetime] = None,
) -> str:
    """Build the ``# CURRENT DATE AND TIME`` section to anchor the model in time.

    The Gemini realtime model has no inherent sense of the current date/time, so
    without this anchor it can guess when a caller asks about relative dates or
    times. This section states the current date/time in a configured timezone so
    the model reasons from a real reference point.

    The timezone is resolved per organization (``organizations.timezone`` IANA name)
    with an optional platform dev fallback (``AGENT_DEFAULT_TIMEZONE`` env var when
    the org timezone is unset). Organization-specific temporal context may still
    appear in the organization or agent instructions; this section supplies a
    structured "now" anchor.

    Args:
        timezone_name: IANA timezone name (e.g. ``"America/Phoenix"``). If
            ``None``, empty, or invalid, falls back to UTC (a warning is logged
            for an invalid name) — this never raises, so a misconfigured env var
            never breaks agent startup.
        now: The instant to render. Defaults to ``datetime.now(tz)``. Accepts a
            fixed value so tests are deterministic.

    Returns:
        A markdown section string with a human-readable, timezone-aware current
        timestamp (weekday, date, clock time, tz name, UTC offset) plus guidance
        telling the model to treat it as the reference point for relative time
        words and to reconcile with the org's stated timezone if different.
    """
    if timezone_name:
        try:
            tz = ZoneInfo(timezone_name)
        except Exception:
            logger.warning(
                "build_current_datetime_section: unknown IANA timezone %r; "
                "falling back to UTC. Set AGENT_DEFAULT_TIMEZONE to a valid IANA "
                "name (e.g. 'America/Phoenix').",
                timezone_name,
            )
            tz = ZoneInfo("UTC")
            timezone_name = "UTC"
    else:
        tz = ZoneInfo("UTC")
        timezone_name = "UTC"

    instant = now if now is not None else datetime.now(tz)
    if instant.tzinfo is None:
        # Treat a naive `now` as being in the chosen tz so the offset is correct.
        instant = instant.replace(tzinfo=tz)
    else:
        instant = instant.astimezone(tz)

    # e.g. "Thursday, July 16, 2026 at 2:30 PM" and offset "UTC-07:00".
    formatted = instant.strftime("%A, %B %-d, %Y at %-I:%M %p")
    offset = instant.strftime("%z")  # e.g. "-0700"
    offset_pretty = f"UTC{offset[:3]}:{offset[3:]}" if offset else "UTC+00:00"

    iso_now = instant.isoformat()

    return (
        "# CURRENT DATE AND TIME\n\n"
        f"It is currently {formatted} ({timezone_name}, {offset_pretty}).\n"
        f"Reference instant (ISO 8601): {iso_now}\n\n"
        'Treat this as the current date and time. When the caller says "today", '
        '"tomorrow", "now", "this week", or asks about a time-sensitive fact, '
        "reason from this reference point. If the caller's timezone differs, "
        "reconcile using the organization's configured timezone or details in "
        "business context.\n\n"
        "Do not claim that a time-sensitive fact is current or upcoming if it "
        "conflicts with this reference instant. If the caller asks about a time "
        "that has already passed, say so rather than pretending it is upcoming."
    )
