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


# NOTE: TestSkillCategoryValidation was deleted because the ``category``
# field was removed in Phase 2c (commit 9dd430f, "Replace built-in skill
# seeding with immutable platform templates"). The category enum (built_in /
# custom) was superseded by the platform fork model: org skills are always
# "custom", with platform_skills as the source of truth.


class TestSkillCreateModel:
    """Test cases for skill creation model."""

    def test_create_with_all_fields(self):
        skill = OrganizationSkillCreate(
            organization_id=UUID("00000000-0000-0000-0000-000000000001"),
            name="Appointment Booking",
            slug="appointment-booking",
            description="Handle scheduling",
            content="# Appointment Booking\n\n## Procedure\n...",
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


class TestSkillFileCreateModel:
    """Test cases for SkillFileCreate model."""

    def test_create_with_all_fields(self):
        from shared.voice_agents.skill_models import SkillFileCreate

        f = SkillFileCreate(
            file_path="references/policies.md",
            content="# Policies\n\nBe respectful.",
            file_kind="reference",
        )
        assert f.file_path == "references/policies.md"
        assert f.content == "# Policies\n\nBe respectful."
        assert f.file_kind == "reference"

    def test_create_default_file_kind(self):
        from shared.voice_agents.skill_models import SkillFileCreate

        f = SkillFileCreate(file_path="doc.md", content="# Doc")
        assert f.file_kind == "reference"

    def test_create_invalid_file_kind(self):
        from shared.voice_agents.skill_models import SkillFileCreate

        with pytest.raises(ValidationError, match="File kind must be"):
            SkillFileCreate(
                file_path="test.md", content="# Test", file_kind="invalid"
            )

    def test_create_empty_content_raises(self):
        from shared.voice_agents.skill_models import SkillFileCreate

        with pytest.raises(ValidationError):
            SkillFileCreate(file_path="test.md", content="")

    def test_create_empty_path_raises(self):
        from shared.voice_agents.skill_models import SkillFileCreate

        with pytest.raises(ValidationError):
            SkillFileCreate(file_path="", content="# Test")


class TestSkillFileUpdateModel:
    """Test cases for SkillFileUpdate model."""

    def test_update_partial(self):
        from shared.voice_agents.skill_models import SkillFileUpdate

        update = SkillFileUpdate(content="# New content")
        assert update.content == "# New content"
        assert update.file_path is None

    def test_update_path_only(self):
        from shared.voice_agents.skill_models import SkillFileUpdate

        update = SkillFileUpdate(file_path="new/path.md")
        assert update.file_path == "new/path.md"
        assert update.content is None

    def test_update_both(self):
        from shared.voice_agents.skill_models import SkillFileUpdate

        update = SkillFileUpdate(
            file_path="new/path.md", content="# Updated"
        )
        assert update.file_path == "new/path.md"
        assert update.content == "# Updated"


class TestSkillFileModel:
    """Test cases for SkillFile response model."""

    def test_full_file_model(self):
        from shared.voice_agents.skill_models import SkillFile

        f = SkillFile(
            id=UUID("00000000-0000-0000-0000-000000000010"),
            skill_id=UUID("00000000-0000-0000-0000-000000000001"),
            file_path="references/policies.md",
            content="# Policies",
            file_kind="reference",
            content_hash="abc123",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )
        assert f.id == UUID("00000000-0000-0000-0000-000000000010")
        assert f.skill_id == UUID("00000000-0000-0000-0000-000000000001")
        assert f.file_path == "references/policies.md"
        assert f.content == "# Policies"
        assert f.content_hash == "abc123"


class TestSkillFileSummaryModel:
    """Test cases for SkillFileSummary model."""

    def test_summary_no_content(self):
        from shared.voice_agents.skill_models import SkillFileSummary

        s = SkillFileSummary(
            id=UUID("00000000-0000-0000-0000-000000000010"),
            file_path="references/policies.md",
            file_kind="reference",
            content_hash="abc123",
        )
        assert s.file_path == "references/policies.md"
        assert not hasattr(s, "content")


class TestSkillImportRequestModel:
    """Test cases for SkillImportRequest model."""

    def test_valid_url(self):
        from shared.voice_agents.skill_models import SkillImportRequest

        req = SkillImportRequest(url="https://github.com/owner/repo")
        assert req.url == "https://github.com/owner/repo"

    def test_empty_url_raises(self):
        from shared.voice_agents.skill_models import SkillImportRequest

        with pytest.raises(ValidationError):
            SkillImportRequest(url="")


class TestSkillImportResultModel:
    """Test cases for SkillImportResult model."""

    def test_import_result(self):
        from shared.voice_agents.skill_models import (
            SkillImportResult,
            OrganizationSkill,
        )

        skill = OrganizationSkill(
            id=UUID("00000000-0000-0000-0000-000000000010"),
            organization_id=UUID("00000000-0000-0000-0000-000000000001"),
            slug="imported-skill",
            name="Imported Skill",
            content="# Imported",
            is_active=True,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )

        result = SkillImportResult(
            skill=skill,
            files_imported=5,
            source_url="https://github.com/owner/repo/tree/main/skill",
        )
        assert result.skill.slug == "imported-skill"
        assert result.files_imported == 5
        assert "github.com" in result.source_url
