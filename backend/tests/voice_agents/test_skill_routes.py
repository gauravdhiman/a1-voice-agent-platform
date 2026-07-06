"""
Tests for skill API routes.

Tests cover: CRUD endpoints, permission checks (admin-only write, read for all),
built-in skill protection, error handling, and 204 responses.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID


class TestSkillRoutes:
    """Test cases for organization skill routes."""

    @pytest.mark.asyncio
    async def test_get_organization_skills_success(self):
        """Test listing organization skills."""
        from src.voice_agents.skill_routes import get_organization_skills
        from shared.voice_agents.skill_models import OrganizationSkill

        test_org_id = UUID("00000000-0000-0000-0000-000000000001")
        test_user_id = UUID("00000000-0000-0000-0000-000000000003")

        mock_skill = OrganizationSkill(
            id=UUID("00000000-0000-0000-0000-000000000010"),
            organization_id=test_org_id,
            slug="test-skill",
            name="Test Skill",
            description="A test skill",
            content="# Test",
            category="custom",
            is_active=True,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )

        mock_user_profile = Mock()
        mock_user_profile.has_role = Mock(return_value=True)

        with patch("src.voice_agents.skill_routes.skill_service") as mock_service:
            mock_service.get_organization_skills = AsyncMock(return_value=([mock_skill], None))

            result = await get_organization_skills(
                org_id=test_org_id,
                user_data=(test_user_id, mock_user_profile),
            )

            assert len(result) == 1
            assert result[0].slug == "test-skill"

    @pytest.mark.asyncio
    async def test_get_organization_skills_regular_user_can_read(self):
        """Test that regular users can read skills."""
        from src.voice_agents.skill_routes import get_organization_skills

        test_org_id = UUID("00000000-0000-0000-0000-000000000001")
        test_user_id = UUID("00000000-0000-0000-0000-000000000003")

        mock_user_profile = Mock()
        # Not platform_admin, not org_admin, but regular_user
        def has_role(role, org_id=None):
            if role == "platform_admin":
                return False
            if role == "org_admin":
                return False
            if role == "regular_user":
                return True
            return False
        mock_user_profile.has_role = has_role

        with patch("src.voice_agents.skill_routes.skill_service") as mock_service:
            mock_service.get_organization_skills = AsyncMock(return_value=([], None))

            result = await get_organization_skills(
                org_id=test_org_id,
                user_data=(test_user_id, mock_user_profile),
            )

            assert result == []

    @pytest.mark.asyncio
    async def test_create_skill_requires_admin(self):
        """Test that only admins can create skills."""
        from src.voice_agents.skill_routes import create_skill
        from shared.voice_agents.skill_models import OrganizationSkillCreate
        from fastapi import HTTPException

        test_org_id = UUID("00000000-0000-0000-0000-000000000001")
        test_user_id = UUID("00000000-0000-0000-0000-000000000003")

        skill_data = OrganizationSkillCreate(
            organization_id=test_org_id,
            name="Test",
            slug="test",
            content="# Test",
        )

        mock_user_profile = Mock()
        mock_user_profile.has_role = Mock(return_value=False)

        with pytest.raises(HTTPException) as exc_info:
            await create_skill(
                org_id=test_org_id,
                skill_data=skill_data,
                user_data=(test_user_id, mock_user_profile),
            )

        assert exc_info.value.status_code == 403
"""
Tests for skill API routes.

Tests cover: CRUD endpoints, permission checks (admin-only write, read for all),
fork/refresh endpoints, import, file management, error handling, and 204 responses.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID


