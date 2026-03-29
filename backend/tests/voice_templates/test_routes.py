"""Smoke tests for voice template routes."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID, uuid4


SAMPLE_TEMPLATE = {
    "id": "00000000-0000-0000-0000-000000000001",
    "name": "Dental Receptionist",
    "industry": "dental",
    "description": "Friendly dental office receptionist.",
    "persona": "You are Alex, a dental receptionist.",
    "tone": "warm, professional, reassuring",
    "mission": "Help patients schedule dental appointments.",
    "greeting": "Thank you for calling [Business Name]! This is Alex.",
    "custom_instructions": "Always confirm appointment details.",
    "is_active": True,
    "created_at": datetime.now(timezone.utc).isoformat(),
    "updated_at": datetime.now(timezone.utc).isoformat(),
}


class TestListVoiceTemplates:
    """Tests for GET /api/v1/voice-templates/"""

    @pytest.mark.asyncio
    async def test_list_templates_success(self):
        """Returns list of active templates."""
        from src.voice_templates.routes import list_voice_templates
        from src.voice_templates.models import VoiceTemplate

        mock_template = VoiceTemplate(**SAMPLE_TEMPLATE)
        mock_user = (UUID("00000000-0000-0000-0000-000000000002"), Mock())

        with patch("src.voice_templates.routes.voice_template_service") as mock_svc:
            mock_svc.list_templates = AsyncMock(return_value=([mock_template], None))
            result = await list_voice_templates(industry=None, _=mock_user)

        assert len(result) == 1
        assert result[0].name == "Dental Receptionist"
        mock_svc.list_templates.assert_awaited_once_with(industry=None)

    @pytest.mark.asyncio
    async def test_list_templates_filtered_by_industry(self):
        """Returns templates filtered by industry."""
        from src.voice_templates.routes import list_voice_templates
        from src.voice_templates.models import VoiceTemplate

        mock_template = VoiceTemplate(**SAMPLE_TEMPLATE)
        mock_user = (UUID("00000000-0000-0000-0000-000000000002"), Mock())

        with patch("src.voice_templates.routes.voice_template_service") as mock_svc:
            mock_svc.list_templates = AsyncMock(return_value=([mock_template], None))
            result = await list_voice_templates(industry="dental", _=mock_user)

        assert len(result) == 1
        mock_svc.list_templates.assert_awaited_once_with(industry="dental")

    @pytest.mark.asyncio
    async def test_list_templates_service_error_raises_500(self):
        """Service error propagates as HTTP 500."""
        from src.voice_templates.routes import list_voice_templates
        from fastapi import HTTPException

        mock_user = (UUID("00000000-0000-0000-0000-000000000002"), Mock())

        with patch("src.voice_templates.routes.voice_template_service") as mock_svc:
            mock_svc.list_templates = AsyncMock(return_value=([], "DB connection failed"))
            with pytest.raises(HTTPException) as exc_info:
                await list_voice_templates(industry=None, _=mock_user)

        assert exc_info.value.status_code == 500
        assert "DB connection failed" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_list_templates_empty_list(self):
        """Returns empty list when no templates available."""
        from src.voice_templates.routes import list_voice_templates

        mock_user = (UUID("00000000-0000-0000-0000-000000000002"), Mock())

        with patch("src.voice_templates.routes.voice_template_service") as mock_svc:
            mock_svc.list_templates = AsyncMock(return_value=([], None))
            result = await list_voice_templates(industry=None, _=mock_user)

        assert result == []


class TestGetVoiceTemplate:
    """Tests for GET /api/v1/voice-templates/{template_id}"""

    @pytest.mark.asyncio
    async def test_get_template_success(self):
        """Returns template by ID."""
        from src.voice_templates.routes import get_voice_template
        from src.voice_templates.models import VoiceTemplate

        template_id = UUID(SAMPLE_TEMPLATE["id"])
        mock_template = VoiceTemplate(**SAMPLE_TEMPLATE)
        mock_user = (UUID("00000000-0000-0000-0000-000000000002"), Mock())

        with patch("src.voice_templates.routes.voice_template_service") as mock_svc:
            mock_svc.get_template_by_id = AsyncMock(return_value=(mock_template, None))
            result = await get_voice_template(template_id=template_id, _=mock_user)

        assert result.id == template_id
        assert result.industry == "dental"

    @pytest.mark.asyncio
    async def test_get_template_not_found_raises_404(self):
        """Missing template raises HTTP 404."""
        from src.voice_templates.routes import get_voice_template
        from fastapi import HTTPException

        template_id = uuid4()
        mock_user = (UUID("00000000-0000-0000-0000-000000000002"), Mock())

        with patch("src.voice_templates.routes.voice_template_service") as mock_svc:
            mock_svc.get_template_by_id = AsyncMock(return_value=(None, "Voice template not found"))
            with pytest.raises(HTTPException) as exc_info:
                await get_voice_template(template_id=template_id, _=mock_user)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_template_service_error_raises_500(self):
        """Service error (non-not-found) propagates as HTTP 500."""
        from src.voice_templates.routes import get_voice_template
        from fastapi import HTTPException

        template_id = uuid4()
        mock_user = (UUID("00000000-0000-0000-0000-000000000002"), Mock())

        with patch("src.voice_templates.routes.voice_template_service") as mock_svc:
            mock_svc.get_template_by_id = AsyncMock(return_value=(None, "Unexpected DB error"))
            with pytest.raises(HTTPException) as exc_info:
                await get_voice_template(template_id=template_id, _=mock_user)

        assert exc_info.value.status_code == 500
