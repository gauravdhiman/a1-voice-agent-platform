"""
Tests for PromptBuilder service.
"""

from datetime import datetime, timezone
from uuid import UUID

import pytest
from shared.organization.models import Organization
from shared.voice_agents.models import VoiceAgent
from shared.voice_agents.prompt_builder import PromptBuilder


class TestPromptBuilder:
    """Test cases for PromptBuilder."""

    def test_build_system_prompt_complete(self):
        """Test building system prompt with all fields populated."""
        now = datetime.now(timezone.utc)
        org = Organization(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            name="Test Company",
            slug="test-company",
            industry="Technology",
            location="123 Tech Street, San Francisco, CA",
            business_details="We provide cloud computing solutions for enterprise clients.",
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        agent = VoiceAgent(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            organization_id=org.id,
            name="Support Agent",
            phone_number="+14155551234",
            persona="Technical Support Specialist",
            tone="professional and friendly",
            mission="Help customers resolve technical issues quickly",
            custom_instructions="Always verify account details before discussing sensitive information",
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        default_rules = "# RULES\n- Be helpful\n- Be concise"

        prompt = PromptBuilder.build_system_prompt(org, agent, default_rules)

        # Verify all sections are present
        assert "Technical Support Specialist" in prompt
        assert "Test Company" in prompt
        assert "professional and friendly" in prompt
        assert "Help customers resolve" in prompt
        assert "Technology" in prompt
        assert "123 Tech Street" in prompt
        assert "cloud computing solutions" in prompt
        assert "verify account details" in prompt
        assert "# RULES" in prompt

    def test_build_system_prompt_minimal(self):
        """Test building system prompt with minimal fields."""
        now = datetime.now(timezone.utc)
        org = Organization(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            name="Test Company",
            slug="test-company",
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        agent = VoiceAgent(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            organization_id=org.id,
            name="Basic Agent",
            phone_number="+14155551234",
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        prompt = PromptBuilder.build_system_prompt(org, agent)

        # Should have default persona
        assert "a helpful AI voice assistant" in prompt
        # Should not have sections for missing fields
        assert "YOUR MISSION" not in prompt
        assert "BUSINESS CONTEXT" not in prompt
        assert "ADDITIONAL INSTRUCTIONS" not in prompt

    def test_build_system_prompt_no_default_rules(self):
        """Test building system prompt without default rules."""
        now = datetime.now(timezone.utc)
        org = Organization(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            name="Test Company",
            slug="test-company",
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        agent = VoiceAgent(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            organization_id=org.id,
            name="Agent",
            phone_number="+14155551234",
            persona="Sales Rep",
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        prompt = PromptBuilder.build_system_prompt(org, agent, default_rules=None)

        assert "Sales Rep" in prompt
        assert "Test Company" in prompt
        # No rules section when default_rules is None
        assert "# OUTPUT RULES" not in prompt

    def test_build_from_markdown_with_template_vars(self):
        """Test markdown prompt building with template variable rendering."""
        now = datetime.now(timezone.utc)
        org = Organization(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            name="Pleasant Pediatrics",
            slug="pleasant-pediatrics",
            industry="dental",
            location="Phoenix, AZ",
            business_details="Family dental office",
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        agent = VoiceAgent(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            organization_id=org.id,
            name="Receptionist",
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        markdown = "You are a receptionist at {{org.name}} in {{org.location}}.\nIndustry: {{org.industry}}\nAgent: {{agent.name}}"
        prompt = PromptBuilder.build_from_markdown(org, agent, markdown)

        assert "Pleasant Pediatrics" in prompt
        assert "Phoenix, AZ" in prompt
        assert "dental" in prompt
        assert "Receptionist" in prompt
        # Guardrails always appended
        assert "SYSTEM GUARDRAILS" in prompt

    def test_build_from_markdown_missing_vars_render_empty(self):
        """Test that unresolved template vars render as empty strings."""
        now = datetime.now(timezone.utc)
        org = Organization(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            name="Test Co",
            slug="test",
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        agent = VoiceAgent(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            organization_id=org.id,
            name="Agent",
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        markdown = "Location: {{org.location}}, Details: {{org.business_details}}"
        prompt = PromptBuilder.build_from_markdown(org, agent, markdown)

        assert "Location: , Details: " in prompt

    def test_build_from_markdown_includes_tool_guidelines(self):
        """Test that tool guidelines are appended in markdown mode."""
        now = datetime.now(timezone.utc)
        org = Organization(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            name="Test",
            slug="test",
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        agent = VoiceAgent(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            organization_id=org.id,
            name="Agent",
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        markdown = "# My Agent"
        prompt = PromptBuilder.build_from_markdown(
            org, agent, markdown, enabled_tools=["Google_Calendar"]
        )

        assert "Google Calendar Tool Guidelines" in prompt

    def test_build_routes_to_markdown_when_set(self):
        """Test that build() uses markdown when instructions_markdown is set."""
        now = datetime.now(timezone.utc)
        org = Organization(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            name="Test Co",
            slug="test",
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        agent = VoiceAgent(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            organization_id=org.id,
            name="Agent",
            persona="Should NOT appear",
            instructions_markdown="# Custom Instructions\n\nThis is my agent at {{org.name}}.",
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        prompt = PromptBuilder.build(org, agent)

        # Should use markdown content, not field-based
        assert "Custom Instructions" in prompt
        assert "This is my agent at Test Co" in prompt
        # Field-based persona should NOT be assembled
        assert "Should NOT appear" not in prompt

    def test_build_falls_back_to_fields_when_no_markdown(self):
        """Test that build() uses field-based when no markdown is set."""
        now = datetime.now(timezone.utc)
        org = Organization(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            name="Test Co",
            slug="test",
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        agent = VoiceAgent(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            organization_id=org.id,
            name="Agent",
            persona="Sales Rep",
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        prompt = PromptBuilder.build(org, agent)

        # Should use field-based builder
        assert "Sales Rep" in prompt
        assert "IDENTITY AND PERSONA" in prompt

    def test_build_injects_skill_metadata_in_markdown_mode(self):
        """Test that skill summaries are injected as metadata in markdown mode."""
        now = datetime.now(timezone.utc)
        org = Organization(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            name="Test Co",
            slug="test",
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        agent = VoiceAgent(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            organization_id=org.id,
            name="Agent",
            instructions_markdown="# My Agent",
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        # Simulate skill summaries (like OrganizationSkillSummary)
        class SkillSummary:
            def __init__(self, slug, name, description):
                self.slug = slug
                self.name = name
                self.description = description

        skills = [
            SkillSummary("appointment-booking", "Appointment Booking", "Handle scheduling"),
            SkillSummary("call-transfer", "Call Transfer", "Escalate to human"),
        ]

        prompt = PromptBuilder.build(org, agent, agent_skills=skills)

        # Skill metadata should be present
        assert "AVAILABLE SKILLS" in prompt
        assert "appointment-booking" in prompt
        assert "Handle scheduling" in prompt
        assert "call-transfer" in prompt
        assert "load_skill" in prompt
        # Full skill content should NOT be present (progressive disclosure)
        assert "# Appointment Booking" not in prompt.split("AVAILABLE SKILLS")[1].split("SYSTEM GUARDRAILS")[0]

    def test_build_no_skills_section_when_empty(self):
        """Test that no skills section appears when agent has no skills."""
        now = datetime.now(timezone.utc)
        org = Organization(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            name="Test Co",
            slug="test",
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        agent = VoiceAgent(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            organization_id=org.id,
            name="Agent",
            instructions_markdown="# My Agent",
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        prompt = PromptBuilder.build(org, agent, agent_skills=None)
        assert "AVAILABLE SKILLS" not in prompt

        prompt2 = PromptBuilder.build(org, agent, agent_skills=[])
        assert "AVAILABLE SKILLS" not in prompt2

    def test_build_system_prompt_business_context_partial(self):
        """Test business context section with only some fields."""
        now = datetime.now(timezone.utc)
        org = Organization(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            name="Test Company",
            slug="test-company",
            industry="Retail",
            # No location or business_details
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        agent = VoiceAgent(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            organization_id=org.id,
            name="Agent",
            phone_number="+14155551234",
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        prompt = PromptBuilder.build_system_prompt(org, agent)

        # Should have business context with just industry
        assert "Industry: Retail" in prompt
        assert "BUSINESS CONTEXT" in prompt
