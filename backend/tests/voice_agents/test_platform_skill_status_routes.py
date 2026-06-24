"""Route-level tests for platform-skill status transitions and filter param.

These tests describe the desired HTTP behavior for the new status-enum design.
They should fail until platform_skill_routes.py is updated.
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID

import pytest
from fastapi import HTTPException

from shared.voice_agents.skill_models import (
    PlatformSkill,
    PlatformSkillStatus,
    PlatformSkillSummary,
)

TEST_USER_ID = UUID("00000000-0000-0000-0000-000000000003")
TEST_SKILL_ID = UUID("00000000-0000-0000-0000-000000000100")


def _profile(is_admin: bool) -> Mock:
    p = Mock()
    p.has_role = Mock(return_value=is_admin)
    return p


def _summary(status: PlatformSkillStatus = PlatformSkillStatus.ACTIVE) -> PlatformSkillSummary:
    return PlatformSkillSummary(
        id=TEST_SKILL_ID,
        slug="appointment-booking",
        name="Appointment Booking",
        description="desc",
        version="2026.06.24_1",
        status=status,
    )


def _full_skill(status: PlatformSkillStatus = PlatformSkillStatus.ACTIVE) -> PlatformSkill:
    return PlatformSkill(
        id=TEST_SKILL_ID,
        slug="appointment-booking",
        name="Appointment Booking",
        description="desc",
        content="# Skill",
        version="2026.06.24_1",
        content_hash="hash",
        status=status,
        created_at=datetime(2026, 6, 24),
        updated_at=datetime(2026, 6, 24),
    )


class TestListByStatus:
    """GET /platform/skills?statuses=... filter behavior."""

    @pytest.mark.asyncio
    async def test_default_statuses_is_active_only(self):
        from src.voice_agents.platform_skill_routes import list_platform_skills

        with patch("src.voice_agents.platform_skill_routes.skill_service") as svc:
            svc.list_platform_skills = AsyncMock(return_value=([_summary()], None))
            await list_platform_skills(user_data=(TEST_USER_ID, _profile(is_admin=False)))
        # default must be [ACTIVE]
        called_statuses = svc.list_platform_skills.call_args.kwargs.get("statuses")
        if called_statuses is None:
            called_statuses = svc.list_platform_skills.call_args.args[0]
        assert called_statuses == [PlatformSkillStatus.ACTIVE]

    @pytest.mark.asyncio
    async def test_explicit_statuses_passed_through(self):
        from src.voice_agents.platform_skill_routes import list_platform_skills

        with patch("src.voice_agents.platform_skill_routes.skill_service") as svc:
            svc.list_platform_skills = AsyncMock(return_value=([], None))
            await list_platform_skills(
                statuses=[PlatformSkillStatus.ACTIVE, PlatformSkillStatus.DEPRECATED],
                user_data=(TEST_USER_ID, _profile(is_admin=True)),
            )
        called_statuses = svc.list_platform_skills.call_args.kwargs.get("statuses")
        if called_statuses is None:
            called_statuses = svc.list_platform_skills.call_args.args[0]
        assert called_statuses == [PlatformSkillStatus.ACTIVE, PlatformSkillStatus.DEPRECATED]

    @pytest.mark.asyncio
    async def test_draft_status_requires_admin(self):
        """statuses including DRAFT are admin-only (403 for non-admins)."""
        from src.voice_agents.platform_skill_routes import list_platform_skills

        with patch("src.voice_agents.platform_skill_routes.skill_service") as svc:
            svc.list_platform_skills = AsyncMock(return_value=([], None))
            with pytest.raises(HTTPException) as exc_info:
                await list_platform_skills(
                    statuses=[PlatformSkillStatus.DRAFT],
                    user_data=(TEST_USER_ID, _profile(is_admin=False)),
                )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_deprecated_status_requires_admin(self):
        """statuses including DEPRECATED are admin-only."""
        from src.voice_agents.platform_skill_routes import list_platform_skills

        with patch("src.voice_agents.platform_skill_routes.skill_service") as svc:
            svc.list_platform_skills = AsyncMock(return_value=([], None))
            with pytest.raises(HTTPException) as exc_info:
                await list_platform_skills(
                    statuses=[PlatformSkillStatus.DEPRECATED],
                    user_data=(TEST_USER_ID, _profile(is_admin=False)),
                )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_deleted_status_requires_admin(self):
        """statuses=[DELETED] is admin-only."""
        from src.voice_agents.platform_skill_routes import list_platform_skills

        with patch("src.voice_agents.platform_skill_routes.skill_service") as svc:
            svc.list_platform_skills = AsyncMock(return_value=([], None))
            with pytest.raises(HTTPException) as exc_info:
                await list_platform_skills(
                    statuses=[PlatformSkillStatus.DELETED],
                    user_data=(TEST_USER_ID, _profile(is_admin=False)),
                )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_invalid_status_value_returns_400(self):
        from src.voice_agents.platform_skill_routes import list_platform_skills

        with pytest.raises(HTTPException) as exc_info:
            await list_platform_skills(
                statuses=["archived"],
                user_data=(TEST_USER_ID, _profile(is_admin=True)),
            )
        assert exc_info.value.status_code == 400


class TestDeprecateEndpoint:
    """POST /platform/skills/{id}/deprecate."""

    @pytest.mark.asyncio
    async def test_deprecate_requires_admin(self):
        from src.voice_agents.platform_skill_routes import deprecate_platform_skill

        with pytest.raises(HTTPException) as exc_info:
            await deprecate_platform_skill(
                skill_id=TEST_SKILL_ID,
                user_data=(TEST_USER_ID, _profile(is_admin=False)),
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_deprecate_succeeds_for_admin(self):
        from src.voice_agents.platform_skill_routes import deprecate_platform_skill

        with patch("src.voice_agents.platform_skill_routes.skill_service") as svc:
            svc.deprecate_platform_skill = AsyncMock(
                return_value=(_full_skill(PlatformSkillStatus.DEPRECATED), None)
            )
            result = await deprecate_platform_skill(
                skill_id=TEST_SKILL_ID,
                user_data=(TEST_USER_ID, _profile(is_admin=True)),
            )
        assert result.status == PlatformSkillStatus.DEPRECATED

    @pytest.mark.asyncio
    async def test_deprecate_invalid_transition_returns_400(self):
        from src.voice_agents.platform_skill_routes import deprecate_platform_skill

        with patch("src.voice_agents.platform_skill_routes.skill_service") as svc:
            svc.deprecate_platform_skill = AsyncMock(
                return_value=(None, "Cannot deprecate skill in state 'deleted'")
            )
            with pytest.raises(HTTPException) as exc_info:
                await deprecate_platform_skill(
                    skill_id=TEST_SKILL_ID,
                    user_data=(TEST_USER_ID, _profile(is_admin=True)),
                )
        assert exc_info.value.status_code == 400


class TestReactivateEndpoint:
    """POST /platform/skills/{id}/reactivate."""

    @pytest.mark.asyncio
    async def test_reactivate_requires_admin(self):
        from src.voice_agents.platform_skill_routes import reactivate_platform_skill

        with pytest.raises(HTTPException) as exc_info:
            await reactivate_platform_skill(
                skill_id=TEST_SKILL_ID,
                user_data=(TEST_USER_ID, _profile(is_admin=False)),
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_reactivate_succeeds_for_admin(self):
        from src.voice_agents.platform_skill_routes import reactivate_platform_skill

        with patch("src.voice_agents.platform_skill_routes.skill_service") as svc:
            svc.reactivate_platform_skill = AsyncMock(
                return_value=(_full_skill(PlatformSkillStatus.ACTIVE), None)
            )
            result = await reactivate_platform_skill(
                skill_id=TEST_SKILL_ID,
                user_data=(TEST_USER_ID, _profile(is_admin=True)),
            )
        assert result.status == PlatformSkillStatus.ACTIVE


class TestDeleteRejectsAlreadyDeleted:
    """DELETE from already-DELETED skill returns 400."""

    @pytest.mark.asyncio
    async def test_delete_already_deleted_returns_400(self):
        from src.voice_agents.platform_skill_routes import delete_platform_skill

        with patch("src.voice_agents.platform_skill_routes.skill_service") as svc:
            svc.delete_platform_skill = AsyncMock(return_value=(False, "Skill is already deleted"))
            with pytest.raises(HTTPException) as exc_info:
                await delete_platform_skill(
                    skill_id=TEST_SKILL_ID,
                    user_data=(TEST_USER_ID, _profile(is_admin=True)),
                )
        assert exc_info.value.status_code == 400


class TestRestoreRejectsNonDeleted:
    """Restore from non-DELETED skill returns 400."""

    @pytest.mark.asyncio
    async def test_restore_active_skill_returns_400(self):
        from src.voice_agents.platform_skill_routes import restore_platform_skill

        with patch("src.voice_agents.platform_skill_routes.skill_service") as svc:
            svc.restore_platform_skill = AsyncMock(
                return_value=(None, "Cannot restore skill in state 'active': only deleted skills can be restored")
            )
            with pytest.raises(HTTPException) as exc_info:
                await restore_platform_skill(
                    skill_id=TEST_SKILL_ID,
                    user_data=(TEST_USER_ID, _profile(is_admin=True)),
                )
        assert exc_info.value.status_code == 400
