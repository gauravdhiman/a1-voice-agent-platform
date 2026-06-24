"""Service-level tests for platform-skill status transitions and filtering.

These tests verify the behavior of the new status-enum design that replaced
the legacy ``is_active``/``is_deleted`` boolean flags. They cover:

* Default listing returns only ACTIVE skills.
* Multiple-status filters (admin-only) work as expected.
* State machine transitions: deprecate/reactivate/delete/restore.
* Invalid transitions are rejected with a meaningful error.

Note: the soft-delete behavior (DELETED state) was previously covered here
under ``is_deleted``. With the new status enum, it lives in
``test_platform_skill_status_service.py`` (delete / restore cases).
"""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from shared.voice_agents.skill_models import PlatformSkillStatus
from shared.voice_agents.skill_service import SkillService


def _ts_with_client():
    ts = SkillService()
    client = MagicMock()
    ts.supabase_config = MagicMock()
    ts.supabase_config.client = client
    return ts, client


def _row(status: str = "active", **over):
    base = {
        "id": "00000000-0000-0000-0000-000000000001",
        "slug": "appointment-booking",
        "name": "Appointment Booking",
        "description": None,
        "content": "# Skill",
        "version": "2026.06.24_1",
        "content_hash": "h",
        "status": status,
        "author": None,
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }
    base.update(over)
    return base


@pytest.mark.asyncio
class TestPlatformSkillDeleteSoft:
    """Soft-delete via the status enum (DELETED state)."""

    async def test_delete_sets_status_deleted(self):
        ts, client = _ts_with_client()
        # get_platform_skill_by_id returns an active row
        client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = _row(
            status="active"
        )
        ok, err = await ts.delete_platform_skill(uuid4())
        assert ok is True and err is None
        client.table.assert_called_with("platform_skills")
        client.table.return_value.update.assert_called_with({"status": "deleted"})

    async def test_delete_returns_false_on_error(self):
        ts, client = _ts_with_client()
        client.table.side_effect = RuntimeError("db down")
        ok, err = await ts.delete_platform_skill(uuid4())
        assert ok is False and err is not None

    async def test_delete_rejects_already_deleted(self):
        ts, client = _ts_with_client()
        client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = _row(
            status="deleted"
        )
        ok, err = await ts.delete_platform_skill(uuid4())
        assert ok is False
        assert "already deleted" in err.lower()


@pytest.mark.asyncio
class TestPlatformSkillRestore:
    """Restore from DELETED to ACTIVE."""

    async def test_restore_sets_status_active(self):
        ts, client = _ts_with_client()
        # get_platform_skill_by_id returns a deleted row
        client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = _row(
            status="deleted"
        )
        client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [_row(status="active")]
        skill, err = await ts.restore_platform_skill(uuid4())
        assert err is None
        assert skill is not None
        assert skill.status == PlatformSkillStatus.ACTIVE
        client.table.return_value.update.assert_called_with({"status": "active"})

    async def test_restore_returns_not_found_when_no_row(self):
        ts, client = _ts_with_client()
        client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = None
        skill, err = await ts.restore_platform_skill(uuid4())
        assert skill is None
        assert err is not None

    async def test_restore_rejects_active_skill(self):
        """Restoring a non-deleted skill returns an error."""
        ts, client = _ts_with_client()
        client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = _row(
            status="active"
        )
        skill, err = await ts.restore_platform_skill(uuid4())
        assert skill is None
        assert "cannot restore" in err.lower()


@pytest.mark.asyncio
class TestPlatformSkillListFiltering:
    """list_platform_skills(statuses=[...]) filter behavior."""

    async def _list(self, client, rows):
        q = MagicMock()
        client.table.return_value = q
        q.select.return_value = q
        q.order.return_value = q
        q.in_.return_value = q
        q.eq.return_value = q
        q.execute.return_value.data = rows
        return q

    async def test_default_filters_to_active_only(self):
        ts, client = _ts_with_client()
        q = await self._list(client, [_row(status="active")])
        await ts.list_platform_skills()
        in_args = [c.args for c in q.in_.call_args_list]
        assert ("status", ["active"]) in in_args

    async def test_admin_can_filter_to_active_and_deprecated(self):
        ts, client = _ts_with_client()
        q = await self._list(client, [_row(status="active"), _row(status="deprecated")])
        await ts.list_platform_skills(
            statuses=[PlatformSkillStatus.ACTIVE, PlatformSkillStatus.DEPRECATED]
        )
        in_args = [c.args for c in q.in_.call_args_list]
        assert ("status", ["active", "deprecated"]) in in_args

    async def test_deleted_only_filter(self):
        ts, client = _ts_with_client()
        q = await self._list(client, [_row(status="deleted")])
        await ts.list_platform_skills(statuses=[PlatformSkillStatus.DELETED])
        in_args = [c.args for c in q.in_.call_args_list]
        assert ("status", ["deleted"]) in in_args

    async def test_empty_statuses_rejected(self):
        ts, _ = _ts_with_client()
        skills, err = await ts.list_platform_skills(statuses=[])
        assert skills == []
        assert err is not None
        assert "non-empty" in err.lower() or "empty" in err.lower()
