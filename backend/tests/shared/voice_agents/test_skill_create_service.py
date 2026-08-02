"""
Regression tests for SkillService.create_skill.

OrganizationSkillCreate no longer exposes ``category`` / ``source_url`` /
``source_ref`` (removed with the platform-skills fork model). create_skill
must still persist org skills with category='custom' and must not read
those removed attributes (which caused AttributeError → 400 in the UI).
"""

from unittest.mock import MagicMock
from uuid import UUID

import pytest

from shared.voice_agents.skill_models import OrganizationSkillCreate
from shared.voice_agents.skill_service import SkillService


ORG_ID = UUID("00000000-0000-0000-0000-000000000888")


def _ts_with_client():
    ts = SkillService()
    client = MagicMock()
    ts.supabase_config = MagicMock()
    ts.supabase_config.client = client
    return ts, client


def _created_row(**over):
    base = {
        "id": "00000000-0000-0000-0000-000000000777",
        "organization_id": str(ORG_ID),
        "slug": "appointment-booking",
        "name": "Appointment Booking",
        "description": "Books appointments",
        "content": "# Appointment Booking\n\n## When to use\n\n\n## Instructions\n\n",
        "version": None,
        "author": None,
        "content_hash": "abc",
        "category": "custom",
        "is_active": True,
        "is_visible": True,
        "source_skill_id": None,
        "source_version": None,
        "created_at": "2026-07-31T00:00:00Z",
        "updated_at": "2026-07-31T00:00:00Z",
    }
    base.update(over)
    return base


@pytest.mark.asyncio
class TestCreateSkillService:
    """create_skill must work with the current OrganizationSkillCreate shape."""

    async def test_create_skill_succeeds_without_category_on_model(self):
        """Reproduce the UI create path: metadata + starter SKILL.md only."""
        ts, client = _ts_with_client()

        org_table = MagicMock()
        client.table.return_value = org_table

        # Duplicate-slug check: no existing row
        select_chain = org_table.select.return_value
        select_chain.eq.return_value = select_chain
        select_chain.execute.return_value.data = []

        # Insert returns the new row
        insert_chain = org_table.insert.return_value
        insert_chain.execute.return_value.data = [_created_row()]

        skill_data = OrganizationSkillCreate(
            organization_id=ORG_ID,
            slug="appointment-booking",
            name="Appointment Booking",
            description="Books appointments",
            content="# Appointment Booking\n\n## When to use\n\n\n## Instructions\n\n",
        )
        # Pin the contract that triggered the bug: these attrs must not exist.
        assert not hasattr(skill_data, "category")
        assert not hasattr(skill_data, "source_url")
        assert not hasattr(skill_data, "source_ref")

        skill, err = await ts.create_skill(skill_data)

        assert err is None, f"create_skill failed: {err}"
        assert skill is not None
        assert skill.slug == "appointment-booking"
        assert skill.name == "Appointment Booking"

        insert_payload = org_table.insert.call_args.args[0]
        assert insert_payload["category"] == "custom"
        assert "source_url" not in insert_payload
        assert "source_ref" not in insert_payload
        assert insert_payload["slug"] == "appointment-booking"
        assert insert_payload["content"].startswith("# Appointment Booking")

    async def test_create_skill_rejects_duplicate_slug(self):
        ts, client = _ts_with_client()
        org_table = MagicMock()
        client.table.return_value = org_table

        select_chain = org_table.select.return_value
        select_chain.eq.return_value = select_chain
        select_chain.execute.return_value.data = [
            {"id": "existing", "name": "Existing Skill"}
        ]

        skill_data = OrganizationSkillCreate(
            organization_id=ORG_ID,
            slug="appointment-booking",
            name="Appointment Booking",
            content="# Appointment Booking\n",
        )

        skill, err = await ts.create_skill(skill_data)

        assert skill is None
        assert err is not None
        assert "already exists" in err.lower()
        org_table.insert.assert_not_called()
