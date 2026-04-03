"""
Tests for Skill Pydantic models.
"""

import pytest
from pydantic import ValidationError
from uuid import UUID

from shared.voice_agents.skill_models import (
    OrganizationSkillBase,
    OrganizationSkillCreate,
    OrganizationSkillUpdate,
)


class TestSkillSlugValidation:
    """Test cases for skill slug validation."""

    def test_valid_slug(self):
        skill = OrganizationSkillBase(
            name="Test", slug="appointment-booking", content="# Test"
        )
        assert skill.slug == "appointment-booking"

    def test_valid_single_word_slug(self):
        skill = OrganizationSkillBase(
            name="Test", slug="faq", content="# Test"
        )
        assert skill.slug == "faq"

    def test_invalid_slug_uppercase(self):
        with pytest.raises(ValidationError, match="kebab-case"):
            OrganizationSkillBase(
                name="Test", slug="Appointment-Booking", content="# Test"
            )

    def test_invalid_slug_spaces(self):
        with pytest.raises(ValidationError, match="kebab-case"):
            OrganizationSkillBase(
                name="Test", slug="appointment booking", content="# Test"
            )

    def test_invalid_slug_underscores(self):
        with pytest.raises(ValidationError, match="kebab-case"):
            OrganizationSkillBase(
                name="Test", slug="appointment_booking", content="# Test"
            )


class TestSkillCategoryValidation:
    """Test cases for skill category validation."""

    def test_valid_built_in(self):
        skill = OrganizationSkillBase(
            name="Test", slug="test", content="# Test", category="built_in"
        )
        assert skill.category == "built_in"

    def test_valid_custom(self):
        skill = OrganizationSkillBase(
            name="Test", slug="test", content="# Test", category="custom"
        )
        assert skill.category == "custom"

    def test_default_category_is_custom(self):
        skill = OrganizationSkillBase(
            name="Test", slug="test", content="# Test"
        )
        assert skill.category == "custom"

    def test_invalid_category(self):
        with pytest.raises(ValidationError, match="Category must be"):
            OrganizationSkillBase(
                name="Test", slug="test", content="# Test", category="invalid"
            )


class TestSkillCreateModel:
    """Test cases for skill creation model."""

    def test_create_with_all_fields(self):
        skill = OrganizationSkillCreate(
            organization_id=UUID("00000000-0000-0000-0000-000000000001"),
            name="Appointment Booking",
            slug="appointment-booking",
            description="Handle scheduling",
            content="# Appointment Booking\n\n## Procedure\n...",
            category="custom",
            version="1.0.0",
            author="Test Author",
        )
        assert skill.name == "Appointment Booking"
        assert skill.version == "1.0.0"
        assert skill.author == "Test Author"

    def test_create_minimal(self):
        skill = OrganizationSkillCreate(
            organization_id=UUID("00000000-0000-0000-0000-000000000001"),
            name="Test",
            slug="test",
            content="# Test",
        )
        assert skill.category == "custom"
        assert skill.version is None
        assert skill.author is None
        assert skill.content_hash is None


class TestSkillUpdateModel:
    """Test cases for skill update model."""

    def test_update_partial(self):
        update = OrganizationSkillUpdate(content="# Updated content")
        assert update.content == "# Updated content"
        assert update.name is None

    def test_update_is_active(self):
        update = OrganizationSkillUpdate(is_active=False)
        assert update.is_active is False
