"""Service-level tests for platform-skill status transitions and filtering.

These tests describe the desired behavior of the new status-enum design
for the SkillService methods that operate on platform_skills.
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
class TestPlatformSkillListByStatus:
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

    async def test_default_list_filters_to_active_only(self):
        ts, client = _ts_with_client()
        q = await self._list(client, [_row(status="active")])
        await ts.list_platform_skills()
        in_args = [c.args for c in q.in_.call_args_list]
        assert ("status", ["active"]) in in_args

    async def test_admin_can_filter_to_multiple_statuses(self):
        ts, client = _ts_with_client()
        q = await self._list(client, [_row(status="active"), _row(status="deprecated")])
        await ts.list_platform_skills(
            statuses=[PlatformSkillStatus.ACTIVE, PlatformSkillStatus.DEPRECATED]
        )
        in_args = [c.args for c in q.in_.call_args_list]
        assert ("status", ["active", "deprecated"]) in in_args

    async def test_include_deleted_only_returns_deleted(self):
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
        assert "status" in err.lower()

    async def test_unknown_status_rejected(self):
        ts, _ = _ts_with_client()
        skills, err = await ts.list_platform_skills(statuses=["archived"])
        assert skills == []
        assert err is not None


@pytest.mark.asyncio
class TestPlatformSkillStatusTransitions:
    """State-machine transitions: deprecate, reactivate, delete, restore."""

    async def test_deprecate_from_active_succeeds(self):
        ts, client = _ts_with_client()
        # Mock get_platform_skill_by_id to return ACTIVE row
        client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = _row(
            status="active"
        )
        # Mock update call chain
        client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [_row(status="deprecated")]
        skill, err = await ts.deprecate_platform_skill(uuid4())
        assert err is None
        assert skill is not None
        client.table.return_value.update.assert_called_with({"status": "deprecated"})

    async def test_deprecate_from_deleted_rejected(self):
        ts, client = _ts_with_client()
        client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = _row(
            status="deleted"
        )
        skill, err = await ts.deprecate_platform_skill(uuid4())
        assert skill is None
        assert err is not None
        assert "cannot" in err.lower() and "state" in err.lower()

    async def test_reactivate_from_deprecated_succeeds(self):
        ts, client = _ts_with_client()
        client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = _row(
            status="deprecated"
        )
        client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [_row(status="active")]
        skill, err = await ts.reactivate_platform_skill(uuid4())
        assert err is None
        assert skill is not None
        client.table.return_value.update.assert_called_with({"status": "active"})

    async def test_reactivate_from_active_rejected(self):
        ts, client = _ts_with_client()
        client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = _row(
            status="active"
        )
        skill, err = await ts.reactivate_platform_skill(uuid4())
        assert skill is None
        assert err is not None
        assert "cannot" in err.lower() and "state" in err.lower()

    async def test_delete_from_active_succeeds(self):
        ts, client = _ts_with_client()
        # get_platform_skill_by_id returns an active row
        client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = _row(
            status="active"
        )
        ok, err = await ts.delete_platform_skill(uuid4())
        assert ok is True
        assert err is None
        client.table.assert_called_with("platform_skills")
        client.table.return_value.update.assert_called_with({"status": "deleted"})

    async def test_delete_from_deprecated_succeeds(self):
        ts, client = _ts_with_client()
        # get_platform_skill_by_id returns a deprecated row
        client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = _row(
            status="deprecated"
        )
        client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [_row(status="deleted")]
        ok, err = await ts.delete_platform_skill(uuid4())
        assert ok is True
        assert err is None

    async def test_delete_from_deleted_rejected(self):
        ts, client = _ts_with_client()
        client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = _row(
            status="deleted"
        )
        ok, err = await ts.delete_platform_skill(uuid4())
        assert ok is False
        assert err is not None
        assert "already deleted" in err.lower()

    async def test_restore_always_lands_on_active(self):
        ts, client = _ts_with_client()
        # get_platform_skill_by_id returns a deleted row
        client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = _row(
            status="deleted"
        )
        client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [_row(status="active")]
        skill, err = await ts.restore_platform_skill(uuid4())
        assert err is None
        assert skill.status.value == "active"
        client.table.return_value.update.assert_called_with({"status": "active"})

    async def test_restore_from_active_rejected(self):
        ts, client = _ts_with_client()
        # The service must check current status before transitioning
        client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = _row(
            status="active"
        )
        skill, err = await ts.restore_platform_skill(uuid4())
        assert skill is None
        assert err is not None
