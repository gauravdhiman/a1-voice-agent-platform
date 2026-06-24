"""Tests for PlatformSkillStatus enum and platform-skill models.

These tests describe the desired behavior of the new status-enum design.
They should fail until shared.voice_agents.skill_models is updated to
include PlatformSkillStatus and the platform-skill fields are refactored.
"""

import pytest
from pydantic import ValidationError

from shared.voice_agents.skill_models import (
    PlatformSkill,
    PlatformSkillBase,
    PlatformSkillCreate,
    PlatformSkillStatus,
    PlatformSkillSummary,
    PlatformSkillUpdate,
)


class TestPlatformSkillStatusEnum:
    """PlatformSkillStatus values and validation."""

    def test_status_values(self):
        """Enum exposes draft, active, deprecated, deleted."""
        assert PlatformSkillStatus.DRAFT.value == "draft"
        assert PlatformSkillStatus.ACTIVE.value == "active"
        assert PlatformSkillStatus.DEPRECATED.value == "deprecated"
        assert PlatformSkillStatus.DELETED.value == "deleted"

    def test_invalid_status_rejected(self):
        """Models reject unknown statuses."""
        with pytest.raises(ValidationError):
            PlatformSkillBase(
                slug="x",
                name="X",
                content="# X",
                status="archived",  # not a valid enum value
            )


class TestPlatformSkillBaseStatus:
    """PlatformSkillBase default status and overrides."""

    def test_default_status_is_active(self):
        base = PlatformSkillBase(slug="x", name="X", content="# X")
        assert base.status == PlatformSkillStatus.ACTIVE

    def test_status_can_be_set_to_draft(self):
        base = PlatformSkillBase(
            slug="x", name="X", content="# X", status=PlatformSkillStatus.DRAFT
        )
        assert base.status == PlatformSkillStatus.DRAFT

    def test_no_is_active_or_is_deleted_fields(self):
        """Legacy boolean fields are gone."""
        base = PlatformSkillBase(slug="x", name="X", content="# X")
        assert not hasattr(base, "is_active") or "is_active" not in base.model_fields
        assert not hasattr(base, "is_deleted") or "is_deleted" not in base.model_fields


class TestPlatformSkillUpdate:
    """PlatformSkillUpdate no longer carries status (transitions are dedicated endpoints)."""

    def test_update_model_has_no_status_field(self):
        assert "status" not in PlatformSkillUpdate.model_fields

    def test_update_partial(self):
        u = PlatformSkillUpdate(content="# Updated")
        assert u.content == "# Updated"
        assert u.name is None
        assert u.description is None


class TestPlatformSkillSummary:
    """PlatformSkillSummary exposes status instead of booleans."""

    def test_default_status_is_active(self):
        from uuid import UUID

        s = PlatformSkillSummary(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            slug="x",
            name="X",
            description=None,
            version="2026.06.24_1",
        )
        assert s.status == PlatformSkillStatus.ACTIVE

    def test_status_round_trip(self):
        from uuid import UUID

        s = PlatformSkillSummary(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            slug="x",
            name="X",
            description=None,
            version="2026.06.24_1",
            status=PlatformSkillStatus.DEPRECATED,
        )
        assert s.status == PlatformSkillStatus.DEPRECATED


class TestPlatformSkillFull:
    """PlatformSkill full model has status, no booleans."""

    def test_full_skill_has_status(self):
        from uuid import UUID

        from datetime import datetime

        s = PlatformSkill(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            slug="x",
            name="X",
            description=None,
            content="# X",
            version="2026.06.24_1",
            content_hash="h",
            status=PlatformSkillStatus.DELETED,
            created_at=datetime(2026, 6, 24),
            updated_at=datetime(2026, 6, 24),
        )
        assert s.status == PlatformSkillStatus.DELETED
