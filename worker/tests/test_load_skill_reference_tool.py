"""
Tests for the load_skill_reference tool used in progressive skill disclosure.

Tests cover: function binding, file content retrieval, error handling,
org+slug scoping, and graceful fallback messages.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID


class TestLoadSkillReferenceTool:
    """Test cases for the load_skill_reference tool."""

    @pytest.fixture
    def mock_skill_service(self):
        """Create a mock skill service."""
        service = MagicMock()
        service.get_skill_file_content_by_slug = AsyncMock()
        return service

    @pytest.mark.asyncio
    async def test_load_skill_reference_returns_content(self, mock_skill_service):
        """Test successful reference file content loading."""
        from src.tools.skill_tool import create_load_skill_reference_function

        mock_skill_service.get_skill_file_content_by_slug.return_value = (
            "# Booking Policies\n\n- Confirm insurance\n- Verify ID",
            None,
        )

        load_ref = create_load_skill_reference_function(
            "00000000-0000-0000-0000-000000000001",
            mock_skill_service,
        )

        result = await load_ref("appointment-booking", "references/policies.md")

        assert "Booking Policies" in result
        assert "confirm insurance" in result.lower()
        mock_skill_service.get_skill_file_content_by_slug.assert_called_once_with(
            UUID("00000000-0000-0000-0000-000000000001"),
            "appointment-booking",
            "references/policies.md",
        )

    @pytest.mark.asyncio
    async def test_load_skill_reference_not_found_returns_friendly_message(
        self, mock_skill_service
    ):
        """Test graceful handling when file doesn't exist."""
        from src.tools.skill_tool import create_load_skill_reference_function

        mock_skill_service.get_skill_file_content_by_slug.return_value = (
            None,
            "File 'missing.md' not found",
        )

        load_ref = create_load_skill_reference_function(
            "00000000-0000-0000-0000-000000000001",
            mock_skill_service,
        )

        result = await load_ref("test-skill", "missing.md")

        assert "not available" in result.lower()
        assert "missing.md" in result
        assert "test-skill" in result

    @pytest.mark.asyncio
    async def test_load_skill_reference_skill_not_found(self, mock_skill_service):
        """Test handling when the skill itself doesn't exist."""
        from src.tools.skill_tool import create_load_skill_reference_function

        mock_skill_service.get_skill_file_content_by_slug.return_value = (
            None,
            "Skill 'bad-skill' not found or inactive",
        )

        load_ref = create_load_skill_reference_function(
            "00000000-0000-0000-0000-000000000001",
            mock_skill_service,
        )

        result = await load_ref("bad-skill", "some/file.md")

        assert "not available" in result.lower()

    @pytest.mark.asyncio
    async def test_load_skill_reference_exception_returns_fallback(
        self, mock_skill_service
    ):
        """Test that exceptions are caught and return a fallback message."""
        from src.tools.skill_tool import create_load_skill_reference_function

        mock_skill_service.get_skill_file_content_by_slug.side_effect = Exception(
            "DB connection failed"
        )

        load_ref = create_load_skill_reference_function(
            "00000000-0000-0000-0000-000000000001",
            mock_skill_service,
        )

        result = await load_ref("appointment-booking", "references/policies.md")

        assert "unable to load" in result.lower()
        assert "appointment-booking" in result
        assert "references/policies.md" in result

    @pytest.mark.asyncio
    async def test_load_skill_reference_scoped_to_org(self, mock_skill_service):
        """Test that reference loading is scoped to the correct organization."""
        from src.tools.skill_tool import create_load_skill_reference_function

        org_id = "22222222-2222-2222-2222-222222222222"
        mock_skill_service.get_skill_file_content_by_slug.return_value = (
            "# Content",
            None,
        )

        load_ref = create_load_skill_reference_function(org_id, mock_skill_service)
        await load_ref("my-skill", "ref.md")

        call_args = mock_skill_service.get_skill_file_content_by_slug.call_args
        assert str(call_args[0][0]) == org_id

    def test_create_load_skill_reference_returns_callable(self, mock_skill_service):
        """Test that create_load_skill_reference_function returns an async callable."""
        from src.tools.skill_tool import create_load_skill_reference_function
        import asyncio

        load_ref = create_load_skill_reference_function(
            "00000000-0000-0000-0000-000000000001",
            mock_skill_service,
        )

        assert callable(load_ref)
        assert asyncio.iscoroutinefunction(load_ref)

    def test_load_skill_reference_has_docstring(self, mock_skill_service):
        """Test that the function has a proper docstring for the LLM."""
        from src.tools.skill_tool import create_load_skill_reference_function

        load_ref = create_load_skill_reference_function(
            "00000000-0000-0000-0000-000000000001",
            mock_skill_service,
        )

        assert load_ref.__doc__ is not None
        assert "reference" in load_ref.__doc__.lower()
        assert "file" in load_ref.__doc__.lower()
        assert "skill_slug" in load_ref.__doc__
        assert "file_path" in load_ref.__doc__

    @pytest.mark.asyncio
    async def test_load_skill_reference_with_code_file(self, mock_skill_service):
        """Test loading a script reference file."""
        from src.tools.skill_tool import create_load_skill_reference_function

        mock_skill_service.get_skill_file_content_by_slug.return_value = (
            "def validate_email(email):\n    return '@' in email",
            None,
        )

        load_ref = create_load_skill_reference_function(
            "00000000-0000-0000-0000-000000000001",
            mock_skill_service,
        )

        result = await load_ref("email-tool", "scripts/validate.py")

        assert "validate_email" in result
        assert "@" in result
