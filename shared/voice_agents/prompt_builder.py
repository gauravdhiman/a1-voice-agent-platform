"""
Prompt builder service for constructing detailed system prompts for AI agents.
"""

from typing import List, Optional
from shared.organization.models import Organization
from shared.voice_agents.models import VoiceAgent


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

    "Calcom": """## Cal.com Tool Guidelines
- Booking details and attendee information are private
- DO NOT expose booking IDs, internal URLs, or attendee details to callers
- Use booking system internally to manage appointments
- Confirm bookings with general information only""",
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
    def build(
        org: Organization,
        agent: VoiceAgent,
        default_rules: Optional[str] = None,
        enabled_tools: Optional[List[str]] = None,
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

        Returns:
            Complete system prompt string.
        """
        if agent.instructions_markdown:
            return PromptBuilder.build_from_markdown(
                org, agent, agent.instructions_markdown,
                default_rules, enabled_tools,
            )
        return PromptBuilder.build_system_prompt(
            org, agent, default_rules, enabled_tools,
        )

    @staticmethod
    def build_from_markdown(
        org: Organization,
        agent: VoiceAgent,
        markdown: str,
        default_rules: Optional[str] = None,
        enabled_tools: Optional[List[str]] = None,
    ) -> str:
        """Build system prompt from user-provided markdown with template variable rendering.

        Template variables like {{org.name}} are replaced with actual values.
        System guardrails and tool guidelines are appended after the user's content
        to ensure safety policies cannot be overridden.

        Args:
            org: Organization details for template variable rendering.
            agent: Voice agent configuration.
            markdown: Raw markdown instructions with optional template variables.
            default_rules: Optional output rules to append.
            enabled_tools: Optional list of enabled tool names.

        Returns:
            Complete system prompt string with rendered variables and appended guardrails.
        """
        # Render template variables
        rendered = markdown
        for var_name, resolver in PromptBuilder.TEMPLATE_VARS.items():
            placeholder = "{{" + var_name + "}}"
            rendered = rendered.replace(placeholder, resolver(org, agent))

        sections = [rendered]

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
    ) -> str:
        """
        Builds a comprehensive system prompt by aggregating information from
        the organization and the agent.

        Args:
            org: Organization details
            agent: Voice agent configuration
            default_rules: Optional default rules to include
            enabled_tools: Optional list of enabled tool names for toolset-specific instructions

        Returns:
            Complete system prompt string
        """
        sections = []

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

        # 5. System Guardrails (Generic security and privacy rules)
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
