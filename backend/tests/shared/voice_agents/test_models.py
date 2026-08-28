"""
Tests for Voice Agent Pydantic models.
"""

from datetime import datetime, timezone
from uuid import UUID

import pytest
from pydantic import ValidationError

from shared.voice_agents.models import (
    VoiceAgent,
    VoiceAgentBase,
    VoiceAgentCreate,
    VoiceAgentUpdate,
)


class TestPhoneNumberValidation:
    """Test cases for phone number E.164 validation."""

    def test_valid_us_phone_number(self):
        """Test valid US phone number passes validation."""
        agent = VoiceAgentBase(name="Test", phone_number="+14155551234")
        assert agent.phone_number == "+14155551234"

    def test_valid_uk_phone_number(self):
        """Test valid UK phone number passes validation."""
        agent = VoiceAgentBase(name="Test", phone_number="+441632960000")
        assert agent.phone_number == "+441632960000"

    def test_phone_number_with_spaces_is_normalized_to_e164(self):
        """Allow human-formatted spaces while storing canonical E.164."""
        agent = VoiceAgentBase(name="Test", phone_number="+1 480 745 2168")
        assert agent.phone_number == "+14807452168"

    def test_phone_number_with_leading_and_repeated_whitespace_is_normalized(self):
        """Normalize tabs, newlines, and repeated whitespace before constraints."""
        agent = VoiceAgentBase(name="Test", phone_number=" \t+1  480\n745 2168 ")
        assert agent.phone_number == "+14807452168"

    def test_update_phone_number_with_spaces_is_normalized_to_e164(self):
        """Apply the same canonicalization when editing an existing agent."""
        update = VoiceAgentUpdate(phone_number="+1 480 745 2168")
        assert update.phone_number == "+14807452168"

    def test_none_phone_number_allowed(self):
        """Test None phone number is allowed (agent without phone)."""
        agent = VoiceAgentBase(name="Test", phone_number=None)
        assert agent.phone_number is None

    def test_empty_string_phone_number_becomes_none(self):
        """Test empty string phone number is converted to None."""
        agent = VoiceAgentBase(name="Test", phone_number="")
        assert agent.phone_number is None

    def test_whitespace_only_phone_number_becomes_none(self):
        """Whitespace-only optional phone numbers are treated as empty."""
        agent = VoiceAgentBase(name="Test", phone_number=" \t\n")
        assert agent.phone_number is None

    def test_missing_phone_number_defaults_to_none(self):
        """Test omitted phone number defaults to None."""
        agent = VoiceAgentBase(name="Test")
        assert agent.phone_number is None

    def test_invalid_phone_number_no_plus(self):
        """Test phone number without + prefix is rejected."""
        with pytest.raises(ValidationError, match="E.164 format"):
            VoiceAgentBase(name="Test", phone_number="14155551234")

    def test_invalid_phone_number_too_short(self):
        """Test phone number that is too short is rejected."""
        with pytest.raises(ValidationError, match="E.164 format"):
            VoiceAgentBase(name="Test", phone_number="+123")

    def test_invalid_phone_number_letters(self):
        """Test phone number with letters is rejected."""
        with pytest.raises(ValidationError, match="E.164 format"):
            VoiceAgentBase(name="Test", phone_number="+1415abc1234")


