"""Tests for platform-admin voice template CRUD routes."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from src.voice_templates.models import (
    VoiceTemplate,
    VoiceTemplateCreate,
    VoiceTemplateUpdate,
)

TEST_USER_ID = UUID("00000000-0000-0000-0000-000000000002")
TEST_TEMPLATE_ID = UUID("00000000-0000-0000-0000-000000000001")


def _profile(is_admin: bool) -> Mock:
    """Build a profile whose platform-admin role can be toggled."""
    profile = Mock()
    profile.has_role = Mock(return_value=is_admin)
    return profile


def _template(*, is_active: bool = True) -> VoiceTemplate:
    """Build a representative voice template response."""
    return VoiceTemplate(
        id=TEST_TEMPLATE_ID,
        name="Dental Receptionist",
        industry="dental",
        description="Friendly dental receptionist.",
        persona="You are a helpful dental receptionist.",
        tone="warm",
        mission="Schedule dental appointments.",
        greeting="Thanks for calling {{org.name}}.",
        custom_instructions="Confirm the date and time.",
        is_active=is_active,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


class TestPlatformVoiceTemplateRoutes:
    """Authorization and CRUD behavior for platform voice templates."""

    @pytest.mark.asyncio
    async def test_admin_list_requires_platform_admin(self):
        """Inactive-inclusive catalog reads are restricted to platform admins."""
        from src.voice_templates.routes import list_admin_voice_templates

        with pytest.raises(HTTPException) as exc_info:
            await list_admin_voice_templates(
                user_data=(TEST_USER_ID, _profile(False)),
            )

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_list_returns_active_and_inactive_templates(self):
        """Platform admins receive the full catalog for management."""
        from src.voice_templates.routes import list_admin_voice_templates

        templates = [_template(), _template(is_active=False)]
        with patch("src.voice_templates.routes.voice_template_service") as service:
            service.list_templates = AsyncMock(return_value=(templates, None))
            result = await list_admin_voice_templates(
                user_data=(TEST_USER_ID, _profile(True)),
            )

        assert result == templates
        service.list_templates.assert_awaited_once_with(
            industry=None,
            include_inactive=True,
        )

    @pytest.mark.asyncio
    async def test_admin_list_service_error_raises_500(self):
        """Admin catalog failures are returned as server errors."""
        from src.voice_templates.routes import list_admin_voice_templates

        with patch("src.voice_templates.routes.voice_template_service") as service:
            service.list_templates = AsyncMock(return_value=([], "database down"))
            with pytest.raises(HTTPException) as exc_info:
                await list_admin_voice_templates(
                    user_data=(TEST_USER_ID, _profile(True)),
                )

        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_admin_get_returns_inactive_template_for_admin(self):
        """Admins can open an inactive row for editing."""
        from src.voice_templates.routes import get_admin_voice_template

        with patch("src.voice_templates.routes.voice_template_service") as service:
            service.get_template_by_id = AsyncMock(
                return_value=(_template(is_active=False), None)
            )
            result = await get_admin_voice_template(
                template_id=TEST_TEMPLATE_ID,
                user_data=(TEST_USER_ID, _profile(True)),
            )

        assert result.is_active is False
        service.get_template_by_id.assert_awaited_once_with(
            TEST_TEMPLATE_ID,
            include_inactive=True,
        )

    @pytest.mark.asyncio
    async def test_create_requires_platform_admin_and_persists_template(self):
        """Only platform admins can create a reusable template."""
        from src.voice_templates.routes import create_admin_voice_template

        payload = VoiceTemplateCreate(name="New Template", industry="plumbing")
        with pytest.raises(HTTPException) as exc_info:
            await create_admin_voice_template(
                template_data=payload,
                user_data=(TEST_USER_ID, _profile(False)),
            )
        assert exc_info.value.status_code == 403

        with patch("src.voice_templates.routes.voice_template_service") as service:
            service.create_template = AsyncMock(return_value=(_template(), None))
            result = await create_admin_voice_template(
                template_data=payload,
                user_data=(TEST_USER_ID, _profile(True)),
            )

        assert result.name == "Dental Receptionist"
        service.create_template.assert_awaited_once_with(payload)

    @pytest.mark.asyncio
    async def test_update_maps_missing_template_to_not_found(self):
        """Updating a missing template returns a stable 404 response."""
        from src.voice_templates.routes import update_admin_voice_template

        payload = VoiceTemplateUpdate(description="Updated")
        with patch("src.voice_templates.routes.voice_template_service") as service:
            service.update_template = AsyncMock(
                return_value=(None, "Voice template not found")
            )
            with pytest.raises(HTTPException) as exc_info:
                await update_admin_voice_template(
                    template_id=uuid4(),
                    template_data=payload,
                    user_data=(TEST_USER_ID, _profile(True)),
                )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_create_and_update_service_errors_map_to_400(self):
        """Write failures other than missing rows are client-visible 400s."""
        from src.voice_templates.routes import (
            create_admin_voice_template,
            update_admin_voice_template,
        )

        create_payload = VoiceTemplateCreate(name="New Template", industry="dental")
        update_payload = VoiceTemplateUpdate(description="Updated")
        with patch("src.voice_templates.routes.voice_template_service") as service:
            service.create_template = AsyncMock(return_value=(None, "duplicate name"))
            with pytest.raises(HTTPException) as create_error:
                await create_admin_voice_template(
                    template_data=create_payload,
                    user_data=(TEST_USER_ID, _profile(True)),
                )

            service.update_template = AsyncMock(
                return_value=(None, "validation failed")
            )
            with pytest.raises(HTTPException) as update_error:
                await update_admin_voice_template(
                    template_id=TEST_TEMPLATE_ID,
                    template_data=update_payload,
                    user_data=(TEST_USER_ID, _profile(True)),
                )

        assert create_error.value.status_code == 400
        assert update_error.value.status_code == 400

    @pytest.mark.asyncio
    async def test_update_returns_updated_template(self):
        """Successful edits return the updated typed response."""
        from src.voice_templates.routes import update_admin_voice_template

        payload = VoiceTemplateUpdate(description="Updated")
        with patch("src.voice_templates.routes.voice_template_service") as service:
            service.update_template = AsyncMock(return_value=(_template(), None))
            result = await update_admin_voice_template(
                template_id=TEST_TEMPLATE_ID,
                template_data=payload,
                user_data=(TEST_USER_ID, _profile(True)),
            )

        assert result.id == TEST_TEMPLATE_ID

    @pytest.mark.asyncio
    async def test_delete_requires_platform_admin_and_deletes_template(self):
        """Deletion is admin-only and returns no content on success."""
        from src.voice_templates.routes import delete_admin_voice_template

        with pytest.raises(HTTPException) as exc_info:
            await delete_admin_voice_template(
                template_id=TEST_TEMPLATE_ID,
                user_data=(TEST_USER_ID, _profile(False)),
            )
        assert exc_info.value.status_code == 403

        with patch("src.voice_templates.routes.voice_template_service") as service:
            service.delete_template = AsyncMock(return_value=(True, None))
            result = await delete_admin_voice_template(
                template_id=TEST_TEMPLATE_ID,
                user_data=(TEST_USER_ID, _profile(True)),
            )

        assert result is None
        service.delete_template.assert_awaited_once_with(TEST_TEMPLATE_ID)

    @pytest.mark.asyncio
    async def test_delete_maps_missing_and_generic_errors(self):
        """Delete failures distinguish missing rows from other write errors."""
        from src.voice_templates.routes import delete_admin_voice_template

        with patch("src.voice_templates.routes.voice_template_service") as service:
            service.delete_template = AsyncMock(
                return_value=(None, "Voice template not found")
            )
            with pytest.raises(HTTPException) as not_found:
                await delete_admin_voice_template(
                    template_id=TEST_TEMPLATE_ID,
                    user_data=(TEST_USER_ID, _profile(True)),
                )

            service.delete_template = AsyncMock(return_value=(None, "database down"))
            with pytest.raises(HTTPException) as bad_request:
                await delete_admin_voice_template(
                    template_id=TEST_TEMPLATE_ID,
                    user_data=(TEST_USER_ID, _profile(True)),
                )

        assert not_found.value.status_code == 404
        assert bad_request.value.status_code == 400