class TestSkillRoutes:
    """Test cases for organization skill routes."""

    @pytest.mark.asyncio
    async def test_get_organization_skills_success(self):
        """Test listing organization skills."""
        from src.voice_agents.skill_routes import get_organization_skills
        from shared.voice_agents.skill_models import OrganizationSkill

        test_org_id = UUID("00000000-0000-0000-0000-000000000001")
        test_user_id = UUID("00000000-0000-0000-0000-000000000003")

        mock_skill = OrganizationSkill(
            id=UUID("00000000-0000-0000-0000-000000000010"),
            organization_id=test_org_id,
            slug="test-skill",
            name="Test Skill",
            description="A test skill",
            content="# Test",
            category="custom",
            is_active=True,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )

        mock_user_profile = Mock()
        mock_user_profile.has_role = Mock(return_value=True)

        with patch("src.voice_agents.skill_routes.skill_service") as mock_service:
            mock_service.get_organization_skills = AsyncMock(return_value=([mock_skill], None))

            result = await get_organization_skills(
                org_id=test_org_id,
                user_data=(test_user_id, mock_user_profile),
            )

            assert len(result) == 1
            assert result[0].slug == "test-skill"

    @pytest.mark.asyncio
    async def test_get_organization_skills_regular_user_can_read(self):
        """Test that regular users can read skills."""
        from src.voice_agents.skill_routes import get_organization_skills

        test_org_id = UUID("00000000-0000-0000-0000-000000000001")
        test_user_id = UUID("00000000-0000-0000-0000-000000000003")

        mock_user_profile = Mock()
        # Not platform_admin, not org_admin, but regular_user
        def has_role(role, org_id=None):
            if role == "platform_admin":
                return False
            if role == "org_admin":
                return False
            if role == "regular_user":
                return True
            return False
        mock_user_profile.has_role = has_role

        with patch("src.voice_agents.skill_routes.skill_service") as mock_service:
            mock_service.get_organization_skills = AsyncMock(return_value=([], None))

            result = await get_organization_skills(
                org_id=test_org_id,
                user_data=(test_user_id, mock_user_profile),
            )

            assert result == []

    @pytest.mark.asyncio
    async def test_create_skill_requires_admin(self):
        """Test that only admins can create skills."""
        from src.voice_agents.skill_routes import create_skill
        from shared.voice_agents.skill_models import OrganizationSkillCreate
        from fastapi import HTTPException

        test_org_id = UUID("00000000-0000-0000-0000-000000000001")
        test_user_id = UUID("00000000-0000-0000-0000-000000000003")

        skill_data = OrganizationSkillCreate(
            organization_id=test_org_id,
            name="Test",
            slug="test",
            content="# Test",
        )

        mock_user_profile = Mock()
        mock_user_profile.has_role = Mock(return_value=False)

        with pytest.raises(HTTPException) as exc_info:
            await create_skill(
                org_id=test_org_id,
                skill_data=skill_data,
                user_data=(test_user_id, mock_user_profile),
            )

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_update_skill_success(self):
        """Test that any org skill can be updated (no built_in restriction)."""
        from src.voice_agents.skill_routes import update_skill
        from shared.voice_agents.skill_models import OrganizationSkill, OrganizationSkillUpdate

        test_org_id = UUID("00000000-0000-0000-0000-000000000001")
        test_skill_id = UUID("00000000-0000-0000-0000-000000000010")
        test_user_id = UUID("00000000-0000-0000-0000-000000000003")

        existing_skill = OrganizationSkill(
            id=test_skill_id,
            organization_id=test_org_id,
            slug="appointment-booking",
            name="Appointment Booking",
            content="# Original",
            category="custom",
            is_active=True,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )

        updated_skill = existing_skill.model_copy(update={"content": "# Modified", "name": "New Name"})
        update_data = OrganizationSkillUpdate(content="# Modified", name="New Name")

        mock_user_profile = Mock()
        mock_user_profile.has_role = Mock(return_value=True)

        with patch("src.voice_agents.skill_routes.skill_service") as mock_service:
            mock_service.get_skill_by_id = AsyncMock(return_value=(existing_skill, None))
            mock_service.update_skill = AsyncMock(return_value=(updated_skill, None))

            result = await update_skill(
                org_id=test_org_id,
                skill_id=test_skill_id,
                skill_data=update_data,
                user_data=(test_user_id, mock_user_profile),
            )

            assert result.content == "# Modified"
            assert result.name == "New Name"

    @pytest.mark.asyncio
    async def test_delete_skill_success(self):
        """Test that any org skill can be deleted (no built_in restriction)."""
        from src.voice_agents.skill_routes import delete_skill
        from shared.voice_agents.skill_models import OrganizationSkill

        test_org_id = UUID("00000000-0000-0000-0000-000000000001")
        test_skill_id = UUID("00000000-0000-0000-0000-000000000010")
        test_user_id = UUID("00000000-0000-0000-0000-000000000003")

        existing_skill = OrganizationSkill(
            id=test_skill_id,
            organization_id=test_org_id,
            slug="appointment-booking",
            name="Appointment Booking",
            content="# Original",
            category="custom",
            is_active=True,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )

        mock_user_profile = Mock()
        mock_user_profile.has_role = Mock(return_value=True)

        with patch("src.voice_agents.skill_routes.skill_service") as mock_service:
            mock_service.get_skill_by_id = AsyncMock(return_value=(existing_skill, None))
            mock_service.delete_skill = AsyncMock(return_value=(True, None))

            result = await delete_skill(
                org_id=test_org_id,
                skill_id=test_skill_id,
                user_data=(test_user_id, mock_user_profile),
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_assign_skill_requires_admin(self):
        """Test that only admins can assign skills to agents."""
        from src.voice_agents.skill_routes import assign_skill_to_agent
        from shared.voice_agents.skill_models import AgentSkillAssignment
        from shared.voice_agents.models import VoiceAgent
        from fastapi import HTTPException

        test_agent_id = UUID("00000000-0000-0000-0000-000000000002")
        test_user_id = UUID("00000000-0000-0000-0000-000000000003")
        test_org_id = UUID("00000000-0000-0000-0000-000000000001")
        test_skill_id = UUID("00000000-0000-0000-0000-000000000010")

        agent = VoiceAgent(
            id=test_agent_id,
            organization_id=test_org_id,
            name="Test Agent",
            is_active=True,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )

        assignment = AgentSkillAssignment(skill_id=test_skill_id)

        mock_user_profile = Mock()
        mock_user_profile.has_role = Mock(return_value=False)

        with patch("src.voice_agents.skill_routes.voice_agent_service") as mock_agent_svc:
            mock_agent_svc.get_agent_by_id = AsyncMock(return_value=(agent, None))

            with pytest.raises(HTTPException) as exc_info:
                await assign_skill_to_agent(
                    agent_id=test_agent_id,
                    assignment=assignment,
                    user_data=(test_user_id, mock_user_profile),
                )

            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_get_skill_content_by_slug(self):
        """Test content retrieval for the load_skill tool."""
        from src.voice_agents.skill_routes import get_skill_content

        test_org_id = UUID("00000000-0000-0000-0000-000000000001")

        with patch("src.voice_agents.skill_routes.skill_service") as mock_service:
            mock_service.get_skill_content_by_slug = AsyncMock(
                return_value=("# Appointment Booking\n\n## Procedure\n...", None)
            )

            result = await get_skill_content(org_id=test_org_id, slug="appointment-booking")

            assert "Appointment Booking" in result
            assert "Procedure" in result

    @pytest.mark.asyncio
    async def test_get_skill_content_not_found(self):
        """Test content retrieval for non-existent skill."""
        from src.voice_agents.skill_routes import get_skill_content
        from fastapi import HTTPException

        test_org_id = UUID("00000000-0000-0000-0000-000000000001")

        with patch("src.voice_agents.skill_routes.skill_service") as mock_service:
            mock_service.get_skill_content_by_slug = AsyncMock(
                return_value=(None, "Skill 'nonexistent' not found or inactive")
            )

            with pytest.raises(HTTPException) as exc_info:
                await get_skill_content(org_id=test_org_id, slug="nonexistent")

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_seed_platform_skills_requires_platform_admin(self):
        """Test that only platform admins can seed platform skills."""
        from src.voice_agents.skill_routes import seed_platform_skills
        from fastapi import HTTPException

        test_user_id = UUID("00000000-0000-0000-0000-000000000003")

        mock_user_profile = Mock()
        mock_user_profile.has_role = Mock(return_value=False)

        with pytest.raises(HTTPException) as exc_info:
            await seed_platform_skills(
                user_data=(test_user_id, mock_user_profile),
            )

        assert exc_info.value.status_code == 403
        assert "platform admin" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_sync_platform_skills_requires_platform_admin(self):
        """Test that only platform admins can sync platform skills."""
        from src.voice_agents.skill_routes import sync_platform_skills
        from fastapi import HTTPException

        test_user_id = UUID("00000000-0000-0000-0000-000000000003")

        mock_user_profile = Mock()
        mock_user_profile.has_role = Mock(return_value=False)

        with pytest.raises(HTTPException) as exc_info:
            await sync_platform_skills(
                user_data=(test_user_id, mock_user_profile),
            )

        assert exc_info.value.status_code == 403
        assert "platform admin" in exc_info.value.detail.lower()

    # ───── Fork / Refresh ─────

    @pytest.mark.asyncio
    async def test_fork_skill_success(self):
        """Test forking a platform skill into org library."""
        from src.voice_agents.skill_routes import fork_platform_skill
        from shared.voice_agents.skill_models import OrganizationSkill, SkillForkRequest

        test_org_id = UUID("00000000-0000-0000-0000-000000000001")
        test_user_id = UUID("00000000-0000-0000-0000-000000000003")
        test_platform_skill_id = UUID("00000000-0000-0000-0000-000000000100")

        forked_skill = OrganizationSkill(
            id=UUID("00000000-0000-0000-0000-000000000020"),
            organization_id=test_org_id,
            slug="appointment-booking",
            name="Appointment Booking",
            description="Forked from platform",
            content="# Content",
            category="custom",
            is_visible=True,
            source_skill_id=test_platform_skill_id,
            source_version="2026.01.01_1",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )

        request = SkillForkRequest(platform_skill_id=test_platform_skill_id)

        mock_user_profile = Mock()
        mock_user_profile.has_role = Mock(return_value=True)

        with patch("src.voice_agents.skill_routes.skill_service") as mock_service:
            mock_service.fork_platform_skill = AsyncMock(return_value=(forked_skill, None))

            result = await fork_platform_skill(
                org_id=test_org_id,
                request=request,
                user_data=(test_user_id, mock_user_profile),
            )

            assert result.source_skill_id == test_platform_skill_id
            assert result.source_version == "2026.01.01_1"

    @pytest.mark.asyncio
    async def test_fork_skill_requires_admin(self):
        """Test that only admins can fork skills."""
        from src.voice_agents.skill_routes import fork_platform_skill
        from shared.voice_agents.skill_models import SkillForkRequest
        from fastapi import HTTPException

        test_org_id = UUID("00000000-0000-0000-0000-000000000001")
        test_user_id = UUID("00000000-0000-0000-0000-000000000003")
        test_platform_skill_id = UUID("00000000-0000-0000-0000-000000000100")

        request = SkillForkRequest(platform_skill_id=test_platform_skill_id)

        mock_user_profile = Mock()
        mock_user_profile.has_role = Mock(return_value=False)

        with pytest.raises(HTTPException) as exc_info:
            await fork_platform_skill(
                org_id=test_org_id,
                request=request,
                user_data=(test_user_id, mock_user_profile),
            )

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_check_update_success(self):
        """Test checking for skill updates."""
        from src.voice_agents.skill_routes import check_skill_update

        test_org_id = UUID("00000000-0000-0000-0000-000000000001")
        test_user_id = UUID("00000000-0000-0000-0000-000000000003")
        test_skill_id = UUID("00000000-0000-0000-0000-000000000010")

        mock_user_profile = Mock()
        mock_user_profile.has_role = Mock(return_value=True)

        with patch("src.voice_agents.skill_routes.skill_service") as mock_service:
            mock_service.check_update_available = AsyncMock(
                return_value=(True, "2026.05.01_2", None)
            )

            result = await check_skill_update(
                org_id=test_org_id,
                skill_id=test_skill_id,
                user_data=(test_user_id, mock_user_profile),
            )

            assert result["update_available"] is True
            assert result["latest_version"] == "2026.05.01_2"

    @pytest.mark.asyncio
    async def test_refresh_skill_requires_confirmation(self):
        """Test that refresh requires confirm_overwrite=true."""
        from src.voice_agents.skill_routes import refresh_forked_skill
        from shared.voice_agents.skill_models import SkillRefreshRequest
        from fastapi import HTTPException

        test_org_id = UUID("00000000-0000-0000-0000-000000000001")
        test_user_id = UUID("00000000-0000-0000-0000-000000000003")
        test_skill_id = UUID("00000000-0000-0000-0000-000000000010")

        request = SkillRefreshRequest(confirm_overwrite=False)

        mock_user_profile = Mock()
        mock_user_profile.has_role = Mock(return_value=True)

        with pytest.raises(HTTPException) as exc_info:
            await refresh_forked_skill(
                org_id=test_org_id,
                skill_id=test_skill_id,
                request=request,
                user_data=(test_user_id, mock_user_profile),
            )

        assert exc_info.value.status_code == 400
        assert "confirm_overwrite" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_refresh_skill_success(self):
        """Test successful refresh of forked skill."""
        from src.voice_agents.skill_routes import refresh_forked_skill
        from shared.voice_agents.skill_models import OrganizationSkill, SkillRefreshRequest

        test_org_id = UUID("00000000-0000-0000-0000-000000000001")
        test_user_id = UUID("00000000-0000-0000-0000-000000000003")
        test_skill_id = UUID("00000000-0000-0000-0000-000000000010")

        refreshed = OrganizationSkill(
            id=test_skill_id,
            organization_id=test_org_id,
            slug="appointment-booking",
            name="Appointment Booking",
            content="# Refreshed Content",
            category="custom",
            is_visible=True,
            source_version="2026.05.01_2",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-02T00:00:00",
        )

        request = SkillRefreshRequest(confirm_overwrite=True)

        mock_user_profile = Mock()
        mock_user_profile.has_role = Mock(return_value=True)

        with patch("src.voice_agents.skill_routes.skill_service") as mock_service:
            mock_service.refresh_forked_skill = AsyncMock(return_value=(refreshed, None))

            result = await refresh_forked_skill(
                org_id=test_org_id,
                skill_id=test_skill_id,
                request=request,
                user_data=(test_user_id, mock_user_profile),
            )

            assert result.content == "# Refreshed Content"
            assert result.source_version == "2026.05.01_2"


class TestSkillFileRoutes:
    """Test cases for skill reference file endpoints."""

    @pytest.mark.asyncio
    async def test_get_skill_files_success(self):
        """Test listing skill files."""
        from src.voice_agents.skill_routes import get_skill_files
        from shared.voice_agents.skill_models import SkillFileSummary

        test_org_id = UUID("00000000-0000-0000-0000-000000000001")
        test_skill_id = UUID("00000000-0000-0000-0000-000000000010")
        test_user_id = UUID("00000000-0000-0000-0000-000000000003")

        mock_file = SkillFileSummary(
            id=UUID("00000000-0000-0000-0000-000000000020"),
            file_path="references/policies.md",
            file_kind="reference",
            content_hash="abc123",
        )

        mock_user_profile = Mock()
        mock_user_profile.has_role = Mock(return_value=True)

        with patch("src.voice_agents.skill_routes.skill_service") as mock_service:
            mock_service.get_skill_files = AsyncMock(return_value=([mock_file], None))

            result = await get_skill_files(
                org_id=test_org_id,
                skill_id=test_skill_id,
                user_data=(test_user_id, mock_user_profile),
            )

            assert len(result) == 1
            assert result[0].file_path == "references/policies.md"

    @pytest.mark.asyncio
    async def test_create_skill_file_requires_admin(self):
        """Test that only admins can create skill files."""
        from src.voice_agents.skill_routes import create_skill_file
        from shared.voice_agents.skill_models import SkillFileCreate
        from fastapi import HTTPException

        test_org_id = UUID("00000000-0000-0000-0000-000000000001")
        test_skill_id = UUID("00000000-0000-0000-0000-000000000010")
        test_user_id = UUID("00000000-0000-0000-0000-000000000003")

        file_data = SkillFileCreate(
            file_path="references/test.md", content="# Test"
        )

        mock_user_profile = Mock()
        mock_user_profile.has_role = Mock(return_value=False)

        with pytest.raises(HTTPException) as exc_info:
            await create_skill_file(
                org_id=test_org_id,
                skill_id=test_skill_id,
                file_data=file_data,
                user_data=(test_user_id, mock_user_profile),
            )

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_update_skill_file_requires_admin(self):
        """Test that only admins can update skill files."""
        from src.voice_agents.skill_routes import update_skill_file
        from shared.voice_agents.skill_models import SkillFileUpdate
        from fastapi import HTTPException

        test_org_id = UUID("00000000-0000-0000-0000-000000000001")
        test_skill_id = UUID("00000000-0000-0000-0000-000000000010")
        test_file_id = UUID("00000000-0000-0000-0000-000000000020")
        test_user_id = UUID("00000000-0000-0000-0000-000000000003")

        file_data = SkillFileUpdate(content="# Updated")

        mock_user_profile = Mock()
        mock_user_profile.has_role = Mock(return_value=False)

        with pytest.raises(HTTPException) as exc_info:
            await update_skill_file(
                org_id=test_org_id,
                skill_id=test_skill_id,
                file_id=test_file_id,
                file_data=file_data,
                user_data=(test_user_id, mock_user_profile),
            )

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_skill_file_requires_admin(self):
        """Test that only admins can delete skill files."""
        from src.voice_agents.skill_routes import delete_skill_file
        from fastapi import HTTPException

        test_org_id = UUID("00000000-0000-0000-0000-000000000001")
        test_skill_id = UUID("00000000-0000-0000-0000-000000000010")
        test_file_id = UUID("00000000-0000-0000-0000-000000000020")
        test_user_id = UUID("00000000-0000-0000-0000-000000000003")

        mock_user_profile = Mock()
        mock_user_profile.has_role = Mock(return_value=False)

        with pytest.raises(HTTPException) as exc_info:
            await delete_skill_file(
                org_id=test_org_id,
                skill_id=test_skill_id,
                file_id=test_file_id,
                user_data=(test_user_id, mock_user_profile),
            )

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_skill_file_returns_204(self):
        """Test successful file deletion returns 204."""
        from src.voice_agents.skill_routes import delete_skill_file

        test_org_id = UUID("00000000-0000-0000-0000-000000000001")
        test_skill_id = UUID("00000000-0000-0000-0000-000000000010")
        test_file_id = UUID("00000000-0000-0000-0000-000000000020")
        test_user_id = UUID("00000000-0000-0000-0000-000000000003")

        mock_user_profile = Mock()
        mock_user_profile.has_role = Mock(return_value=True)

        with patch("src.voice_agents.skill_routes.skill_service") as mock_service:
            # Cross-org IDOR guard: the route now calls get_skill_file
            # to resolve the parent skill's organization_id.
            mock_service.get_skill_file = AsyncMock(
                return_value=(Mock(skill_id=test_skill_id), None)
            )
            mock_service.delete_skill_file = AsyncMock(return_value=(True, None))

            result = await delete_skill_file(
                org_id=test_org_id,
                skill_id=test_skill_id,
                file_id=test_file_id,
                user_data=(test_user_id, mock_user_profile),
            )

            assert result is None  # 204 returns None

    @pytest.mark.asyncio
    async def test_get_skill_file_content_by_slug(self):
        """Test file content retrieval for the load_skill_reference tool."""
        from src.voice_agents.skill_routes import get_skill_file_content

        test_org_id = UUID("00000000-0000-0000-0000-000000000001")

        with patch("src.voice_agents.skill_routes.skill_service") as mock_service:
            mock_service.get_skill_file_content_by_slug = AsyncMock(
                return_value=("# Booking Policies\n\n- Rule 1\n- Rule 2", None)
            )

            result = await get_skill_file_content(
                org_id=test_org_id,
                slug="appointment-booking",
                file_path="references/policies.md",
            )

            assert "Booking Policies" in result
            assert "Rule 1" in result

    @pytest.mark.asyncio
    async def test_get_skill_file_content_not_found(self):
        """Test file content retrieval for non-existent file."""
        from src.voice_agents.skill_routes import get_skill_file_content
        from fastapi import HTTPException

        test_org_id = UUID("00000000-0000-0000-0000-000000000001")

        with patch("src.voice_agents.skill_routes.skill_service") as mock_service:
            mock_service.get_skill_file_content_by_slug = AsyncMock(
                return_value=(None, "File 'missing.md' not found")
            )

            with pytest.raises(HTTPException) as exc_info:
                await get_skill_file_content(
                    org_id=test_org_id,
                    slug="test",
                    file_path="missing.md",
                )

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_agents_using_skill(self):
        """Test listing agents that use a skill."""
        from src.voice_agents.skill_routes import get_agents_using_skill

        test_org_id = UUID("00000000-0000-0000-0000-000000000001")
        test_skill_id = UUID("00000000-0000-0000-0000-000000000010")
        test_user_id = UUID("00000000-0000-0000-0000-000000000003")

        mock_agents = [
            {"id": "agent-1", "name": "Support Agent", "is_active": True},
            {"id": "agent-2", "name": "Sales Agent", "is_active": False},
        ]

        mock_user_profile = Mock()
        mock_user_profile.has_role = Mock(return_value=True)

        with patch("src.voice_agents.skill_routes.skill_service") as mock_service:
            mock_service.get_agents_using_skill = AsyncMock(
                return_value=(mock_agents, None)
            )

            result = await get_agents_using_skill(
                org_id=test_org_id,
                skill_id=test_skill_id,
                user_data=(test_user_id, mock_user_profile),
            )

            assert len(result) == 2
            assert result[0]["name"] == "Support Agent"


class TestSkillImportRoutes:
    """Test cases for skill import endpoint."""

    @pytest.mark.asyncio
    async def test_import_skill_requires_admin(self):
        """Test that only admins can import skills."""
        from src.voice_agents.skill_routes import import_skill_from_url
        from shared.voice_agents.skill_models import SkillImportRequest
        from fastapi import HTTPException

        test_org_id = UUID("00000000-0000-0000-0000-000000000001")
        test_user_id = UUID("00000000-0000-0000-0000-000000000003")

        request = SkillImportRequest(url="https://github.com/owner/repo")

        mock_user_profile = Mock()
        mock_user_profile.has_role = Mock(return_value=False)

        with pytest.raises(HTTPException) as exc_info:
            await import_skill_from_url(
                org_id=test_org_id,
                request=request,
                user_data=(test_user_id, mock_user_profile),
            )

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_import_skill_invalid_url(self):
        """Test import with invalid URL format."""
        from src.voice_agents.skill_routes import import_skill_from_url
        from shared.voice_agents.skill_models import SkillImportRequest
        from fastapi import HTTPException

        test_org_id = UUID("00000000-0000-0000-0000-000000000001")
        test_user_id = UUID("00000000-0000-0000-0000-000000000003")

        request = SkillImportRequest(url="not-a-valid-url")

        mock_user_profile = Mock()
        mock_user_profile.has_role = Mock(return_value=True)

        from unittest.mock import MagicMock

        with patch("src.voice_agents.skill_import.SkillImporter") as mock_importer_class:
            mock_importer = MagicMock()
            mock_importer.fetch_skill_packages = AsyncMock(
                side_effect=ValueError("Unsupported URL format")
            )
            mock_importer_class.return_value = mock_importer

            with pytest.raises(HTTPException) as exc_info:
                await import_skill_from_url(
                    org_id=test_org_id,
                    request=request,
                    user_data=(test_user_id, mock_user_profile),
                )

            assert exc_info.value.status_code == 400
    async def test_assign_skill_requires_admin(self):
        """Test that only admins can assign skills to agents."""
        from src.voice_agents.skill_routes import assign_skill_to_agent
        from shared.voice_agents.skill_models import AgentSkillAssignment
        from shared.voice_agents.models import VoiceAgent
        from fastapi import HTTPException

        test_agent_id = UUID("00000000-0000-0000-0000-000000000002")
        test_user_id = UUID("00000000-0000-0000-0000-000000000003")
        test_org_id = UUID("00000000-0000-0000-0000-000000000001")
        test_skill_id = UUID("00000000-0000-0000-0000-000000000010")

        agent = VoiceAgent(
            id=test_agent_id,
            organization_id=test_org_id,
            name="Test Agent",
            is_active=True,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )

        assignment = AgentSkillAssignment(skill_id=test_skill_id)

        mock_user_profile = Mock()
        mock_user_profile.has_role = Mock(return_value=False)

        with patch("src.voice_agents.skill_routes.voice_agent_service") as mock_agent_svc:
            mock_agent_svc.get_agent_by_id = AsyncMock(return_value=(agent, None))

            with pytest.raises(HTTPException) as exc_info:
                await assign_skill_to_agent(
                    agent_id=test_agent_id,
                    assignment=assignment,
                    user_data=(test_user_id, mock_user_profile),
                )

            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_get_skill_content_by_slug(self):
        """Test content retrieval for the load_skill tool."""
        from src.voice_agents.skill_routes import get_skill_content

        test_org_id = UUID("00000000-0000-0000-0000-000000000001")

        with patch("src.voice_agents.skill_routes.skill_service") as mock_service:
            mock_service.get_skill_content_by_slug = AsyncMock(
                return_value=("# Appointment Booking\n\n## Procedure\n...", None)
            )

            result = await get_skill_content(org_id=test_org_id, slug="appointment-booking")

            assert "Appointment Booking" in result
            assert "Procedure" in result

    @pytest.mark.asyncio
    async def test_get_skill_content_not_found(self):
        """Test content retrieval for non-existent skill."""
        from src.voice_agents.skill_routes import get_skill_content
        from fastapi import HTTPException

        test_org_id = UUID("00000000-0000-0000-0000-000000000001")

        with patch("src.voice_agents.skill_routes.skill_service") as mock_service:
            mock_service.get_skill_content_by_slug = AsyncMock(
                return_value=(None, "Skill 'nonexistent' not found or inactive")
            )

            with pytest.raises(HTTPException) as exc_info:
                await get_skill_content(org_id=test_org_id, slug="nonexistent")

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_sync_platform_requires_platform_admin(self):
        """Test that only platform admins can sync platform skills."""
        from src.voice_agents.skill_routes import sync_platform_skills
        from fastapi import HTTPException

        test_user_id = UUID("00000000-0000-0000-0000-000000000003")

        mock_user_profile = Mock()
        mock_user_profile.has_role = Mock(return_value=False)

        with pytest.raises(HTTPException) as exc_info:
            await sync_platform_skills(
                user_data=(test_user_id, mock_user_profile),
            )

        assert exc_info.value.status_code == 403
        assert "platform admin" in exc_info.value.detail.lower()


class TestSkillFileRoutes:
    """Test cases for skill reference file endpoints."""

    @pytest.mark.asyncio
    async def test_get_skill_files_success(self):
        """Test listing skill files."""
        from src.voice_agents.skill_routes import get_skill_files
        from shared.voice_agents.skill_models import SkillFileSummary

        test_org_id = UUID("00000000-0000-0000-0000-000000000001")
        test_skill_id = UUID("00000000-0000-0000-0000-000000000010")
        test_user_id = UUID("00000000-0000-0000-0000-000000000003")

        mock_file = SkillFileSummary(
            id=UUID("00000000-0000-0000-0000-000000000020"),
            file_path="references/policies.md",
            file_kind="reference",
            content_hash="abc123",
        )

        mock_user_profile = Mock()
        mock_user_profile.has_role = Mock(return_value=True)

        with patch("src.voice_agents.skill_routes.skill_service") as mock_service:
            mock_service.get_skill_files = AsyncMock(return_value=([mock_file], None))

            result = await get_skill_files(
                org_id=test_org_id,
                skill_id=test_skill_id,
                user_data=(test_user_id, mock_user_profile),
            )

            assert len(result) == 1
            assert result[0].file_path == "references/policies.md"

    @pytest.mark.asyncio
    async def test_create_skill_file_requires_admin(self):
        """Test that only admins can create skill files."""
        from src.voice_agents.skill_routes import create_skill_file
        from shared.voice_agents.skill_models import SkillFileCreate
        from fastapi import HTTPException

        test_org_id = UUID("00000000-0000-0000-0000-000000000001")
        test_skill_id = UUID("00000000-0000-0000-0000-000000000010")
        test_user_id = UUID("00000000-0000-0000-0000-000000000003")

        file_data = SkillFileCreate(
            file_path="references/test.md", content="# Test"
        )

        mock_user_profile = Mock()
        mock_user_profile.has_role = Mock(return_value=False)

        with pytest.raises(HTTPException) as exc_info:
            await create_skill_file(
                org_id=test_org_id,
                skill_id=test_skill_id,
                file_data=file_data,
                user_data=(test_user_id, mock_user_profile),
            )

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_update_skill_file_requires_admin(self):
        """Test that only admins can update skill files."""
        from src.voice_agents.skill_routes import update_skill_file
        from shared.voice_agents.skill_models import SkillFileUpdate
        from fastapi import HTTPException

        test_org_id = UUID("00000000-0000-0000-0000-000000000001")
        test_skill_id = UUID("00000000-0000-0000-0000-000000000010")
        test_file_id = UUID("00000000-0000-0000-0000-000000000020")
        test_user_id = UUID("00000000-0000-0000-0000-000000000003")

        file_data = SkillFileUpdate(content="# Updated")

        mock_user_profile = Mock()
        mock_user_profile.has_role = Mock(return_value=False)

        with pytest.raises(HTTPException) as exc_info:
            await update_skill_file(
                org_id=test_org_id,
                skill_id=test_skill_id,
                file_id=test_file_id,
                file_data=file_data,
                user_data=(test_user_id, mock_user_profile),
            )

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_skill_file_requires_admin(self):
        """Test that only admins can delete skill files."""
        from src.voice_agents.skill_routes import delete_skill_file
        from fastapi import HTTPException

        test_org_id = UUID("00000000-0000-0000-0000-000000000001")
        test_skill_id = UUID("00000000-0000-0000-0000-000000000010")
        test_file_id = UUID("00000000-0000-0000-0000-000000000020")
        test_user_id = UUID("00000000-0000-0000-0000-000000000003")

        mock_user_profile = Mock()
        mock_user_profile.has_role = Mock(return_value=False)

        with pytest.raises(HTTPException) as exc_info:
            await delete_skill_file(
                org_id=test_org_id,
                skill_id=test_skill_id,
                file_id=test_file_id,
                user_data=(test_user_id, mock_user_profile),
            )

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_skill_file_returns_204(self):
        """Test successful file deletion returns 204."""
        from src.voice_agents.skill_routes import delete_skill_file

        test_org_id = UUID("00000000-0000-0000-0000-000000000001")
        test_skill_id = UUID("00000000-0000-0000-0000-000000000010")
        test_file_id = UUID("00000000-0000-0000-0000-000000000020")
        test_user_id = UUID("00000000-0000-0000-0000-000000000003")

        mock_user_profile = Mock()
        mock_user_profile.has_role = Mock(return_value=True)

        with patch("src.voice_agents.skill_routes.skill_service") as mock_service:
            # Cross-org IDOR guard: the route now calls get_skill_file
            # to resolve the parent skill's organization_id.
            mock_service.get_skill_file = AsyncMock(
                return_value=(Mock(skill_id=test_skill_id), None)
            )
            mock_service.delete_skill_file = AsyncMock(return_value=(True, None))

            result = await delete_skill_file(
                org_id=test_org_id,
                skill_id=test_skill_id,
                file_id=test_file_id,
                user_data=(test_user_id, mock_user_profile),
            )

            assert result is None  # 204 returns None

    @pytest.mark.asyncio
    async def test_get_skill_file_content_by_slug(self):
        """Test file content retrieval for the load_skill_reference tool."""
        from src.voice_agents.skill_routes import get_skill_file_content

        test_org_id = UUID("00000000-0000-0000-0000-000000000001")

        with patch("src.voice_agents.skill_routes.skill_service") as mock_service:
            mock_service.get_skill_file_content_by_slug = AsyncMock(
                return_value=("# Booking Policies\n\n- Rule 1\n- Rule 2", None)
            )

            result = await get_skill_file_content(
                org_id=test_org_id,
                slug="appointment-booking",
                file_path="references/policies.md",
            )

            assert "Booking Policies" in result
            assert "Rule 1" in result

    @pytest.mark.asyncio
    async def test_get_skill_file_content_not_found(self):
        """Test file content retrieval for non-existent file."""
        from src.voice_agents.skill_routes import get_skill_file_content
        from fastapi import HTTPException

        test_org_id = UUID("00000000-0000-0000-0000-000000000001")

        with patch("src.voice_agents.skill_routes.skill_service") as mock_service:
            mock_service.get_skill_file_content_by_slug = AsyncMock(
                return_value=(None, "File 'missing.md' not found")
            )

            with pytest.raises(HTTPException) as exc_info:
                await get_skill_file_content(
                    org_id=test_org_id,
                    slug="test",
                    file_path="missing.md",
                )

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_agents_using_skill(self):
        """Test listing agents that use a skill."""
        from src.voice_agents.skill_routes import get_agents_using_skill

        test_org_id = UUID("00000000-0000-0000-0000-000000000001")
        test_skill_id = UUID("00000000-0000-0000-0000-000000000010")
        test_user_id = UUID("00000000-0000-0000-0000-000000000003")

        mock_agents = [
            {"id": "agent-1", "name": "Support Agent", "is_active": True},
            {"id": "agent-2", "name": "Sales Agent", "is_active": False},
        ]

        mock_user_profile = Mock()
        mock_user_profile.has_role = Mock(return_value=True)

        with patch("src.voice_agents.skill_routes.skill_service") as mock_service:
            mock_service.get_agents_using_skill = AsyncMock(
                return_value=(mock_agents, None)
            )

            result = await get_agents_using_skill(
                org_id=test_org_id,
                skill_id=test_skill_id,
                user_data=(test_user_id, mock_user_profile),
            )

            assert len(result) == 2
            assert result[0]["name"] == "Support Agent"


class TestSkillImportRoutes:
    """Test cases for skill import endpoint."""

    @pytest.mark.asyncio
    async def test_import_skill_requires_admin(self):
        """Test that only admins can import skills."""
        from src.voice_agents.skill_routes import import_skill_from_url
        from shared.voice_agents.skill_models import SkillImportRequest
        from fastapi import HTTPException

        test_org_id = UUID("00000000-0000-0000-0000-000000000001")
        test_user_id = UUID("00000000-0000-0000-0000-000000000003")

        request = SkillImportRequest(url="https://github.com/owner/repo")

        mock_user_profile = Mock()
        mock_user_profile.has_role = Mock(return_value=False)

        with pytest.raises(HTTPException) as exc_info:
            await import_skill_from_url(
                org_id=test_org_id,
                request=request,
                user_data=(test_user_id, mock_user_profile),
            )

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_import_skill_invalid_url(self):
        """Test import with invalid URL format."""
        from src.voice_agents.skill_routes import import_skill_from_url
        from shared.voice_agents.skill_models import SkillImportRequest
        from fastapi import HTTPException

        test_org_id = UUID("00000000-0000-0000-0000-000000000001")
        test_user_id = UUID("00000000-0000-0000-0000-000000000003")

        request = SkillImportRequest(url="not-a-valid-url")

        mock_user_profile = Mock()
        mock_user_profile.has_role = Mock(return_value=True)

        from unittest.mock import MagicMock

        with patch("src.voice_agents.skill_import.SkillImporter") as mock_importer_class:
            mock_importer = MagicMock()
            mock_importer.fetch_skill_packages = AsyncMock(
                side_effect=ValueError("Unsupported URL format")
            )
            mock_importer_class.return_value = mock_importer

            with pytest.raises(HTTPException) as exc_info:
                await import_skill_from_url(
                    org_id=test_org_id,
                    request=request,
                    user_data=(test_user_id, mock_user_profile),
                )

            assert exc_info.value.status_code == 400