class TestInstructionsMarkdown:
    """Test cases for instructions_markdown field."""

    def test_instructions_markdown_default_none(self):
        """Test instructions_markdown defaults to None."""
        agent = VoiceAgentBase(name="Test")
        assert agent.instructions_markdown is None

    def test_instructions_markdown_with_content(self):
        """Test instructions_markdown accepts markdown content."""
        md = "# Agent\n\nYou are a receptionist for {{org.name}}."
        agent = VoiceAgentBase(name="Test", instructions_markdown=md)
        assert agent.instructions_markdown == md

    def test_instructions_markdown_with_template_vars(self):
        """Test instructions_markdown preserves template variables as-is."""
        md = "Industry: {{org.industry}}\nLocation: {{org.location}}"
        agent = VoiceAgentBase(name="Test", instructions_markdown=md)
        assert "{{org.industry}}" in agent.instructions_markdown
        assert "{{org.location}}" in agent.instructions_markdown

    def test_create_model_includes_instructions_markdown(self):
        """Test VoiceAgentCreate accepts instructions_markdown."""
        agent = VoiceAgentCreate(
            name="Test Agent",
            organization_id=UUID("00000000-0000-0000-0000-000000000001"),
            instructions_markdown="# Test\n\nInstructions here.",
        )
        assert agent.instructions_markdown == "# Test\n\nInstructions here."

    def test_update_model_includes_instructions_markdown(self):
        """Test VoiceAgentUpdate accepts instructions_markdown."""
        update = VoiceAgentUpdate(instructions_markdown="# Updated instructions")
        assert update.instructions_markdown == "# Updated instructions"

    def test_voice_agent_response_includes_instructions_markdown(self):
        """Test VoiceAgent response model includes instructions_markdown."""
        now = datetime.now(timezone.utc)
        agent = VoiceAgent(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            organization_id=UUID("00000000-0000-0000-0000-000000000002"),
            name="Test",
            is_active=True,
            instructions_markdown="# My Agent",
            created_at=now,
            updated_at=now,
        )
        assert agent.instructions_markdown == "# My Agent"

    def test_voice_agent_without_markdown_falls_back(self):
        """Test VoiceAgent works without instructions_markdown (backward compat)."""
        now = datetime.now(timezone.utc)
        agent = VoiceAgent(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            organization_id=UUID("00000000-0000-0000-0000-000000000002"),
            name="Test",
            persona="A helpful assistant",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        assert agent.instructions_markdown is None
        assert agent.persona == "A helpful assistant"


class TestCallRecording:
    """Test cases for the per-agent call recording preference."""

    def test_call_recording_is_disabled_by_default(self):
        """New agents must not record calls unless explicitly enabled."""
        agent = VoiceAgentBase(name="Test")

        assert agent.call_recording_enabled is False

    def test_update_model_accepts_call_recording_preference(self):
        """Editing an agent can explicitly enable or disable recording."""
        update = VoiceAgentUpdate(call_recording_enabled=True)

        assert update.call_recording_enabled is True


class TestPublicAgentConfiguration:
    """Validate public organization and demo-agent model fields."""

    def test_public_and_demo_fields_default_to_private(self):
        """New agents must remain private and non-demo by default."""
        agent = VoiceAgentBase(name="Test")

        assert agent.is_published_on_public_page is False
        assert agent.is_demo is False
        assert agent.demo_slug is None
        assert agent.public_description is None
        assert agent.demo_calls_remaining == -1
        assert agent.demo_max_call_duration_seconds == -1

    def test_demo_limits_accept_finite_and_unlimited_values(self):
        from shared.voice_agents.models import VoiceAgentBase, VoiceAgentUpdate

        base = VoiceAgentBase(
            name="Demo",
            demo_calls_remaining=3,
            demo_max_call_duration_seconds=600,
        )
        update = VoiceAgentUpdate(
            demo_calls_remaining=0,
            demo_max_call_duration_seconds=-1,
        )

        assert base.demo_calls_remaining == 3
        assert base.demo_max_call_duration_seconds == 600
        assert update.demo_calls_remaining == 0
        assert update.demo_max_call_duration_seconds == -1

    def test_demo_max_call_duration_rejects_zero_and_negative_values(self):
        from shared.voice_agents.models import VoiceAgentBase, VoiceAgentUpdate

        with pytest.raises(ValueError, match="Demo max call duration"):
            VoiceAgentBase(name="Demo", demo_max_call_duration_seconds=0)
        with pytest.raises(ValueError):
            VoiceAgentUpdate(demo_max_call_duration_seconds=-2)

    def test_demo_slug_is_normalized_for_create_and_update(self):
        """Demo slugs are lowercased and whitespace becomes hyphens."""
        created = VoiceAgentCreate(
            name="Demo",
            organization_id=UUID("00000000-0000-0000-0000-000000000001"),
            is_demo=True,
            demo_slug="  Acme Dental Demo  ",
        )
        updated = VoiceAgentUpdate(demo_slug="  Follow Up Demo  ")

        assert created.demo_slug == "acme-dental-demo"
        assert updated.demo_slug == "follow-up-demo"

    @pytest.mark.parametrize(
        "slug",
        ["a", "has_underscore", "has/slash", "has.dot", "x" * 101],
    )
    def test_demo_slug_rejects_invalid_values(self, slug):
        """Demo slugs must use the documented URL-safe format and length."""
        with pytest.raises(ValidationError, match="Demo slug"):
            VoiceAgentBase(name="Demo", demo_slug=slug)

    def test_public_description_is_trimmed_and_supported_on_update(self):
        """Marketing copy is trimmed and can be changed independently."""
        agent = VoiceAgentBase(
            name="Demo",
            public_description="  A helpful public description.  ",
        )
        update = VoiceAgentUpdate(public_description="  Updated copy.  ")

        assert agent.public_description == "A helpful public description."
        assert update.public_description == "Updated copy."

    def test_blank_public_demo_fields_are_normalized_to_none(self):
        """Blank optional demo metadata can clear an existing value."""
        agent = VoiceAgentBase(name="Demo", demo_slug="", public_description="")
        update = VoiceAgentUpdate(demo_slug="", public_description="")

        assert agent.demo_slug is None
        assert agent.public_description is None
        assert update.demo_slug is None
        assert update.public_description is None

    def test_public_description_rejects_oversized_create_and_update_values(self):
        """Public copy has the same length limit on create and update."""
        with pytest.raises(ValidationError, match="Public description"):
            VoiceAgentBase(name="Demo", public_description="x" * 1001)
        with pytest.raises(ValidationError, match="Public description"):
            VoiceAgentUpdate(public_description="x" * 1001)

    def test_update_demo_slug_rejects_invalid_and_too_short_values(self):
        """Updates enforce the same URL-safe demo slug contract as creates."""
        with pytest.raises(ValidationError, match="Demo slug"):
            VoiceAgentUpdate(demo_slug="has_underscore")
        with pytest.raises(ValidationError, match="Demo slug"):
            VoiceAgentUpdate(demo_slug="a")

    def test_update_demo_duration_rejects_zero(self):
        """Zero is not a valid finite per-call duration."""
        with pytest.raises(ValidationError, match="Demo max call duration"):
            VoiceAgentUpdate(demo_max_call_duration_seconds=0)
