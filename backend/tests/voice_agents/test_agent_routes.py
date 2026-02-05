"""
Tests for voice agent routes.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID


class TestAgentRoutes:
    """Test cases for agent routes."""

    @pytest.mark.asyncio
    async def test_get_agent_system_prompt_success(self):
        """Test successful retrieval of generated system prompt."""
        from src.voice_agents.routes import get_agent_system_prompt
        from shared.voice_agents.models import VoiceAgent
        from shared.organization.models import Organization

        # Create test data
        test_agent_id = UUID("00000000-0000-0000-0000-000000000001")
        test_org_id = UUID("00000000-0000-0000-0000-000000000002")
        test_user_id = UUID("00000000-0000-0000-0000-000000000003")

        agent = VoiceAgent(
            id=test_agent_id,
            organization_id=test_org_id,
            name="Test Agent",
            phone_number="+1234567890",
            persona="Support Specialist",
            tone="Professional",
            mission="Help customers with their inquiries",
            custom_instructions="Always be polite and helpful",
            is_active=True,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )

        org = Organization(
            id=test_org_id,
            name="Test Organization",
            slug="test-org",
            description="A test organization",
            industry="Technology",
            location="123 Test St",
            business_details="We provide excellent tech support",
            is_active=True,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )

        # Mock user profile
        mock_user_profile = Mock()
        mock_user_profile.has_role = Mock(return_value=True)

        # Mock voice_agent_service
        with patch("src.voice_agents.routes.voice_agent_service") as mock_voice_service:
            mock_voice_service.get_agent_by_id = AsyncMock(return_value=(agent, None))

            # Mock OrganizationService
            with patch("src.voice_agents.routes.OrganizationService") as mock_org_service_class:
                mock_org_service = Mock()
                mock_org_service.get_organization_by_id = AsyncMock(return_value=(org, None))
                mock_org_service_class.return_value = mock_org_service

                # Call the endpoint
                result = await get_agent_system_prompt(
                    agent_id=test_agent_id,
                    user_data=(test_user_id, mock_user_profile),
                )

                # Verify the result contains expected sections
                assert "Support Specialist" in result
                assert "Test Organization" in result
                assert "Professional" in result
                assert "Help customers" in result
                assert "tech support" in result
                assert "polite and helpful" in result

    @pytest.mark.asyncio
    async def test_get_agent_system_prompt_agent_not_found(self):
        """Test system prompt retrieval when agent doesn't exist."""
        from src.voice_agents.routes import get_agent_system_prompt
        from fastapi import HTTPException

        test_agent_id = UUID("00000000-0000-0000-0000-000000000001")
        test_user_id = UUID("00000000-0000-0000-0000-000000000003")

        mock_user_profile = Mock()
        mock_user_profile.has_role = Mock(return_value=True)

        with patch("src.voice_agents.routes.voice_agent_service") as mock_voice_service:
            mock_voice_service.get_agent_by_id = AsyncMock(
                return_value=(None, "Agent not found")
            )

            with pytest.raises(HTTPException) as exc_info:
                await get_agent_system_prompt(
                    agent_id=test_agent_id,
                    user_data=(test_user_id, mock_user_profile),
                )

            assert exc_info.value.status_code == 404
            assert "Agent not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_agent_system_prompt_permission_denied(self):
        """Test system prompt retrieval without proper permissions."""
        from src.voice_agents.routes import get_agent_system_prompt
        from fastapi import HTTPException
        from shared.voice_agents.models import VoiceAgent

        test_agent_id = UUID("00000000-0000-0000-0000-000000000001")
        test_org_id = UUID("00000000-0000-0000-0000-000000000002")
        test_user_id = UUID("00000000-0000-0000-0000-000000000003")

        agent = VoiceAgent(
            id=test_agent_id,
            organization_id=test_org_id,
            name="Test Agent",
            phone_number="+1234567890",
            is_active=True,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )

        # Mock user profile that denies all permissions
        mock_user_profile = Mock()
        mock_user_profile.has_role = Mock(return_value=False)

        with patch("src.voice_agents.routes.voice_agent_service") as mock_voice_service:
            mock_voice_service.get_agent_by_id = AsyncMock(return_value=(agent, None))

            with pytest.raises(HTTPException) as exc_info:
                await get_agent_system_prompt(
                    agent_id=test_agent_id,
                    user_data=(test_user_id, mock_user_profile),
                )

            assert exc_info.value.status_code == 403
            assert "Insufficient permissions" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_agent_system_prompt_org_not_found(self):
        """Test system prompt retrieval when organization doesn't exist."""
        from src.voice_agents.routes import get_agent_system_prompt
        from fastapi import HTTPException
        from shared.voice_agents.models import VoiceAgent

        test_agent_id = UUID("00000000-0000-0000-0000-000000000001")
        test_org_id = UUID("00000000-0000-0000-0000-000000000002")
        test_user_id = UUID("00000000-0000-0000-0000-000000000003")

        agent = VoiceAgent(
            id=test_agent_id,
            organization_id=test_org_id,
            name="Test Agent",
            phone_number="+1234567890",
            is_active=True,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )

        mock_user_profile = Mock()
        mock_user_profile.has_role = Mock(return_value=True)

        with patch("src.voice_agents.routes.voice_agent_service") as mock_voice_service:
            mock_voice_service.get_agent_by_id = AsyncMock(return_value=(agent, None))

            with patch("src.voice_agents.routes.OrganizationService") as mock_org_service_class:
                mock_org_service = Mock()
                mock_org_service.get_organization_by_id = AsyncMock(
                    return_value=(None, "Organization not found")
                )
                mock_org_service_class.return_value = mock_org_service

                with pytest.raises(HTTPException) as exc_info:
                    await get_agent_system_prompt(
                        agent_id=test_agent_id,
                        user_data=(test_user_id, mock_user_profile),
                    )

                assert exc_info.value.status_code == 500
                assert "Could not fetch organization" in exc_info.value.detail
