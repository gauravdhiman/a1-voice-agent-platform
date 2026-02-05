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
