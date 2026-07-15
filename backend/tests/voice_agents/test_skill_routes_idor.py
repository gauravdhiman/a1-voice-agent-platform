"""
Tests for skill_routes cross-org IDORs (Task #33 — N1 follow-up #4).

Closes 3 HIGH-severity cross-org IDORs in
`backend/src/voice_agents/skill_routes.py`:

  - PUT   /organizations/{org_id}/skills/{skill_id}/files/{file_id}
  - DELETE /organizations/{org_id}/skills/{skill_id}/files/{file_id}
  - POST  /organizations/{org_id}/skills/{skill_id}/refresh

All three accept ``{org_id}`` in the path, check the caller's role
against that path-org, but NEVER verify that the targeted file/skill
actually belongs to that org. An org_admin on org A could submit a
PUT/DELETE/refresh with a file/skill UUID from org B (guessing the
UUID) and the route would happily execute against org B's data.

Contract (per endpoint):
  - org_admin on the path's org, file/skill belongs to that org → 200.
  - org_admin on a DIFFERENT org, file/skill belongs to that other org
    → 403 (cross-org IDOR guard).
  - regular user (no admin role) → 403 (unchanged).
  - platform_admin → 200 (unchanged, org-agnostic).
  - The underlying service method (update/delete/refresh) is NEVER
    called for a 403 path.
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID

from fastapi import HTTPException

TEST_ORG_ID = UUID("00000000-0000-0000-0000-000000000020")
TEST_OTHER_ORG_ID = UUID("00000000-0000-0000-0000-000000000030")
TEST_SKILL_ID = UUID("00000000-0000-0000-0000-000000000040")
TEST_FILE_ID = UUID("00000000-0000-0000-0000-000000000050")
TEST_USER_ID = UUID("00000000-0000-0000-0000-000000000060")


def _make_user_profile(
    is_platform_admin: bool = False,
    is_org_admin_on: str | None = None,
):
    profile = Mock()
    profile.has_role = Mock(
        side_effect=lambda role, org_id=None: (
            (role == "platform_admin" and is_platform_admin)
            or (role == "org_admin" and org_id == is_org_admin_on)
        )
    )
    return profile


def _make_skill(org_id: UUID = TEST_ORG_ID) -> Mock:
    """Mock OrganizationSkill with .organization_id."""
    skill = Mock()
    skill.id = TEST_SKILL_ID
    skill.organization_id = org_id
    return skill


def _make_skill_file(skill_id: UUID = TEST_SKILL_ID) -> Mock:
    """Mock SkillFile with .skill_id (no org_id — look up skill to get it)."""
    f = Mock()
    f.id = TEST_FILE_ID
    f.skill_id = skill_id
    f.file_path = "README.md"
    f.content = "Hello"
    return f


class TestSkillFileUpdateCrossOrg:
    """PUT /organizations/{org_id}/skills/{skill_id}/files/{file_id}"""

    @pytest.mark.asyncio
    async def test_org_admin_cross_org_file_id_forbidden(self):
        """org_admin on path org, but file_id belongs to a DIFFERENT org → 403."""
        from src.voice_agents.skill_routes import update_skill_file
        from shared.voice_agents.skill_models import SkillFileUpdate

        profile = _make_user_profile(is_org_admin_on=str(TEST_ORG_ID))
        # The file belongs to OTHER org, but path is for OUR org.
        file_in_other_org = _make_skill_file(skill_id=TEST_SKILL_ID)
        skill_in_other_org = _make_skill(org_id=TEST_OTHER_ORG_ID)

        with patch("src.voice_agents.skill_routes.skill_service") as mock_svc:
            # get_skill_file returns the file (no org_id on the file itself).
            mock_svc.get_skill_file = AsyncMock(
                return_value=(file_in_other_org, None)
            )
            # get_skill_by_id returns the parent skill whose org_id we
            # compare against the path org_id.
            mock_svc.get_skill_by_id = AsyncMock(
                return_value=(skill_in_other_org, None)
            )
            mock_svc.update_skill_file = AsyncMock()

            with pytest.raises(HTTPException) as exc_info:
                await update_skill_file(
                    org_id=TEST_ORG_ID,
                    skill_id=TEST_SKILL_ID,
                    file_id=TEST_FILE_ID,
                    file_data=SkillFileUpdate(content="attacker content"),
                    user_data=(TEST_USER_ID, profile),
                )

            assert exc_info.value.status_code == 403
            mock_svc.update_skill_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_org_admin_same_org_file_allowed(self):
        """org_admin on path org, file belongs to that org → 200."""
        from src.voice_agents.skill_routes import update_skill_file
        from shared.voice_agents.skill_models import SkillFileUpdate

        profile = _make_user_profile(is_org_admin_on=str(TEST_ORG_ID))
        file_in_our_org = _make_skill_file(skill_id=TEST_SKILL_ID)
        skill_in_our_org = _make_skill(org_id=TEST_ORG_ID)
        updated_file = _make_skill_file()

        with patch("src.voice_agents.skill_routes.skill_service") as mock_svc:
            mock_svc.get_skill_file = AsyncMock(
                return_value=(file_in_our_org, None)
            )
            mock_svc.get_skill_by_id = AsyncMock(
                return_value=(skill_in_our_org, None)
            )
            mock_svc.update_skill_file = AsyncMock(
                return_value=(updated_file, None)
            )

            result = await update_skill_file(
                org_id=TEST_ORG_ID,
                skill_id=TEST_SKILL_ID,
                file_id=TEST_FILE_ID,
                file_data=SkillFileUpdate(content="legit content"),
                user_data=(TEST_USER_ID, profile),
            )

            assert result is not None
            mock_svc.update_skill_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_platform_admin_allowed(self):
        """platform_admin bypasses the cross-org check (org-agnostic)."""
        from src.voice_agents.skill_routes import update_skill_file
        from shared.voice_agents.skill_models import SkillFileUpdate

        profile = _make_user_profile(is_platform_admin=True)
        file_in_other_org = _make_skill_file()
        skill_in_other_org = _make_skill(org_id=TEST_OTHER_ORG_ID)
        updated = _make_skill_file()

        with patch("src.voice_agents.skill_routes.skill_service") as mock_svc:
            mock_svc.get_skill_file = AsyncMock(
                return_value=(file_in_other_org, None)
            )
            mock_svc.get_skill_by_id = AsyncMock(
                return_value=(skill_in_other_org, None)
            )
            mock_svc.update_skill_file = AsyncMock(
                return_value=(updated, None)
            )

            result = await update_skill_file(
                org_id=TEST_ORG_ID,
                skill_id=TEST_SKILL_ID,
                file_id=TEST_FILE_ID,
                file_data=SkillFileUpdate(content="any"),
                user_data=(TEST_USER_ID, profile),
            )

            assert result is not None


class TestSkillFileDeleteCrossOrg:
    """DELETE /organizations/{org_id}/skills/{skill_id}/files/{file_id}"""

    @pytest.mark.asyncio
    async def test_org_admin_cross_org_file_id_forbidden(self):
        """Same IDOR pattern for DELETE."""
        from src.voice_agents.skill_routes import delete_skill_file

        profile = _make_user_profile(is_org_admin_on=str(TEST_ORG_ID))
        file_in_other_org = _make_skill_file()
        skill_in_other_org = _make_skill(org_id=TEST_OTHER_ORG_ID)

        with patch("src.voice_agents.skill_routes.skill_service") as mock_svc:
            mock_svc.get_skill_file = AsyncMock(
                return_value=(file_in_other_org, None)
            )
            mock_svc.get_skill_by_id = AsyncMock(
                return_value=(skill_in_other_org, None)
            )
            mock_svc.delete_skill_file = AsyncMock()

            with pytest.raises(HTTPException) as exc_info:
                await delete_skill_file(
                    org_id=TEST_ORG_ID,
                    skill_id=TEST_SKILL_ID,
                    file_id=TEST_FILE_ID,
                    user_data=(TEST_USER_ID, profile),
                )

            assert exc_info.value.status_code == 403
            mock_svc.delete_skill_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_org_admin_same_org_file_allowed(self):
        from src.voice_agents.skill_routes import delete_skill_file

        profile = _make_user_profile(is_org_admin_on=str(TEST_ORG_ID))
        file_in_our_org = _make_skill_file()
        skill_in_our_org = _make_skill(org_id=TEST_ORG_ID)

        with patch("src.voice_agents.skill_routes.skill_service") as mock_svc:
            mock_svc.get_skill_file = AsyncMock(
                return_value=(file_in_our_org, None)
            )
            mock_svc.get_skill_by_id = AsyncMock(
                return_value=(skill_in_our_org, None)
            )
            mock_svc.delete_skill_file = AsyncMock(return_value=(True, None))

            result = await delete_skill_file(
                org_id=TEST_ORG_ID,
                skill_id=TEST_SKILL_ID,
                file_id=TEST_FILE_ID,
                user_data=(TEST_USER_ID, profile),
            )

            # DELETE returns None on success (204).
            assert result is None
            mock_svc.delete_skill_file.assert_called_once()


class TestSkillRefreshCrossOrg:
    """POST /organizations/{org_id}/skills/{skill_id}/refresh"""

    @pytest.mark.asyncio
    async def test_org_admin_cross_org_skill_id_forbidden(self):
        """org_admin on path org, but skill_id belongs to a different org → 403."""
        from src.voice_agents.skill_routes import refresh_forked_skill
        from shared.voice_agents.skill_models import SkillRefreshRequest

        profile = _make_user_profile(is_org_admin_on=str(TEST_ORG_ID))
        # Path says org A; skill actually belongs to org B.
        skill_in_other_org = _make_skill(org_id=TEST_OTHER_ORG_ID)

        with patch("src.voice_agents.skill_routes.skill_service") as mock_svc:
            mock_svc.get_skill_by_id = AsyncMock(
                return_value=(skill_in_other_org, None)
            )
            mock_svc.refresh_forked_skill = AsyncMock()

            with pytest.raises(HTTPException) as exc_info:
                await refresh_forked_skill(
                    org_id=TEST_ORG_ID,
                    skill_id=TEST_SKILL_ID,
                    request=SkillRefreshRequest(confirm_overwrite=True),
                    user_data=(TEST_USER_ID, profile),
                )

            assert exc_info.value.status_code == 403
            mock_svc.refresh_forked_skill.assert_not_called()

    @pytest.mark.asyncio
    async def test_org_admin_same_org_skill_allowed(self):
        from src.voice_agents.skill_routes import refresh_forked_skill
        from shared.voice_agents.skill_models import SkillRefreshRequest

        profile = _make_user_profile(is_org_admin_on=str(TEST_ORG_ID))
        skill_in_our_org = _make_skill(org_id=TEST_ORG_ID)
        refreshed = _make_skill(org_id=TEST_ORG_ID)

        with patch("src.voice_agents.skill_routes.skill_service") as mock_svc:
            mock_svc.get_skill_by_id = AsyncMock(
                return_value=(skill_in_our_org, None)
            )
            mock_svc.refresh_forked_skill = AsyncMock(
                return_value=(refreshed, None)
            )

            result = await refresh_forked_skill(
                org_id=TEST_ORG_ID,
                skill_id=TEST_SKILL_ID,
                request=SkillRefreshRequest(confirm_overwrite=True),
                user_data=(TEST_USER_ID, profile),
            )

            assert result is not None
            mock_svc.refresh_forked_skill.assert_called_once()
