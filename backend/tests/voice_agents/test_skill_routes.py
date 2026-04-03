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

    @pytest.mark.asyncio
    async def test_update_built_in_skill_blocks_content_edit(self):
        """Test that built-in skills cannot have content or name edited."""
        from src.voice_agents.skill_routes import update_skill
        from shared.voice_agents.skill_models import OrganizationSkill, OrganizationSkillUpdate
        from fastapi import HTTPException

        test_org_id = UUID("00000000-0000-0000-0000-000000000001")
        test_skill_id = UUID("00000000-0000-0000-0000-000000000010")
        test_user_id = UUID("00000000-0000-0000-0000-000000000003")

        existing_skill = OrganizationSkill(
            id=test_skill_id,
            organization_id=test_org_id,
            slug="appointment-booking",
            name="Appointment Booking",
            content="# Original",
            category="built_in",
            is_active=True,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )

        update_data = OrganizationSkillUpdate(content="# Modified")

        mock_user_profile = Mock()
        mock_user_profile.has_role = Mock(return_value=True)

        with patch("src.voice_agents.skill_routes.skill_service") as mock_service:
            mock_service.get_skill_by_id = AsyncMock(return_value=(existing_skill, None))

            with pytest.raises(HTTPException) as exc_info:
                await update_skill(
                    org_id=test_org_id,
                    skill_id=test_skill_id,
                    skill_data=update_data,
                    user_data=(test_user_id, mock_user_profile),
                )

            assert exc_info.value.status_code == 400
            assert "Built-in" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_update_built_in_skill_allows_disable(self):
        """Test that built-in skills can be disabled (is_active toggle)."""
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
            category="built_in",
            is_active=True,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )

        disabled_skill = existing_skill.model_copy(update={"is_active": False})
        update_data = OrganizationSkillUpdate(is_active=False)

        mock_user_profile = Mock()
        mock_user_profile.has_role = Mock(return_value=True)

        with patch("src.voice_agents.skill_routes.skill_service") as mock_service:
            mock_service.get_skill_by_id = AsyncMock(return_value=(existing_skill, None))
            mock_service.update_skill = AsyncMock(return_value=(disabled_skill, None))

            result = await update_skill(
                org_id=test_org_id,
                skill_id=test_skill_id,
                skill_data=update_data,
                user_data=(test_user_id, mock_user_profile),
            )

            assert result.is_active is False

    @pytest.mark.asyncio
    async def test_delete_built_in_skill_blocked(self):
        """Test that built-in skills cannot be deleted."""
        from src.voice_agents.skill_routes import delete_skill
        from shared.voice_agents.skill_models import OrganizationSkill
        from fastapi import HTTPException

        test_org_id = UUID("00000000-0000-0000-0000-000000000001")
        test_skill_id = UUID("00000000-0000-0000-0000-000000000010")
        test_user_id = UUID("00000000-0000-0000-0000-000000000003")

        existing_skill = OrganizationSkill(
            id=test_skill_id,
            organization_id=test_org_id,
            slug="appointment-booking",
            name="Appointment Booking",
            content="# Original",
            category="built_in",
            is_active=True,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )

        mock_user_profile = Mock()
        mock_user_profile.has_role = Mock(return_value=True)

        with patch("src.voice_agents.skill_routes.skill_service") as mock_service:
            mock_service.get_skill_by_id = AsyncMock(return_value=(existing_skill, None))

            with pytest.raises(HTTPException) as exc_info:
                await delete_skill(
                    org_id=test_org_id,
                    skill_id=test_skill_id,
                    user_data=(test_user_id, mock_user_profile),
                )

            assert exc_info.value.status_code == 400
            assert "cannot be deleted" in exc_info.value.detail.lower()

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
    async def test_sync_all_requires_platform_admin(self):
        """Test that only platform admins can sync skills across all orgs."""
        from src.voice_agents.skill_routes import sync_built_in_skills_all_orgs
        from fastapi import HTTPException

        test_user_id = UUID("00000000-0000-0000-0000-000000000003")

        mock_user_profile = Mock()
        mock_user_profile.has_role = Mock(return_value=False)

        with pytest.raises(HTTPException) as exc_info:
            await sync_built_in_skills_all_orgs(
                user_data=(test_user_id, mock_user_profile),
            )

        assert exc_info.value.status_code == 403
        assert "platform admin" in exc_info.value.detail.lower()
