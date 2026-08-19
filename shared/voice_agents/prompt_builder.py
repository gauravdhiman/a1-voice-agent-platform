"""
Prompt builder service for constructing detailed system prompts for AI agents.
"""

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
- NEVER expose internal IDs, spreadsheet IDs, file names, email addresses, or technical identifiers to callers
- The caller could be anyone including customers - protect sensitive business information
- Use internal data to inform your responses, but share only relevant, non-sensitive summaries

## Error Handling and Communication
For tool/API errors, follow these guidelines:

**Authentication/Authorization Errors (401, 403, 404):**
- DO NOT share error details with the caller
- Use your available communication tools (email, text, Slack) to notify the organization admin users
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

## Communication Style and Best Practices
- Be professional, polite, helpful, and resourceful in all interactions
- Maintain a warm, conversational tone while remaining efficient
- Avoid extended periods of silence - if you need to make tool calls or retrieve information:
  - Acknowledge the request immediately with a brief response
  - Use conversational fillers like "Let me check that for you," "Okay, I'm pulling up that information," or "I appreciate your patience while I look this up" or something on similar lines
  - Keep the caller informed that you're actively working on their request
- Never leave the caller waiting in awkward silence - a brief acknowledgment is better than nothing"""

# Toolset-specific instructions for different tool types
TOOLSET_INSTRUCTIONS = {
    "Google_Sheets": """## Google Sheets Tool Guidelines
