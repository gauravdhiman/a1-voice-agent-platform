"""Tests for the platform-admin preset API routes (Phase 3).

Mirrors the platform-skill route tests: the route handler is invoked directly
with a mock UserProfile (``has_role`` controls platform_admin), the preset
service is patched with AsyncMock, and we assert 403 for non-admins on the
admin-only endpoints plus the success / 404 / 409 paths.
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID

import pytest
from fastapi import HTTPException

from shared.voice_agents.preset_models import Preset, PresetType

TEST_USER_ID = UUID("00000000-0000-0000-0000-000000000003")
TEST_PRESET_ID = UUID("00000000-0000-0000-0000-000000000110")


def _profile(is_admin: bool) -> Mock:
    """Build a mock UserProfile whose has_role reports platform_admin or not."""
    p = Mock()
    p.has_role = Mock(return_value=is_admin)
    return p


def _preset(
    is_published: bool = True,
    preset_type: PresetType = PresetType.REALTIME,
    name="Default Realtime",
    is_default: bool = False,
) -> Preset:
    return Preset(
        id=TEST_PRESET_ID,
        name=name,
        preset_type=preset_type,
        config=(
            {"engine_mode": "realtime"}
            if preset_type is PresetType.REALTIME
            else {
                "engine_mode": "pipeline",
                "stt": {"provider": "deepgram"},
                "llm": {"provider": "openai"},
                "tts": {"provider": "cartesia"},
            }
        ),
        is_published=is_published,
        is_default=is_default,
        created_at=datetime(2026, 7, 29),
        updated_at=datetime(2026, 7, 29),
    )


class TestPresetRoutesAuthz:
    """Authorization + success-path tests for the preset routes."""

    @pytest.mark.asyncio
    async def test_create_preset_requires_platform_admin(self):
        """Create/upsert is 403 for non-admins."""
        from src.voice_agents.preset_routes import create_preset

        with pytest.raises(HTTPException) as exc_info:
            await create_preset(
                preset_data=Mock(),
                user_data=(TEST_USER_ID, _profile(is_admin=False)),
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_create_preset_succeeds_for_admin(self):
        """Admin create returns the upserted preset (201 via route decorator)."""
        from src.voice_agents.preset_routes import create_preset

        with patch("src.voice_agents.preset_routes.preset_service") as mock_service:
            mock_service.upsert_preset = AsyncMock(return_value=(_preset(), None))
            # PresetCreate with a realtime config.
            from shared.voice_agents.preset_models import PresetCreate

            body = PresetCreate(
                name="Default Realtime", config={"engine_mode": "realtime"}
            )
            result = await create_preset(
                preset_data=body,
                user_data=(TEST_USER_ID, _profile(is_admin=True)),
            )
        assert result.name == "Default Realtime"

    @pytest.mark.asyncio
    async def test_create_preset_validation_error_returns_400(self):
        """A service validation error surfaces as 400."""
        from src.voice_agents.preset_routes import create_preset

        with patch("src.voice_agents.preset_routes.preset_service") as mock_service:
            mock_service.upsert_preset = AsyncMock(
                return_value=(None, "Invalid speech config: boom")
            )
            from shared.voice_agents.preset_models import PresetCreate

            body = PresetCreate(name="X", config={"engine_mode": "realtime"})
            with pytest.raises(HTTPException) as exc_info:
                await create_preset(
                    preset_data=body,
                    user_data=(TEST_USER_ID, _profile(is_admin=True)),
                )
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_update_preset_requires_platform_admin(self):
        from src.voice_agents.preset_routes import update_preset

        with pytest.raises(HTTPException) as exc_info:
            await update_preset(
                preset_id=TEST_PRESET_ID,
                preset_data=Mock(),
                user_data=(TEST_USER_ID, _profile(is_admin=False)),
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_update_preset_not_found_returns_404(self):
        from shared.voice_agents.preset_models import PresetUpdate
        from src.voice_agents.preset_routes import update_preset

        with patch("src.voice_agents.preset_routes.preset_service") as mock_service:
            mock_service.update_preset = AsyncMock(
                return_value=(None, "Preset not found")
            )
            with pytest.raises(HTTPException) as exc_info:
                await update_preset(
                    preset_id=TEST_PRESET_ID,
                    preset_data=PresetUpdate(name="Renamed"),
                    user_data=(TEST_USER_ID, _profile(is_admin=True)),
                )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_publish_preset_requires_platform_admin(self):
        from src.voice_agents.preset_routes import publish_preset

        with pytest.raises(HTTPException) as exc_info:
            await publish_preset(
                preset_id=TEST_PRESET_ID,
                user_data=(TEST_USER_ID, _profile(is_admin=False)),
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_publish_preset_succeeds_for_admin(self):
        from src.voice_agents.preset_routes import publish_preset

        with patch("src.voice_agents.preset_routes.preset_service") as mock_service:
            mock_service.publish_preset = AsyncMock(
                return_value=(_preset(is_published=True), None)
            )
            result = await publish_preset(
                preset_id=TEST_PRESET_ID,
                user_data=(TEST_USER_ID, _profile(is_admin=True)),
            )
        assert result.is_published is True
        mock_service.publish_preset.assert_awaited_once_with(TEST_PRESET_ID, True)

    @pytest.mark.asyncio
    async def test_unpublish_preset_succeeds_for_admin(self):
        from src.voice_agents.preset_routes import unpublish_preset

        with patch("src.voice_agents.preset_routes.preset_service") as mock_service:
            mock_service.publish_preset = AsyncMock(
                return_value=(_preset(is_published=False), None)
            )
            result = await unpublish_preset(
                preset_id=TEST_PRESET_ID,
                user_data=(TEST_USER_ID, _profile(is_admin=True)),
            )
        assert result.is_published is False
        mock_service.publish_preset.assert_awaited_once_with(TEST_PRESET_ID, False)

    @pytest.mark.asyncio
    async def test_get_preset_usage_requires_platform_admin(self):
        from src.voice_agents.preset_routes import get_preset_usage

        with pytest.raises(HTTPException) as exc_info:
            await get_preset_usage(
                preset_id=TEST_PRESET_ID,
                user_data=(TEST_USER_ID, _profile(is_admin=False)),
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_get_preset_usage_returns_count_and_agents(self):
        from src.voice_agents.preset_routes import get_preset_usage

        agents = [
            {"id": str(UUID("00000000-0000-0000-0000-000000000001")), "name": "A"}
        ]
        with patch("src.voice_agents.preset_routes.preset_service") as mock_service:
            mock_service.get_preset_usage = AsyncMock(return_value=(agents, None))
            result = await get_preset_usage(
                preset_id=TEST_PRESET_ID,
                user_data=(TEST_USER_ID, _profile(is_admin=True)),
            )
        assert result == {"count": 1, "agents": agents}

    @pytest.mark.asyncio
    async def test_delete_preset_requires_platform_admin(self):
        from src.voice_agents.preset_routes import delete_preset

        with pytest.raises(HTTPException) as exc_info:
            await delete_preset(
                preset_id=TEST_PRESET_ID,
                force=False,
                user_data=(TEST_USER_ID, _profile(is_admin=False)),
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_preset_in_use_returns_409(self):
        from src.voice_agents.preset_routes import delete_preset

        agents = [{"id": "x", "name": "A", "organization_id": "o"}]
        with patch("src.voice_agents.preset_routes.preset_service") as mock_service:
            mock_service.delete_preset = AsyncMock(return_value=(None, "in_use"))
            mock_service.get_preset_usage = AsyncMock(return_value=(agents, None))
            with pytest.raises(HTTPException) as exc_info:
                await delete_preset(
                    preset_id=TEST_PRESET_ID,
                    force=False,
                    user_data=(TEST_USER_ID, _profile(is_admin=True)),
                )
        assert exc_info.value.status_code == 409
        assert exc_info.value.detail["error"] == "in_use"
        assert exc_info.value.detail["agents"] == agents

    @pytest.mark.asyncio
    async def test_delete_preset_not_found_returns_404(self):
        from src.voice_agents.preset_routes import delete_preset

        with patch("src.voice_agents.preset_routes.preset_service") as mock_service:
            mock_service.delete_preset = AsyncMock(
                return_value=(None, "Preset not found")
            )
            with pytest.raises(HTTPException) as exc_info:
                await delete_preset(
                    preset_id=TEST_PRESET_ID,
                    force=False,
                    user_data=(TEST_USER_ID, _profile(is_admin=True)),
                )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_preset_force_succeeds(self):
        from src.voice_agents.preset_routes import delete_preset

        with patch("src.voice_agents.preset_routes.preset_service") as mock_service:
            mock_service.delete_preset = AsyncMock(return_value=(True, None))
            result = await delete_preset(
                preset_id=TEST_PRESET_ID,
                force=True,
                user_data=(TEST_USER_ID, _profile(is_admin=True)),
            )
        assert result is None  # 204 No Content
        mock_service.delete_preset.assert_awaited_once_with(TEST_PRESET_ID, force=True)

    @pytest.mark.asyncio
    async def test_list_presets_published_only_for_non_admin(self):
        """Default list is open to non-admins (published-only)."""
        from src.voice_agents.preset_routes import list_presets

        with patch("src.voice_agents.preset_routes.preset_service") as mock_service:
            mock_service.get_presets = AsyncMock(return_value=([_preset()], None))
            result = await list_presets(
                preset_type=None,
                include_drafts=False,
                user_data=(TEST_USER_ID, _profile(is_admin=False)),
            )
        assert len(result) == 1
        called = mock_service.get_presets.call_args
        assert called.kwargs["only_published"] is True
        assert called.kwargs["include_drafts"] is False

    @pytest.mark.asyncio
    async def test_list_presets_include_drafts_requires_admin(self):
        """include_drafts=True is 403 for non-admins."""
        from src.voice_agents.preset_routes import list_presets

        with pytest.raises(HTTPException) as exc_info:
            await list_presets(
                preset_type=None,
                include_drafts=True,
                user_data=(TEST_USER_ID, _profile(is_admin=False)),
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_list_presets_include_drafts_succeeds_for_admin(self):
        from src.voice_agents.preset_routes import list_presets

        with patch("src.voice_agents.preset_routes.preset_service") as mock_service:
            mock_service.get_presets = AsyncMock(
                return_value=([_preset(is_published=False)], None)
            )
            result = await list_presets(
                preset_type=None,
                include_drafts=True,
                user_data=(TEST_USER_ID, _profile(is_admin=True)),
            )
        assert len(result) == 1
        called = mock_service.get_presets.call_args
        assert called.kwargs["include_drafts"] is True

    @pytest.mark.asyncio
    async def test_get_preset_published_open_to_any_authed(self):
        from src.voice_agents.preset_routes import get_preset

        with patch("src.voice_agents.preset_routes.preset_service") as mock_service:
            mock_service.get_preset_by_id = AsyncMock(
                return_value=(_preset(is_published=True), None)
            )
            result = await get_preset(
                preset_id=TEST_PRESET_ID,
                user_data=(TEST_USER_ID, _profile(is_admin=False)),
            )
        assert result.is_published is True

    @pytest.mark.asyncio
    async def test_get_preset_draft_requires_platform_admin(self):
        from src.voice_agents.preset_routes import get_preset

        with patch("src.voice_agents.preset_routes.preset_service") as mock_service:
            mock_service.get_preset_by_id = AsyncMock(
                return_value=(_preset(is_published=False), None)
            )
            with pytest.raises(HTTPException) as exc_info:
                await get_preset(
                    preset_id=TEST_PRESET_ID,
                    user_data=(TEST_USER_ID, _profile(is_admin=False)),
                )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_get_preset_not_found_returns_404(self):
        from src.voice_agents.preset_routes import get_preset

        with patch("src.voice_agents.preset_routes.preset_service") as mock_service:
            mock_service.get_preset_by_id = AsyncMock(return_value=(None, None))
            with pytest.raises(HTTPException) as exc_info:
                await get_preset(
                    preset_id=TEST_PRESET_ID,
                    user_data=(TEST_USER_ID, _profile(is_admin=True)),
                )
        assert exc_info.value.status_code == 404


class TestPresetDefaultRoutes:
    """System-default preset routes (GET/PUT /default) + default-row guards."""

    @pytest.mark.asyncio
    async def test_get_default_requires_platform_admin(self):
        from src.voice_agents.preset_routes import get_default_preset

        with pytest.raises(HTTPException) as exc_info:
            await get_default_preset(user_data=(TEST_USER_ID, _profile(is_admin=False)))
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_get_default_succeeds_for_admin(self):
        from src.voice_agents.preset_routes import get_default_preset

        with patch("src.voice_agents.preset_routes.preset_service") as mock_service:
            mock_service.get_default_preset = AsyncMock(
                return_value=(
                    _preset(is_default=True, is_published=False, name="System Default"),
                    None,
                )
            )
            result = await get_default_preset(
                user_data=(TEST_USER_ID, _profile(is_admin=True))
            )
        assert result.is_default is True
        assert result.name == "System Default"

    @pytest.mark.asyncio
    async def test_get_default_not_found_returns_404(self):
        from src.voice_agents.preset_routes import get_default_preset

        with patch("src.voice_agents.preset_routes.preset_service") as mock_service:
            mock_service.get_default_preset = AsyncMock(return_value=(None, None))
            with pytest.raises(HTTPException) as exc_info:
                await get_default_preset(
                    user_data=(TEST_USER_ID, _profile(is_admin=True))
                )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_default_requires_platform_admin(self):
        from src.voice_agents.preset_routes import update_default_preset

        with pytest.raises(HTTPException) as exc_info:
            await update_default_preset(
                config={"engine_mode": "realtime"},
                user_data=(TEST_USER_ID, _profile(is_admin=False)),
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_update_default_succeeds_for_admin(self):
        from src.voice_agents.preset_routes import update_default_preset

        with patch("src.voice_agents.preset_routes.preset_service") as mock_service:
            mock_service.update_default_preset = AsyncMock(
                return_value=(
                    _preset(is_default=True, is_published=False, name="System Default"),
                    None,
                )
            )
            result = await update_default_preset(
                config={"engine_mode": "realtime"},
                user_data=(TEST_USER_ID, _profile(is_admin=True)),
            )
        assert result.is_default is True
        mock_service.update_default_preset.assert_awaited_once_with(
            {"engine_mode": "realtime"}
        )

    @pytest.mark.asyncio
    async def test_update_default_invalid_config_returns_400(self):
        from src.voice_agents.preset_routes import update_default_preset

        with patch("src.voice_agents.preset_routes.preset_service") as mock_service:
            mock_service.update_default_preset = AsyncMock(
                return_value=(None, "Invalid speech config: boom")
            )
            with pytest.raises(HTTPException) as exc_info:
                await update_default_preset(
                    config={"engine_mode": "pipeline"},
                    user_data=(TEST_USER_ID, _profile(is_admin=True)),
                )
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_update_default_not_found_returns_404(self):
        from src.voice_agents.preset_routes import update_default_preset

        with patch("src.voice_agents.preset_routes.preset_service") as mock_service:
            mock_service.update_default_preset = AsyncMock(
                return_value=(None, "Default not found")
            )
            with pytest.raises(HTTPException) as exc_info:
                await update_default_preset(
                    config={"engine_mode": "realtime"},
                    user_data=(TEST_USER_ID, _profile(is_admin=True)),
                )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_publish_preset_default_row_returns_400(self):
        """Publishing the system default is rejected (service guard) -> 400."""
        from src.voice_agents.preset_routes import publish_preset

        with patch("src.voice_agents.preset_routes.preset_service") as mock_service:
            mock_service.publish_preset = AsyncMock(
                return_value=(None, "The system default preset is not publishable")
            )
            with pytest.raises(HTTPException) as exc_info:
                await publish_preset(
                    preset_id=TEST_PRESET_ID,
                    user_data=(TEST_USER_ID, _profile(is_admin=True)),
                )
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_delete_preset_default_row_returns_400(self):
        """Deleting the system default is rejected (service guard) -> 400."""
        from src.voice_agents.preset_routes import delete_preset

        with patch("src.voice_agents.preset_routes.preset_service") as mock_service:
            mock_service.delete_preset = AsyncMock(
                return_value=(None, "The system default preset cannot be deleted")
            )
            with pytest.raises(HTTPException) as exc_info:
                await delete_preset(
                    preset_id=TEST_PRESET_ID,
                    force=False,
                    user_data=(TEST_USER_ID, _profile(is_admin=True)),
                )
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_update_preset_default_row_returns_400(self):
        """The generic update path refuses the system default -> 400."""
        from shared.voice_agents.preset_models import PresetUpdate
        from src.voice_agents.preset_routes import update_preset

        with patch("src.voice_agents.preset_routes.preset_service") as mock_service:
            mock_service.update_preset = AsyncMock(
                return_value=(
                    None,
                    "The system default preset is managed via its own config editor",
                )
            )
            with pytest.raises(HTTPException) as exc_info:
                await update_preset(
                    preset_id=TEST_PRESET_ID,
                    preset_data=PresetUpdate(name="X"),
                    user_data=(TEST_USER_ID, _profile(is_admin=True)),
                )
        assert exc_info.value.status_code == 400


class TestPresetCatalogRoute:
    """Org-facing white-label catalog endpoint."""

    TEST_ORG_ID = UUID("00000000-0000-0000-0000-000000000020")

    @pytest.mark.asyncio
    async def test_catalog_returns_readiness_without_config_leak(self):
        from shared.voice_agents.preset_models import PresetCatalogResponse
        from src.voice_agents.preset_routes import get_preset_catalog

        profile = _profile(is_admin=False)
        profile.has_permission = Mock(return_value=True)

        mock_org = Mock()
        catalog = PresetCatalogResponse(
            presets=[
                {
                    "id": TEST_PRESET_ID,
                    "name": "Professional Voice",
                    "description": "Warm tone",
                    "is_ready": False,
                }
            ],
            default_is_ready=True,
            credentials_self_service=True,
        )

        with patch(
            "src.voice_agents.preset_routes.organization_service"
        ) as mock_org_svc, patch(
            "src.voice_agents.preset_routes.preset_service"
        ) as mock_preset_svc:
            mock_org_svc.get_organization_by_id = AsyncMock(
                return_value=(mock_org, None)
            )
            mock_preset_svc.get_presets = AsyncMock(
                return_value=([_preset(name="Professional Voice")], None)
            )
            mock_preset_svc.get_default_preset = AsyncMock(
                return_value=(_preset(name="System Default", is_default=True), None)
            )
            mock_preset_svc.build_preset_catalog = Mock(return_value=catalog)

            result = await get_preset_catalog(
                organization_id=self.TEST_ORG_ID,
                use_platform_credits=False,
                user_data=(TEST_USER_ID, profile),
            )

        assert result.default_is_ready is True
        assert len(result.presets) == 1
        assert result.presets[0].name == "Professional Voice"
        assert result.presets[0].is_ready is False
        assert "config" not in result.presets[0].model_dump()

    @pytest.mark.asyncio
    async def test_catalog_org_not_found_returns_404(self):
        from src.voice_agents.preset_routes import get_preset_catalog

        with patch(
            "src.voice_agents.preset_routes.organization_service"
        ) as mock_org_svc:
            mock_org_svc.get_organization_by_id = AsyncMock(
                return_value=(None, "Organization not found")
            )
            with pytest.raises(HTTPException) as exc_info:
                await get_preset_catalog(
                    organization_id=self.TEST_ORG_ID,
                    use_platform_credits=False,
                    user_data=(TEST_USER_ID, _profile(is_admin=False)),
                )
        assert exc_info.value.status_code == 404
