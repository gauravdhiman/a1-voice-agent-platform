"""
Tests for PromptBuilder integration in worker.

These tests verify that the worker correctly integrates with the PromptBuilder
to generate system prompts from organization and agent data.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest


# ---------------------------------------------------------------------------
# Shared sample-data fixtures.
#
# These were previously defined as class-scoped fixtures inside
# TestPromptBuilderIntegration, which made them invisible to the sibling
# TestPromptBuilderEdgeCases class (the edge-case tests errored with "fixture
# 'sample_organization' not found"). They are plain data fixtures with no
# reason to be class-scoped, so they live at module scope and are visible to
# both test classes.
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_organization():
    """Sample organization data with all context fields."""
    now = datetime.now(timezone.utc)
    return {
        "id": UUID("12345678-1234-5678-1234-567812345678"),
        "name": "Acme Corporation",
        "slug": "acme-corp",
        "description": "Leading provider of innovative solutions",
        "industry": "Technology",
        "location": "123 Innovation Drive, San Francisco, CA 94105",
        "business_details": "We provide cloud-based software solutions for enterprise clients. "
                            "Business hours: Monday-Friday 9am-6pm PST. "
                            "24/7 support available for premium customers. "
                            "All our products come with a 30-day money-back guarantee.",
        "website": "https://acme.example.com",
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }


@pytest.fixture
def sample_voice_agent_full():
    """Sample voice agent with all configuration fields."""
    now = datetime.now(timezone.utc)
    return {
        "id": UUID("87654321-4321-8765-4321-876543218765"),
        "organization_id": UUID("12345678-1234-5678-1234-567812345678"),
        "name": "Customer Support Agent",
        "phone_number": "+14155551234",
        "persona": "Professional Customer Support Specialist",
        "tone": "Professional and empathetic",
        "mission": "Provide exceptional customer support by resolving issues quickly "
                  "and ensuring customer satisfaction",
        "custom_instructions": "Always verify customer identity before accessing account details. "
                                "For billing issues, escalate to supervisor if amount exceeds $500. "
                                "Use customer's name in responses when possible.",
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }


@pytest.fixture
def sample_voice_agent_minimal():
    """Sample voice agent with minimal configuration."""
    now = datetime.now(timezone.utc)
    return {
        "id": UUID("11111111-1111-1111-1111-111111111111"),
        "organization_id": UUID("12345678-1234-5678-1234-567812345678"),
        "name": "Basic Agent",
        "phone_number": "+14155555678",
        "persona": None,
        "tone": None,
        "mission": None,
        "custom_instructions": None,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }


class TestPromptBuilderIntegration:
    """Test cases for PromptBuilder integration in worker."""

    @pytest.mark.asyncio
    async def test_prompt_generation_with_full_data(self, sample_organization, sample_voice_agent_full):
        """Test that worker generates complete prompt with full org and agent data."""
        from shared.organization.models import Organization
        from shared.voice_agents.models import VoiceAgent
        from shared.voice_agents.prompt_builder import PromptBuilder

        # Create models from sample data
        org = Organization(**sample_organization)
        agent = VoiceAgent(**sample_voice_agent_full)

        # Generate prompt with default rules
        default_rules = "# RULES\n- Be concise\n- Be helpful"
        prompt = PromptBuilder.build_system_prompt(org, agent, default_rules)

        # Verify all sections are present
        assert "Professional Customer Support Specialist" in prompt
        assert "Acme Corporation" in prompt
        assert "Professional and empathetic" in prompt
        assert "Provide exceptional customer support" in prompt
        assert "Technology" in prompt
        assert "123 Innovation Drive" in prompt
        assert "cloud-based software solutions" in prompt
        assert "verify customer identity" in prompt
        assert "# RULES" in prompt

    @pytest.mark.asyncio
    async def test_prompt_generation_with_minimal_data(self, sample_organization, sample_voice_agent_minimal):
        """Test that worker generates prompt with minimal agent configuration."""
        from shared.organization.models import Organization
        from shared.voice_agents.models import VoiceAgent
        from shared.voice_agents.prompt_builder import PromptBuilder

        # Create models from sample data
        org = Organization(**sample_organization)
        agent = VoiceAgent(**sample_voice_agent_minimal)

        # Generate prompt without default rules
        prompt = PromptBuilder.build_system_prompt(org, agent)

        # Should have default persona
        assert "a helpful AI voice assistant" in prompt
        assert "Acme Corporation" in prompt
        # Should not have sections for missing fields
        assert "YOUR MISSION" not in prompt
        assert "ADDITIONAL INSTRUCTIONS" not in prompt

    @pytest.mark.asyncio
    async def test_prompt_generation_org_fetch_failure(self, mock_job_context, sample_voice_agent_full):
        """Test that worker falls back to default prompt when org fetch fails."""
        from worker import entrypoint
        from default_system_prompt import default_system_prompt

        # Mock voice_agent_service to return agent
        with patch("worker.voice_agent_service") as mock_voice_service:
            mock_voice_service.get_agent_by_phone = AsyncMock(
                return_value=(MagicMock(**sample_voice_agent_full), None)
            )

            # Mock organization_service to simulate failure
            with patch("worker.organization_service") as mock_org_service:
                mock_org_service.get_organization_by_id = AsyncMock(
                    return_value=(None, "Connection timeout")
                )

                # Mock tool_service to return empty tools
                with patch("worker.tool_service") as mock_tool_service:
                    mock_tool_service.get_agent_tools_with_sensitive_config = AsyncMock(
                        return_value=([], None)
                    )

                    # Mock AgentSession and other LiveKit components
                    with patch("worker.AgentSession") as mock_session_class:
                        mock_session = AsyncMock()
                        mock_session_class.return_value = mock_session

                        with patch("worker.build_realtime_model"):
                            with patch("worker.DynamicAgent") as mock_agent_class:
                                mock_agent = MagicMock()
                                # update_tools is awaited in the entrypoint, so it
                                # must return an awaitable (a plain MagicMock would
                                # raise "object MagicMock can't be used in 'await'").
                                mock_agent.update_tools = AsyncMock()
                                mock_agent_class.return_value = mock_agent

                                # Execute entrypoint
                                await entrypoint(mock_job_context)

                                # Verify that DynamicAgent was created with the
                                # fallback instructions: the current-date/time
                                # anchor is prepended to default_system_prompt
                                # (org fetch failed, so no PromptBuilder context).
                                call_args = mock_agent_class.call_args
                                assert call_args is not None
                                instructions = call_args.kwargs.get("instructions", call_args[1].get("instructions"))
                                # The datetime anchor is the first section.
                                assert instructions.startswith("# CURRENT DATE AND TIME")
                                # The guidance text grounds "today"/"tomorrow"/"now".
                                assert "Treat this as the current date and time" in instructions
                                # The default prompt is appended after the anchor.
                                assert default_system_prompt in instructions
                                assert instructions.endswith(default_system_prompt)

    @pytest.mark.asyncio
    async def test_prompt_generation_with_partial_org_data(self, sample_voice_agent_full):
        """Test prompt generation when organization has partial data."""
        from shared.organization.models import Organization
        from shared.voice_agents.models import VoiceAgent
        from shared.voice_agents.prompt_builder import PromptBuilder

        now = datetime.now(timezone.utc)
        # Organization with only industry, no location or business_details
        partial_org_data = {
            "id": UUID("22222222-2222-2222-2222-222222222222"),
            "name": "Minimal Corp",
            "slug": "minimal-corp",
            "description": None,
            "industry": "Consulting",
            "location": None,
            "business_details": None,
            "website": None,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }

        org = Organization(**partial_org_data)
        agent = VoiceAgent(**sample_voice_agent_full)

        prompt = PromptBuilder.build_system_prompt(org, agent)

        # Should include industry
        assert "Industry: Consulting" in prompt
        assert "BUSINESS CONTEXT" in prompt
        # Should not include location or business details sections
        assert "Location/Address:" not in prompt
        assert "Business Context:" not in prompt

    @pytest.mark.asyncio
    async def test_worker_integration_prompt_sections(self, sample_organization, sample_voice_agent_full):
        """Test that worker-generated prompt has correct structure and sections."""
        from shared.organization.models import Organization
        from shared.voice_agents.models import VoiceAgent
        from shared.voice_agents.prompt_builder import PromptBuilder

        org = Organization(**sample_organization)
        agent = VoiceAgent(**sample_voice_agent_full)

        default_rules = """# OUTPUT RULES