- Spreadsheet data is for YOUR internal analysis and decision-making only
- DO NOT expose raw cell values, sheet names, spreadsheet IDs, or file structure to callers
- Use data internally to formulate helpful responses without revealing sources
- When listing workbooks, use titles internally but don't read them out to callers""",

    "Gmail": """## Gmail Tool Guidelines
- Email addresses, message content, and sender/recipient details are private
- DO NOT share email addresses, names, or message content with callers
- Use email information internally to understand context and respond appropriately
- For email operations, confirm actions without revealing specific email details""",

    "Google_Calendar": """## Google Calendar Tool Guidelines
- Calendar events and attendee information are private
- DO NOT share attendee names, email addresses, or event details with callers
- Use calendar data internally to check availability and schedule appropriately
- Confirm scheduling actions without revealing specific event details""",

    "CalCom": """## Cal.com Tool Guidelines
- Booking details and attendee information are private
- DO NOT expose booking IDs, internal URLs, or attendee details to callers
- Use booking system internally to manage appointments
- Confirm bookings with general information only
- Always call get_available_slots before offering times, and create_booking before confirming a booking""",

    "Google_calendar_appointment": """## Google Calendar Appointment Guidelines
- Use this calendar only for business appointments; never expose event IDs, raw event details, or private attendee information.
- For an open-ended request, call `find_available_slots` with the organization's current date/time and timezone. For one proposed time, call `check_availability` for that exact interval.
- Collect only the appointment details the organization requires. Keep details already provided by the caller; do not ask the same question again unless the caller changes or corrects it.
- Before a mutation, read back the purpose, date, local time, duration, and required contact details once. Call `create_appointment`, `update_appointment`, or `cancel_appointment` with `user_confirmed=true` only after the caller explicitly agrees.
- The service performs its own final conflict check. If it returns `busy`, `past`, `confirmation_required`, or an error, do not claim the action succeeded and do not repeat the same call without resolving that result.
- Treat appointment IDs and matching caller details as internal lookup data, not as identity verification.""",

    "Google_calendar_appointment_mcp": """## Google Calendar Appointment Guidelines
- Use this calendar only for business appointments; never expose event IDs, raw event details, or private attendee information.
- For an open-ended request, call `find_available_slots` with the organization's current date/time and timezone. For one proposed time, call `check_availability` for that exact interval.
- Collect only the appointment details the organization requires. Keep details already provided by the caller; do not ask the same question again unless the caller changes or corrects it.
- Before a mutation, read back the purpose, date, local time, duration, and required contact details once. Call `create_appointment`, `update_appointment`, or `cancel_appointment` with `user_confirmed=true` only after the caller explicitly agrees.
- The service performs its own final conflict check. If it returns `busy`, `past`, `confirmation_required`, or an error, do not claim the action succeeded and do not repeat the same call without resolving that result.
- Treat appointment IDs and matching caller details as internal lookup data, not as identity verification.""",

    # Compatibility guidance for agents that still have the pre-appointment
    # MCP row enabled while the catalog migration is rolling out.
    "Google_calendar_mcp": """## Google Calendar Appointment Guidelines
- Prefer the appointment-specific functions when available; never expose raw event IDs or private attendee information.
- Do not claim an appointment was booked without a successful create result.""",
}


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
            "a specific procedure, use the `load_skill` tool with the skill slug to "
            "load its full content.\n\n"
            + "\n".join(skill_lines)
        )

    @staticmethod
    def build(
        org: Organization,
        agent: VoiceAgent,
        default_rules: Optional[str] = None,
        enabled_tools: Optional[List[str]] = None,
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
            enabled_tools: Optional list of enabled tool names.
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
                org, agent, agent.instructions_markdown,
                default_rules, enabled_tools, agent_skills, current_datetime,
            )
        return PromptBuilder.build_system_prompt(
            org, agent, default_rules, enabled_tools, agent_skills, current_datetime,
        )

    @staticmethod
    def build_from_markdown(
        org: Organization,
        agent: VoiceAgent,
        markdown: str,
        default_rules: Optional[str] = None,
        enabled_tools: Optional[List[str]] = None,
        agent_skills: Optional[list] = None,
        current_datetime: Optional[str] = None,
    ) -> str:
        """Build system prompt from user-provided markdown with template variable rendering.

        Template variables like {{org.name}} are replaced with actual values.
        Skill metadata, system guardrails, and tool guidelines are appended after
        the user's content.

        Args:
            org: Organization details for template variable rendering.
            agent: Voice agent configuration.
            markdown: Raw markdown instructions with optional template variables.
            default_rules: Optional output rules to append.
            enabled_tools: Optional list of enabled tool names.
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

        # Append tool guidelines if applicable
        if enabled_tools:
            tool_instructions = []
            for tool_name in enabled_tools:
                if tool_name in TOOLSET_INSTRUCTIONS:
                    tool_instructions.append(TOOLSET_INSTRUCTIONS[tool_name])
            if tool_instructions:
                sections.append(
                    "# TOOLSET-SPECIFIC GUIDELINES\n" + "\n\n".join(tool_instructions)
                )

        # Append output rules if provided
        if default_rules:
            sections.append(default_rules)

        return "\n\n".join(sections)

    @staticmethod
    def build_system_prompt(
        org: Organization,
        agent: VoiceAgent,
        default_rules: Optional[str] = None,
        enabled_tools: Optional[List[str]] = None,
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
            enabled_tools: Optional list of enabled tool names for toolset-specific instructions
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
        identity_text = role if role.lower().startswith("you are") else f"You are {role}"
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

        # 6. Toolset-Specific Instructions
        if enabled_tools:
            tool_instructions = []
            for tool_name in enabled_tools:
                if tool_name in TOOLSET_INSTRUCTIONS:
                    tool_instructions.append(TOOLSET_INSTRUCTIONS[tool_name])

            if tool_instructions:
                sections.append("# TOOLSET-SPECIFIC GUIDELINES\n" + "\n\n".join(tool_instructions))

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
    without this anchor it guesses when a caller asks about "today", "tomorrow",
    "now", or business hours (observed: it assumed it was the weekend / after
    hours). This section states the current date/time in a configured timezone so
    the model reasons from a real reference point.

    The timezone is resolved per organization (``organizations.timezone`` IANA name)
    with an optional platform dev fallback (``AGENT_DEFAULT_TIMEZONE`` env var when
    the org timezone is unset). Business hours may still appear in
    ``business_details``; this section supplies a structured "now" anchor.

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
        "Treat this as the current date and time. When the caller says \"today\", "
        "\"tomorrow\", \"now\", \"this week\", or asks about upcoming/past events, "
        "reason from this reference point. If the caller's timezone differs, "
        "reconcile using the organization's configured timezone or details in "
        "business context.\n\n"
        "Never offer, suggest, or book appointment times that start before this "
        "reference instant. If a caller asks about a time that has already passed, "
        "say it is in the past and offer only future alternatives. Before stating "
        "any alternative time is free, call check_availability for that exact window."
    )
