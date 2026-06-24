"""
Tests for platform skill API routes (platform admin management).

Covers authorization: read (active) is open to any authenticated user, while
listing inactive skills and all create/update/delete/file operations are
restricted to platform admins. Both the 403 path (non-admin) and the success
path (platform admin) are exercised.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID

from fastapi import HTTPException

from shared.voice_agents.skill_models import (
    PlatformSkill,
    PlatformSkillCreate,
    PlatformSkillFile,
    PlatformSkillFileCreate,
    PlatformSkillFileSummary,
    PlatformSkillStatus,
    PlatformSkillSummary,
    PlatformSkillUpdate,
)

TEST_USER_ID = UUID("00000000-0000-0000-0000-000000000003")
TEST_SKILL_ID = UUID("00000000-0000-0000-0000-000000000100")
TEST_FILE_ID = UUID("00000000-0000-0000-0000-000000000200")


def _profile(is_admin: bool) -> Mock:
    """Build a mock UserProfile whose has_role reports platform_admin or not."""
    p = Mock()
    p.has_role = Mock(return_value=is_admin)
    return p


def _summary(status: PlatformSkillStatus = PlatformSkillStatus.ACTIVE) -> PlatformSkillSummary:
    return PlatformSkillSummary(
        id=TEST_SKILL_ID,
        slug="appointment-booking",
        name="Appointment Booking",
        description="desc",
        version="2026.06.19_1",
        status=status,
    )


def _full_skill(status: PlatformSkillStatus = PlatformSkillStatus.ACTIVE) -> PlatformSkill:
    return PlatformSkill(
        id=TEST_SKILL_ID,
        slug="appointment-booking",
        name="Appointment Booking",
        description="desc",
        content="# Skill",
        version="2026.06.19_1",
        content_hash="hash",
        status=status,
        created_at=datetime(2026, 6, 19),
        updated_at=datetime(2026, 6, 19),
    )


def _file_summary() -> PlatformSkillFileSummary:
    return PlatformSkillFileSummary(
        id=TEST_FILE_ID,
        file_path="references/faqs.md",
        file_kind="reference",
        content_hash="hash",
    )


def _file() -> PlatformSkillFile:
    return PlatformSkillFile(
        id=TEST_FILE_ID,
        skill_id=TEST_SKILL_ID,
        file_path="references/faqs.md",
        content="# FAQs",
        file_kind="reference",
        content_hash="hash",
        created_at=datetime(2026, 6, 19),
        updated_at=datetime(2026, 6, 19),
    )


class TestPlatformSkillRoutesAuthz:
    """Authorization tests for platform skill management routes."""

    @pytest.mark.asyncio
    async def test_list_active_open_to_any_authenticated_user(self):
        """Default list (active only) is available to non-admins."""
        from src.voice_agents.platform_skill_routes import list_platform_skills

        with patch(
            "src.voice_agents.platform_skill_routes.skill_service"
        ) as mock_service:
            mock_service.list_platform_skills = AsyncMock(
                return_value=([_summary()], None)
            )
            result = await list_platform_skills(
                user_data=(TEST_USER_ID, _profile(is_admin=False)),
            )
        assert len(result) == 1
        # default must be [ACTIVE]
        called = mock_service.list_platform_skills.call_args
        called_statuses = called.kwargs.get("statuses") or (called.args[0] if called.args else None)
        assert called_statuses == [PlatformSkillStatus.ACTIVE]

    @pytest.mark.asyncio
    async def test_list_deprecated_requires_platform_admin(self):
        """statuses including DEPRECATED is forbidden for non-admins (403)."""
        from src.voice_agents.platform_skill_routes import list_platform_skills

        with patch(
            "src.voice_agents.platform_skill_routes.skill_service"
        ) as mock_service:
            mock_service.list_platform_skills = AsyncMock(
                return_value=([_summary(PlatformSkillStatus.DEPRECATED), _summary()], None)
            )
            with pytest.raises(HTTPException) as exc_info:
                await list_platform_skills(
                    statuses=[PlatformSkillStatus.ACTIVE, PlatformSkillStatus.DEPRECATED],
                    user_data=(TEST_USER_ID, _profile(is_admin=False)),
                )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_list_multiple_statuses_succeeds_for_platform_admin(self):
        """statuses=[active, deprecated] returns both for platform admins."""
        from src.voice_agents.platform_skill_routes import list_platform_skills

        with patch(
            "src.voice_agents.platform_skill_routes.skill_service"
        ) as mock_service:
            mock_service.list_platform_skills = AsyncMock(
                return_value=(
                    [_summary(PlatformSkillStatus.DEPRECATED), _summary()],
                    None,
                )
            )
            result = await list_platform_skills(
                statuses=[PlatformSkillStatus.ACTIVE, PlatformSkillStatus.DEPRECATED],
                user_data=(TEST_USER_ID, _profile(is_admin=True)),
            )
        assert len(result) == 2
        called = mock_service.list_platform_skills.call_args
        called_statuses = called.kwargs.get("statuses") or (called.args[0] if called.args else None)
        assert called_statuses == [
            PlatformSkillStatus.ACTIVE,
            PlatformSkillStatus.DEPRECATED,
        ]

    @pytest.mark.asyncio
    async def test_get_platform_skill_requires_platform_admin(self):
        """Getting a full platform skill is admin-only (403 for non-admin)."""
        from src.voice_agents.platform_skill_routes import get_platform_skill

        with pytest.raises(HTTPException) as exc_info:
            await get_platform_skill(
                skill_id=TEST_SKILL_ID,
                user_data=(TEST_USER_ID, _profile(is_admin=False)),
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_get_platform_skill_succeeds_for_admin(self):
        from src.voice_agents.platform_skill_routes import get_platform_skill

        with patch(
            "src.voice_agents.platform_skill_routes.skill_service"
        ) as mock_service:
            mock_service.get_platform_skill_by_id = AsyncMock(
                return_value=(_full_skill(), None)
            )
            result = await get_platform_skill(
                skill_id=TEST_SKILL_ID,
                user_data=(TEST_USER_ID, _profile(is_admin=True)),
            )
        assert result.slug == "appointment-booking"

    @pytest.mark.asyncio
    async def test_create_platform_skill_requires_platform_admin(self):
        from src.voice_agents.platform_skill_routes import create_platform_skill

        payload = PlatformSkillCreate(
            slug="new-skill", name="New Skill", content="# New"
        )
        with pytest.raises(HTTPException) as exc_info:
            await create_platform_skill(
                skill_data=payload,
                user_data=(TEST_USER_ID, _profile(is_admin=False)),
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_create_platform_skill_succeeds_for_admin(self):
        from src.voice_agents.platform_skill_routes import create_platform_skill

        payload = PlatformSkillCreate(
            slug="new-skill", name="New Skill", content="# New"
        )
        with patch(
            "src.voice_agents.platform_skill_routes.skill_service"
        ) as mock_service:
            mock_service.create_platform_skill = AsyncMock(
                return_value=(_full_skill(), None)
            )
            result = await create_platform_skill(
                skill_data=payload,
                user_data=(TEST_USER_ID, _profile(is_admin=True)),
            )
        assert result.slug == "appointment-booking"
        mock_service.create_platform_skill.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_platform_skill_requires_platform_admin(self):
        from src.voice_agents.platform_skill_routes import update_platform_skill

        payload = PlatformSkillUpdate(name="Renamed")
        with pytest.raises(HTTPException) as exc_info:
            await update_platform_skill(
                skill_id=TEST_SKILL_ID,
                skill_data=payload,
                user_data=(TEST_USER_ID, _profile(is_admin=False)),
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_update_platform_skill_succeeds_for_admin(self):
        from src.voice_agents.platform_skill_routes import update_platform_skill

        payload = PlatformSkillUpdate(name="Renamed")
        with patch(
            "src.voice_agents.platform_skill_routes.skill_service"
        ) as mock_service:
            mock_service.update_platform_skill = AsyncMock(
                return_value=(_full_skill(), None)
            )
            await update_platform_skill(
                skill_id=TEST_SKILL_ID,
                skill_data=payload,
                user_data=(TEST_USER_ID, _profile(is_admin=True)),
            )
        mock_service.update_platform_skill.assert_awaited_once_with(
            TEST_SKILL_ID, payload
        )

    @pytest.mark.asyncio
    async def test_delete_platform_skill_requires_platform_admin(self):
        from src.voice_agents.platform_skill_routes import delete_platform_skill

        with pytest.raises(HTTPException) as exc_info:
            await delete_platform_skill(
                skill_id=TEST_SKILL_ID,
                user_data=(TEST_USER_ID, _profile(is_admin=False)),
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_platform_skill_succeeds_for_admin(self):
        from src.voice_agents.platform_skill_routes import delete_platform_skill

        with patch(
            "src.voice_agents.platform_skill_routes.skill_service"
        ) as mock_service:
            mock_service.delete_platform_skill = AsyncMock(return_value=(True, None))
            await delete_platform_skill(
                skill_id=TEST_SKILL_ID,
                user_data=(TEST_USER_ID, _profile(is_admin=True)),
            )
        mock_service.delete_platform_skill.assert_awaited_once_with(TEST_SKILL_ID)

    # ───── Files ─────

    @pytest.mark.asyncio
    async def test_list_files_requires_platform_admin(self):
        from src.voice_agents.platform_skill_routes import list_platform_skill_files

        with pytest.raises(HTTPException) as exc_info:
            await list_platform_skill_files(
                skill_id=TEST_SKILL_ID,
                user_data=(TEST_USER_ID, _profile(is_admin=False)),
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_create_file_requires_platform_admin(self):
        from src.voice_agents.platform_skill_routes import create_platform_skill_file

        payload = PlatformSkillFileCreate(file_path="references/x.md", content="# X")
        with pytest.raises(HTTPException) as exc_info:
            await create_platform_skill_file(
                skill_id=TEST_SKILL_ID,
                file_data=payload,
                user_data=(TEST_USER_ID, _profile(is_admin=False)),
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_update_file_requires_platform_admin(self):
        from src.voice_agents.platform_skill_routes import update_platform_skill_file

        payload = PlatformSkillFileCreate(file_path="references/x.md", content="# X2")
        with pytest.raises(HTTPException) as exc_info:
            await update_platform_skill_file(
                skill_id=TEST_SKILL_ID,
                file_id=TEST_FILE_ID,
                file_data=payload,
                user_data=(TEST_USER_ID, _profile(is_admin=False)),
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_file_requires_platform_admin(self):
        from src.voice_agents.platform_skill_routes import delete_platform_skill_file

        with pytest.raises(HTTPException) as exc_info:
            await delete_platform_skill_file(
                skill_id=TEST_SKILL_ID,
                file_id=TEST_FILE_ID,
                user_data=(TEST_USER_ID, _profile(is_admin=False)),
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_create_file_succeeds_for_admin(self):
        from src.voice_agents.platform_skill_routes import create_platform_skill_file

        payload = PlatformSkillFileCreate(file_path="references/x.md", content="# X")
        with patch(
            "src.voice_agents.platform_skill_routes.skill_service"
        ) as mock_service:
            mock_service.create_platform_skill_file = AsyncMock(
                return_value=(_file(), None)
            )
            result = await create_platform_skill_file(
                skill_id=TEST_SKILL_ID,
                file_data=payload,
                user_data=(TEST_USER_ID, _profile(is_admin=True)),
            )
        assert result.file_path == "references/faqs.md"

    # ─── Trash bin: list deleted-only (admin only) ─────

    @pytest.mark.asyncio
    async def test_list_deleted_only_requires_platform_admin(self):
        """statuses=[DELETED] is forbidden for non-admins (403)."""
        from src.voice_agents.platform_skill_routes import list_platform_skills

        with patch(
            "src.voice_agents.platform_skill_routes.skill_service"
        ) as mock_service:
            mock_service.list_platform_skills = AsyncMock(return_value=([], None))
            with pytest.raises(HTTPException) as exc_info:
                await list_platform_skills(
                    statuses=[PlatformSkillStatus.DELETED],
                    user_data=(TEST_USER_ID, _profile(is_admin=False)),
                )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_list_deleted_only_succeeds_for_admin(self):
        """statuses=[DELETED] returns deleted skills for admins."""
        from src.voice_agents.platform_skill_routes import list_platform_skills

        with patch(
            "src.voice_agents.platform_skill_routes.skill_service"
        ) as mock_service:
            mock_service.list_platform_skills = AsyncMock(return_value=([], None))
            await list_platform_skills(
                statuses=[PlatformSkillStatus.DELETED],
                user_data=(TEST_USER_ID, _profile(is_admin=True)),
            )
        called = mock_service.list_platform_skills.call_args
        called_statuses = called.kwargs.get("statuses") or (called.args[0] if called.args else None)
        assert called_statuses == [PlatformSkillStatus.DELETED]

    @pytest.mark.asyncio
    async def test_restore_requires_platform_admin(self):
        """Restoring a soft-deleted skill is platform-admin only (403 otherwise)."""
        from src.voice_agents.platform_skill_routes import restore_platform_skill

        with pytest.raises(HTTPException) as exc_info:
            await restore_platform_skill(
                skill_id=TEST_SKILL_ID,
                user_data=(TEST_USER_ID, _profile(is_admin=False)),
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_restore_succeeds_for_admin(self):
        from src.voice_agents.platform_skill_routes import restore_platform_skill

        with patch(
            "src.voice_agents.platform_skill_routes.skill_service"
        ) as mock_service:
            mock_service.restore_platform_skill = AsyncMock(return_value=(_full_skill(), None))
            result = await restore_platform_skill(
                skill_id=TEST_SKILL_ID,
                user_data=(TEST_USER_ID, _profile(is_admin=True)),
            )
        assert result.slug == "appointment-booking"
        mock_service.restore_platform_skill.assert_awaited_once_with(TEST_SKILL_ID)


class TestPlatformSkillImportRoute:
    """Authorization + wiring tests for platform skill import-from-URL."""

    @pytest.mark.asyncio
    async def test_import_requires_platform_admin(self):
        from src.voice_agents.platform_skill_routes import import_platform_skill_from_url
        from shared.voice_agents.skill_models import SkillImportRequest

        with pytest.raises(HTTPException) as exc_info:
            await import_platform_skill_from_url(
                request=SkillImportRequest(url="https://github.com/o/r/tree/main/skills/x"),
                user_data=(TEST_USER_ID, _profile(is_admin=False)),
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_import_succeeds_for_platform_admin(self):
        from src.voice_agents.platform_skill_routes import import_platform_skill_from_url
        from shared.voice_agents.skill_models import SkillImportRequest
        from shared.voice_agents.skill_models import (
            PlatformSkillImportResult,
        )

        pkg = type("P", (), {})()
        pkg.slug = "imported-skill"
        pkg.name = "Imported Skill"
        pkg.description = "desc"
        pkg.content = "# Imported"
        pkg.source_url = "https://github.com/o/r"
        pkg.files = []

        with patch("src.voice_agents.platform_skill_routes.skill_service") as mock_service, \
                patch("src.voice_agents.platform_skill_routes.SkillImporter", create=True) as _:
            # SkillImporter is imported lazily inside the route; patch the module it imports from
            import sys
            import src.voice_agents.skill_import as si
            orig = si.SkillImporter
            si.SkillImporter = lambda: type("Imp", (), {"fetch_skill_packages": AsyncMock(return_value=[pkg])})()
            try:
                mock_service.create_platform_skill = AsyncMock(return_value=(_full_skill(), None))
                result = await import_platform_skill_from_url(
                    request=SkillImportRequest(url="https://github.com/o/r"),
                    user_data=(TEST_USER_ID, _profile(is_admin=True)),
                )
            finally:
                si.SkillImporter = orig
        assert len(result) == 1
        assert isinstance(result[0], PlatformSkillImportResult)
        assert result[0].source_url == "https://github.com/o/r"