- Keep responses under 50 words
- Always be polite
- Ask clarifying questions when needed"""

        prompt = PromptBuilder.build_system_prompt(org, agent, default_rules)

        # Verify prompt structure
        assert "# IDENTITY AND PERSONA" in prompt
        assert "# YOUR MISSION" in prompt
        assert "# BUSINESS CONTEXT" in prompt
        assert "# ADDITIONAL INSTRUCTIONS" in prompt
        assert "# OUTPUT RULES" in prompt

        # Verify section ordering (should be in logical sequence)
        identity_pos = prompt.find("# IDENTITY AND PERSONA")
        mission_pos = prompt.find("# YOUR MISSION")
        business_pos = prompt.find("# BUSINESS CONTEXT")
        instructions_pos = prompt.find("# ADDITIONAL INSTRUCTIONS")
        rules_pos = prompt.find("# OUTPUT RULES")

        assert identity_pos < mission_pos < business_pos < instructions_pos < rules_pos


class TestPromptBuilderEdgeCases:
    """Test edge cases for PromptBuilder integration."""

    @pytest.mark.asyncio
    async def test_organization_name_in_prompt(self):
        """Test that organization name appears correctly in prompt."""
        from shared.organization.models import Organization
        from shared.voice_agents.models import VoiceAgent
        from shared.voice_agents.prompt_builder import PromptBuilder

        now = datetime.now(timezone.utc)
        org = Organization(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            name="Test Organization",
            slug="test-org",
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        agent = VoiceAgent(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            organization_id=org.id,
            name="Test Agent",
            phone_number="+14155551234",
            persona="Assistant",
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        prompt = PromptBuilder.build_system_prompt(org, agent)

        # Should include "representing" phrase with org name
        assert "representing Test Organization" in prompt
        assert "You are Assistant" in prompt

    @pytest.mark.asyncio
    async def test_special_characters_in_fields(self):
        """Test prompt generation handles special characters correctly."""
        from shared.organization.models import Organization
        from shared.voice_agents.models import VoiceAgent
        from shared.voice_agents.prompt_builder import PromptBuilder

        now = datetime.now(timezone.utc)
        org = Organization(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            name="O'Reilly & Associates",
            slug="oreilly",
            business_details="We handle 24/7 support & maintenance. "
                          "Contact: support@example.com or call 1-800-555-0123.",
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        agent = VoiceAgent(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            organization_id=org.id,
            name="Test Agent",
            phone_number="+14155551234",
            persona="Support Agent",
            custom_instructions='Handle "urgent" requests first. Use <script> tags only when necessary.',
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        prompt = PromptBuilder.build_system_prompt(org, agent)

        # Verify special characters are preserved
        assert "O'Reilly & Associates" in prompt
        assert "24/7 support & maintenance" in prompt
        assert "support@example.com" in prompt
        assert "1-800-555-0123" in prompt
        assert 'Handle "urgent" requests first' in prompt
        assert "<script> tags" in prompt

    def test_build_uses_markdown_when_instructions_markdown_set(self, sample_organization):
        """Test that PromptBuilder.build() uses markdown instructions when set."""
        from shared.voice_agents.prompt_builder import PromptBuilder
        from shared.organization.models import Organization
        from shared.voice_agents.models import VoiceAgent

        now = datetime.now(timezone.utc)
        org_data = sample_organization
        org = Organization(**org_data)

        agent = VoiceAgent(
            id=UUID("87654321-4321-8765-4321-876543218765"),
            organization_id=org.id,
            name="Markdown Agent",
            persona="Should NOT appear in prompt",
            instructions_markdown="# Custom Receptionist\n\nYou work at {{org.name}} in {{org.location}}.",
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        default_rules = "# OUTPUT RULES\n- Be concise"

        prompt = PromptBuilder.build(
            org=org,
            agent=agent,
            default_rules=default_rules,
            enabled_tools=["Google_Calendar"],
        )

        # Markdown content used with template vars rendered
        assert "Custom Receptionist" in prompt
        assert "Acme Corporation" in prompt
        assert "123 Innovation Drive" in prompt
        # Field-based persona NOT used
        assert "Should NOT appear" not in prompt
        # Guardrails appended
        assert "SYSTEM GUARDRAILS" in prompt
        # Tool guidelines appended
        assert "Google Calendar Tool Guidelines" in prompt
        # Default rules appended
        assert "OUTPUT RULES" in prompt

    def test_build_with_skills_injects_metadata_only(self, sample_organization):
        """Test that PromptBuilder.build() injects skill metadata, not full content.

        This integration test verifies the full prompt assembly chain with skills:
        agent markdown + skill metadata + guardrails + tool guidelines.
        Skills should appear as a lightweight 'Available Skills' section with
        only slugs and descriptions, not full content (progressive disclosure).
        """
        from shared.voice_agents.prompt_builder import PromptBuilder
        from shared.organization.models import Organization
        from shared.voice_agents.models import VoiceAgent

        now = datetime.now(timezone.utc)
        org = Organization(**sample_organization)

        agent = VoiceAgent(
            id=UUID("87654321-4321-8765-4321-876543218765"),
            organization_id=org.id,
            name="Skilled Agent",
            instructions_markdown="# Receptionist\n\nYou help callers at {{org.name}}.",
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        # Simulate skill summaries (slug + description only)
        class SkillSummary:
            def __init__(self, slug, name, description):
                self.slug = slug
                self.name = name
                self.description = description

        skills = [
            SkillSummary("appointment-booking", "Appointment Booking", "Handle scheduling and cancellations"),
            SkillSummary("call-transfer", "Call Transfer", "Escalate to human agent"),
            SkillSummary("faq-responder", "FAQ Responder", "Answer common questions"),
        ]

        prompt = PromptBuilder.build(
            org=org,
            agent=agent,
            default_rules="# OUTPUT RULES\n- Be concise",
            enabled_tools=["Google_Calendar"],
            agent_skills=skills,
        )

        # Agent markdown rendered
        assert "Receptionist" in prompt
        assert "Acme Corporation" in prompt

        # Skills metadata section present
        assert "AVAILABLE SKILLS" in prompt
        assert "appointment-booking" in prompt
        assert "Handle scheduling" in prompt
        assert "call-transfer" in prompt
        assert "faq-responder" in prompt
        assert "load_skill" in prompt

        # Guardrails present
        assert "SYSTEM GUARDRAILS" in prompt

        # Tool guidelines present
        assert "Google Calendar Tool Guidelines" in prompt

        # Output rules present
        assert "OUTPUT RULES" in prompt

        # Verify ordering: markdown → skills → guardrails → tools → rules
        md_pos = prompt.index("Receptionist")
        skills_pos = prompt.index("AVAILABLE SKILLS")
        guardrails_pos = prompt.index("SYSTEM GUARDRAILS")
        assert md_pos < skills_pos < guardrails_pos

    def test_build_without_skills_has_no_skills_section(self, sample_organization):
        """Test that prompt has no skills section when agent has none assigned."""
        from shared.voice_agents.prompt_builder import PromptBuilder
        from shared.organization.models import Organization
        from shared.voice_agents.models import VoiceAgent

        now = datetime.now(timezone.utc)
        org = Organization(**sample_organization)

        agent = VoiceAgent(
            id=UUID("87654321-4321-8765-4321-876543218765"),
            organization_id=org.id,
            name="No Skills Agent",
            instructions_markdown="# Basic Agent",
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        prompt = PromptBuilder.build(org=org, agent=agent, agent_skills=[])

        assert "AVAILABLE SKILLS" not in prompt
        assert "load_skill" not in prompt
        # Guardrails still present
        assert "SYSTEM GUARDRAILS" in prompt

    def test_build_falls_back_to_fields_when_no_markdown(self, sample_organization):
        """Test that PromptBuilder.build() falls back to field-based when no markdown."""
        from shared.voice_agents.prompt_builder import PromptBuilder
        from shared.organization.models import Organization
        from shared.voice_agents.models import VoiceAgent

        now = datetime.now(timezone.utc)
        org_data = sample_organization
        org = Organization(**org_data)

        agent = VoiceAgent(
            id=UUID("87654321-4321-8765-4321-876543218765"),
            organization_id=org.id,
            name="Field Agent",
            persona="Technical Support Specialist",
            tone="professional",
            mission="Resolve issues quickly",
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        prompt = PromptBuilder.build(org=org, agent=agent)

        # Field-based content used
        assert "Technical Support Specialist" in prompt
        assert "IDENTITY AND PERSONA" in prompt
        assert "Resolve issues quickly" in prompt
