"""
Tests for the load_skill tool used in progressive skill disclosure.

Tests cover: function binding, content retrieval, error handling,
org scoping, and graceful fallback messages.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID


class TestLoadSkillTool:
    """Test cases for the load_skill tool."""

    @pytest.fixture
    def mock_skill_service(self):
        """Create a mock skill service."""
        service = MagicMock()
        service.get_skill_content_by_slug = AsyncMock()
        return service

    @pytest.mark.asyncio
    async def test_load_skill_returns_content(self, mock_skill_service):
        """Test successful skill content loading."""
        from src.tools.skill_tool import create_load_skill_function

        mock_skill_service.get_skill_content_by_slug.return_value = (
            "# Appointment Booking\n\n## Procedure\n1. Ask for date\n2. Check availability",
            None,
        )

        load_skill = create_load_skill_function(
            "00000000-0000-0000-0000-000000000001",
            mock_skill_service,
        )

        result = await load_skill("appointment-booking")

        assert "Appointment Booking" in result
        assert "Procedure" in result
        mock_skill_service.get_skill_content_by_slug.assert_called_once_with(
            UUID("00000000-0000-0000-0000-000000000001"),
            "appointment-booking",
        )

    @pytest.mark.asyncio
    async def test_load_skill_not_found_returns_friendly_message(self, mock_skill_service):
        """Test graceful handling when skill doesn't exist."""
        from src.tools.skill_tool import create_load_skill_function

        mock_skill_service.get_skill_content_by_slug.return_value = (
            None,
            "Skill 'nonexistent' not found or inactive",
        )

        load_skill = create_load_skill_function(
            "00000000-0000-0000-0000-000000000001",
            mock_skill_service,
        )

        result = await load_skill("nonexistent")

        assert "not available" in result.lower()
        assert "nonexistent" in result

    @pytest.mark.asyncio
    async def test_load_skill_exception_returns_fallback(self, mock_skill_service):
        """Test that exceptions are caught and return a fallback message."""
        from src.tools.skill_tool import create_load_skill_function

        mock_skill_service.get_skill_content_by_slug.side_effect = Exception("DB connection failed")

        load_skill = create_load_skill_function(
            "00000000-0000-0000-0000-000000000001",
            mock_skill_service,
        )

        result = await load_skill("appointment-booking")

        assert "unable to load" in result.lower()
        assert "appointment-booking" in result

    @pytest.mark.asyncio
    async def test_load_skill_scoped_to_org(self, mock_skill_service):
        """Test that skill loading is scoped to the correct organization."""
        from src.tools.skill_tool import create_load_skill_function

        org_id = "11111111-1111-1111-1111-111111111111"
        mock_skill_service.get_skill_content_by_slug.return_value = ("# Content", None)

        load_skill = create_load_skill_function(org_id, mock_skill_service)
        await load_skill("test-skill")

        # Verify the correct org_id was passed
        call_args = mock_skill_service.get_skill_content_by_slug.call_args
        assert str(call_args[0][0]) == org_id

    def test_create_load_skill_function_returns_callable(self, mock_skill_service):
        """Test that create_load_skill_function returns an async callable."""
        from src.tools.skill_tool import create_load_skill_function
        import asyncio

        load_skill = create_load_skill_function(
            "00000000-0000-0000-0000-000000000001",
            mock_skill_service,
        )

        assert callable(load_skill)
        assert asyncio.iscoroutinefunction(load_skill)

    def test_load_skill_has_docstring(self, mock_skill_service):
        """Test that the load_skill function has a proper docstring for the LLM."""
        from src.tools.skill_tool import create_load_skill_function

        load_skill = create_load_skill_function(
            "00000000-0000-0000-0000-000000000001",
            mock_skill_service,
        )

        assert load_skill.__doc__ is not None
        assert "load" in load_skill.__doc__.lower()
        assert "skill" in load_skill.__doc__.lower()
