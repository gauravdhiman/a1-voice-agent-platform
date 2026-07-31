"""Tests for the platform-admin preset service (Phase 3).

Mirrors the ToolService tests: a mocked Supabase client, the
``(result, error)`` tuple contract, upsert-by-name, publish lifecycle, usage
join, and the delete ``in_use`` guardrail. The preset service additionally
derives ``preset_type`` from ``config.engine_mode`` on every write and re-
validates the ``SpeechConfig`` via ``parse_speech_config``.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from shared.voice_agents.preset_models import (Preset, PresetCreate,
                                               PresetType, PresetUpdate)
from shared.voice_agents.preset_service import PresetService


@pytest.fixture
def preset_service(mock_supabase_client):
    """PresetService with a mocked Supabase client."""
    with patch("shared.voice_agents.preset_service.supabase_config") as mock_cfg:
        mock_cfg.client = mock_supabase_client
        mock_cfg.is_configured.return_value = True
        service = PresetService()
        service.supabase_config = mock_cfg
        yield service


def _realtime_create() -> PresetCreate:
    return PresetCreate(
        name="Default Realtime",
        description="Gemini native-audio",
        config={"engine_mode": "realtime"},
    )


def _pipeline_create() -> PresetCreate:
    return PresetCreate(
        name="Deepgram+OpenAI+Cartesia",
        description="Direct pipeline",
        config={
            "engine_mode": "pipeline",
            "stt": {"provider": "deepgram"},
            "llm": {"provider": "openai", "model": "gpt-4.1"},
            "tts": {"provider": "cartesia"},
        },
    )


def _row(
    preset_type: PresetType,
    *,
    is_published: bool = True,
    name="P",
    is_default: bool = False
):
    return {
        "id": str(uuid4()),
        "name": name,
        "description": "d",
        "preset_type": preset_type.value,
        "config": (
            {"engine_mode": "realtime"}
            if preset_type is PresetType.REALTIME
            else {
                "engine_mode": "pipeline",
                "stt": {"provider": "deepgram"},
                "llm": {"provider": "openai"},
                "tts": {"provider": "cartesia"},
            }
        ),
        "is_published": is_published,
        "is_default": is_default,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }


class TestPresetService:
    """Test cases for PresetService."""

    async def test_upsert_realtime_derives_preset_type(
        self, preset_service, mock_supabase_client
    ):
        """Upserting a realtime config derives preset_type=realtime."""
        mock_check = MagicMock(data=[])  # not existing
        mock_insert = MagicMock(
            data=[_row(PresetType.REALTIME, name="Default Realtime")]
        )
        mock_supabase_client.table.return_value.execute.side_effect = [
            mock_check,
            mock_insert,
        ]
        result, error = await preset_service.upsert_preset(_realtime_create())
        assert error is None
        assert result is not None
        assert result.preset_type == PresetType.REALTIME
        # The insert payload carried the derived preset_type.
        insert_call = mock_supabase_client.table.return_value.insert.call_args
        assert insert_call.args[0]["preset_type"] == "realtime"

    async def test_upsert_pipeline_derives_preset_type(
        self, preset_service, mock_supabase_client
    ):
        """Upserting a pipeline config derives preset_type=pipeline."""
        mock_check = MagicMock(data=[])
        mock_insert = MagicMock(
            data=[_row(PresetType.PIPELINE, name="Deepgram+OpenAI+Cartesia")]
        )
        mock_supabase_client.table.return_value.execute.side_effect = [
            mock_check,
            mock_insert,
        ]
        result, error = await preset_service.upsert_preset(_pipeline_create())
        assert error is None
        assert result.preset_type == PresetType.PIPELINE
        insert_call = mock_supabase_client.table.return_value.insert.call_args
        assert insert_call.args[0]["preset_type"] == "pipeline"

    async def test_upsert_invalid_config_returns_error(
        self, preset_service, mock_supabase_client
    ):
        """An unparseable config returns (None, error) and never hits the DB.

        PresetCreate validates ``config`` at construction (discriminated union),
        so build with a valid config then overwrite with a force-invalid dict
        (assignment is not re-validated). The service re-validates via
        parse_speech_config and must reject it before touching the DB.
        """
        bad = _realtime_create()
        bad.config = {"engine_mode": "pipeline"}  # missing stt/llm/tts
        result, error = await preset_service.upsert_preset(bad)
        assert result is None
        assert error is not None
        mock_supabase_client.table.assert_not_called()

    async def test_upsert_updates_existing_by_name(
        self, preset_service, mock_supabase_client
    ):
        """An existing row by name is updated (not inserted)."""
        existing_id = uuid4()
        mock_check = MagicMock(data=[{"id": str(existing_id)}])
        mock_update = MagicMock(
            data=[_row(PresetType.REALTIME, name="Default Realtime")]
        )
        mock_supabase_client.table.return_value.execute.side_effect = [
            mock_check,
            mock_update,
        ]
        result, error = await preset_service.upsert_preset(_realtime_create())
        assert error is None
        assert result is not None
        # update by the existing id, not insert
        mock_supabase_client.table.return_value.update.assert_called_once()
        mock_supabase_client.table.return_value.insert.assert_not_called()

    async def test_get_presets_published_only(
        self, preset_service, mock_supabase_client
    ):
        """Default listing filters to is_published=True."""
        mock_resp = MagicMock(data=[_row(PresetType.REALTIME)])
        mock_supabase_client.table.return_value.execute.return_value = mock_resp
        result, error = await preset_service.get_presets()
        assert error is None
        assert len(result) == 1
        # The query chained an is_published=True filter.
        mock_supabase_client.table.return_value.eq.assert_any_call("is_published", True)

    async def test_get_presets_include_drafts(
        self, preset_service, mock_supabase_client
    ):
        """include_drafts=True skips the is_published filter."""
        mock_resp = MagicMock(data=[_row(PresetType.REALTIME, is_published=False)])
        mock_supabase_client.table.return_value.execute.return_value = mock_resp
        result, error = await preset_service.get_presets(include_drafts=True)
        assert error is None
        assert len(result) == 1

    async def test_get_presets_filter_by_type(
        self, preset_service, mock_supabase_client
    ):
        """preset_type filter is applied."""
        mock_resp = MagicMock(data=[_row(PresetType.PIPELINE)])
        mock_supabase_client.table.return_value.execute.return_value = mock_resp
        await preset_service.get_presets(preset_type=PresetType.PIPELINE)
        mock_supabase_client.table.return_value.eq.assert_any_call(
            "preset_type", "pipeline"
        )

    async def test_get_preset_by_id_found(self, preset_service, mock_supabase_client):
        """get_preset_by_id returns the row (draft or published)."""
        mock_resp = MagicMock(data=[_row(PresetType.REALTIME)])
        mock_supabase_client.table.return_value.execute.return_value = mock_resp
        result, error = await preset_service.get_preset_by_id(uuid4())
        assert error is None
        assert result is not None
        assert isinstance(result, Preset)

    async def test_get_preset_by_id_not_found(
        self, preset_service, mock_supabase_client
    ):
        """Missing preset returns (None, None) — worker falls back to default."""
        mock_resp = MagicMock(data=[])
        mock_supabase_client.table.return_value.execute.return_value = mock_resp
        result, error = await preset_service.get_preset_by_id(uuid4())
        assert error is None
        assert result is None

    async def test_publish_preset_flip(self, preset_service, mock_supabase_client):
        """publish_preset flips is_published and returns the updated row."""
        mock_resp = MagicMock(data=[_row(PresetType.REALTIME, is_published=True)])
        mock_supabase_client.table.return_value.execute.return_value = mock_resp
        result, error = await preset_service.publish_preset(uuid4(), True)
        assert error is None
        assert result is not None
        update_call = mock_supabase_client.table.return_value.update.call_args
        assert update_call.args[0] == {"is_published": True}

    async def test_publish_preset_not_found(self, preset_service, mock_supabase_client):
        """Publishing a missing row returns (None, 'not found')."""
        mock_resp = MagicMock(data=[])
        mock_supabase_client.table.return_value.execute.return_value = mock_resp
        result, error = await preset_service.publish_preset(uuid4(), True)
        assert result is None
        assert error is not None

    async def test_get_preset_usage(self, preset_service, mock_supabase_client):
        """Usage lists agents referencing the preset via the voice_agents join."""
        agent_id = uuid4()
        org_id = uuid4()
        mock_resp = MagicMock(
            data=[
                {"id": str(agent_id), "name": "Agent A", "organization_id": str(org_id)}
            ]
        )
        mock_supabase_client.table.return_value.execute.return_value = mock_resp
        usage, error = await preset_service.get_preset_usage(uuid4())
        assert error is None
        assert len(usage) == 1
        assert usage[0]["name"] == "Agent A"

    async def test_delete_preset_in_use_without_force(
        self, preset_service, mock_supabase_client
    ):
        """A preset referenced by agents cannot be deleted without force."""
        exists = MagicMock(data=[{"id": str(uuid4())}])
        usage = MagicMock(
            data=[{"id": str(uuid4()), "name": "X", "organization_id": str(uuid4())}]
        )
        mock_supabase_client.table.return_value.execute.side_effect = [exists, usage]
        result, error = await preset_service.delete_preset(uuid4())
        assert result is None
        assert error == "in_use"

    async def test_delete_preset_force_succeeds(
        self, preset_service, mock_supabase_client
    ):
        """With force, an in-use preset is deleted (FK SET NULL detaches agents)."""
        exists = MagicMock(data=[{"id": str(uuid4())}])
        usage = MagicMock(
            data=[{"id": str(uuid4()), "name": "X", "organization_id": str(uuid4())}]
        )
        deleted = MagicMock(data=[{"id": str(uuid4())}])
        mock_supabase_client.table.return_value.execute.side_effect = [
            exists,
            usage,
            deleted,
        ]
        result, error = await preset_service.delete_preset(uuid4(), force=True)
        assert error is None
        assert result is True

    async def test_delete_preset_not_in_use_succeeds(
        self, preset_service, mock_supabase_client
    ):
        """A preset with no usage deletes without force."""
        exists = MagicMock(data=[{"id": str(uuid4())}])
        usage = MagicMock(data=[])
        deleted = MagicMock(data=[{"id": str(uuid4())}])
        mock_supabase_client.table.return_value.execute.side_effect = [
            exists,
            usage,
            deleted,
        ]
        result, error = await preset_service.delete_preset(uuid4())
        assert error is None
        assert result is True

    async def test_delete_preset_not_found(self, preset_service, mock_supabase_client):
        """Deleting a missing preset returns (None, 'not found')."""
        exists = MagicMock(data=[])
        mock_supabase_client.table.return_value.execute.return_value = exists
        result, error = await preset_service.delete_preset(uuid4())
        assert result is None
        assert error is not None

    async def test_update_preset_rederives_type_on_config_change(
        self, preset_service, mock_supabase_client
    ):
        """Supplying a new config re-derives preset_type from its engine_mode."""
        mock_resp = MagicMock(data=[_row(PresetType.PIPELINE, name="Renamed")])
        mock_supabase_client.table.return_value.execute.return_value = mock_resp
        update = PresetUpdate(
            name="Renamed",
            config={
                "engine_mode": "pipeline",
                "stt": {"provider": "deepgram"},
                "llm": {"provider": "openai"},
                "tts": {"provider": "cartesia"},
            },
        )
        result, error = await preset_service.update_preset(uuid4(), update)
        assert error is None
        assert result is not None
        update_call = mock_supabase_client.table.return_value.update.call_args
        assert update_call.args[0]["preset_type"] == "pipeline"

    async def test_update_preset_partial_without_config(
        self, preset_service, mock_supabase_client
    ):
        """A partial update without config does not touch preset_type."""
        mock_resp = MagicMock(data=[_row(PresetType.REALTIME, name="Renamed")])
        mock_supabase_client.table.return_value.execute.return_value = mock_resp
        update = PresetUpdate(name="Renamed")
        result, error = await preset_service.update_preset(uuid4(), update)
        assert error is None
        assert result is not None
        update_call = mock_supabase_client.table.return_value.update.call_args
        assert "preset_type" not in update_call.args[0]


class TestPresetServiceErrorBranches:
    """Cover the failure / exception / not-found branches for 90%+ coverage."""

    async def test_upsert_empty_response_returns_failed(
        self, preset_service, mock_supabase_client
    ):
        """An insert that returns no rows surfaces 'Failed to upsert preset'."""
        mock_check = MagicMock(data=[])  # not existing → insert path
        mock_insert = MagicMock(data=[])  # insert returns nothing
        mock_supabase_client.table.return_value.execute.side_effect = [
            mock_check,
            mock_insert,
        ]
        result, error = await preset_service.upsert_preset(_realtime_create())
        assert result is None
        assert error == "Failed to upsert preset"

    async def test_upsert_supabase_exception_returns_error(
        self, preset_service, mock_supabase_client
    ):
        """A Supabase raise is caught and returned as (None, error)."""
        mock_supabase_client.table.return_value.execute.side_effect = RuntimeError(
            "connection lost"
        )
        result, error = await preset_service.upsert_preset(_realtime_create())
        assert result is None
        assert "connection lost" in error

    async def test_update_preset_invalid_config_returns_error(
        self, preset_service, mock_supabase_client
    ):
        """A bad config on update is rejected before touching the DB.

        PresetUpdate validates ``config`` at construction (discriminated union),
        so build with a valid config then overwrite with a force-invalid dict
        (assignment is not re-validated). The service re-validates via
        parse_speech_config and must reject it before touching the DB.
        """
        bad = PresetUpdate(config={"engine_mode": "realtime"})
        bad.config = {"engine_mode": "pipeline"}  # missing stt/llm/tts
        result, error = await preset_service.update_preset(uuid4(), bad)
        assert result is None
        assert error is not None
        mock_supabase_client.table.assert_not_called()

    async def test_update_preset_not_found(self, preset_service, mock_supabase_client):
        """An update that matches no row returns 'Preset not found'."""
        mock_supabase_client.table.return_value.execute.return_value = MagicMock(
            data=[]
        )
        result, error = await preset_service.update_preset(
            uuid4(), PresetUpdate(name="X")
        )
        assert result is None
        assert error == "Preset not found"

    async def test_update_preset_supabase_exception(
        self, preset_service, mock_supabase_client
    ):
        mock_supabase_client.table.return_value.execute.side_effect = RuntimeError(
            "boom"
        )
        result, error = await preset_service.update_preset(
            uuid4(), PresetUpdate(name="X")
        )
        assert result is None
        assert "boom" in error

    async def test_get_presets_supabase_exception(
        self, preset_service, mock_supabase_client
    ):
        mock_supabase_client.table.return_value.execute.side_effect = RuntimeError(
            "boom"
        )
        result, error = await preset_service.get_presets()
        assert result == []
        assert "boom" in error

    async def test_get_preset_by_id_supabase_exception(
        self, preset_service, mock_supabase_client
    ):
        mock_supabase_client.table.return_value.execute.side_effect = RuntimeError(
            "boom"
        )
        result, error = await preset_service.get_preset_by_id(uuid4())
        assert result is None
        assert "boom" in error

    async def test_publish_preset_supabase_exception(
        self, preset_service, mock_supabase_client
    ):
        mock_supabase_client.table.return_value.execute.side_effect = RuntimeError(
            "boom"
        )
        result, error = await preset_service.publish_preset(uuid4(), True)
        assert result is None
        assert "boom" in error

    async def test_get_preset_usage_supabase_exception(
        self, preset_service, mock_supabase_client
    ):
        mock_supabase_client.table.return_value.execute.side_effect = RuntimeError(
            "boom"
        )
        result, error = await preset_service.get_preset_usage(uuid4())
        assert result is None
        assert "boom" in error

    async def test_delete_preset_usage_error_propagates(
        self, preset_service, mock_supabase_client
    ):
        """If the usage lookup errors, delete returns that error (no delete)."""
        exists = MagicMock(data=[{"id": str(uuid4())}])
        # Second execute (the usage query) raises.
        mock_supabase_client.table.return_value.execute.side_effect = [
            exists,
            RuntimeError("usage query failed"),
        ]
        result, error = await preset_service.delete_preset(uuid4())
        assert result is None
        assert "usage query failed" in error

    async def test_delete_preset_supabase_exception(
        self, preset_service, mock_supabase_client
    ):
        """The existence check raising is caught."""
        mock_supabase_client.table.return_value.execute.side_effect = RuntimeError(
            "boom"
        )
        result, error = await preset_service.delete_preset(uuid4())
        assert result is None
        assert "boom" in error

    async def test_upsert_with_dict_config_normalizes(
        self, preset_service, mock_supabase_client
    ):
        """A raw-dict config (caller bypassed Pydantic) is normalized and stored."""
        mock_check = MagicMock(data=[])
        mock_insert = MagicMock(
            data=[_row(PresetType.REALTIME, name="Default Realtime")]
        )
        mock_supabase_client.table.return_value.execute.side_effect = [
            mock_check,
            mock_insert,
        ]
        data = _realtime_create()
        data.config = {"engine_mode": "realtime"}  # raw dict, not a model
        result, error = await preset_service.upsert_preset(data)
        assert error is None
        assert result is not None


class TestPresetServiceDefault:
    """System-default preset: get/update + guards on CRUD methods."""

    async def test_get_default_preset_found(self, preset_service, mock_supabase_client):
        """get_default_preset returns the single is_default=True row."""
        mock_supabase_client.table.return_value.execute.return_value = MagicMock(
            data=[_row(PresetType.REALTIME, is_default=True, name="System Default")]
        )
        result, error = await preset_service.get_default_preset()
        assert error is None
        assert result is not None
        assert result.is_default is True
        # Query filters on is_default=True.
        mock_supabase_client.table.return_value.eq.assert_any_call("is_default", True)

    async def test_get_default_preset_not_found(
        self, preset_service, mock_supabase_client
    ):
        """No default row -> (None, None) (worker falls back to hardcoded)."""
        mock_supabase_client.table.return_value.execute.return_value = MagicMock(
            data=[]
        )
        result, error = await preset_service.get_default_preset()
        assert error is None
        assert result is None

    async def test_get_default_preset_supabase_exception(
        self, preset_service, mock_supabase_client
    ):
        mock_supabase_client.table.return_value.execute.side_effect = RuntimeError(
            "boom"
        )
        result, error = await preset_service.get_default_preset()
        assert result is None
        assert "boom" in error

    async def test_update_default_preset_updates_config(
        self, preset_service, mock_supabase_client
    ):
        """update_default_preset writes config+preset_type on the default row only."""
        mock_supabase_client.table.return_value.execute.return_value = MagicMock(
            data=[_row(PresetType.PIPELINE, is_default=True, name="System Default")]
        )
        new_config = {
            "engine_mode": "pipeline",
            "stt": {"provider": "deepgram"},
            "llm": {"provider": "openai"},
            "tts": {"provider": "cartesia"},
        }
        result, error = await preset_service.update_default_preset(new_config)
        assert error is None
        assert result is not None
        assert result.is_default is True
        # The update payload is config + derived preset_type, scoped to is_default=True.
        update_call = mock_supabase_client.table.return_value.update.call_args
        assert update_call.args[0]["config"] == new_config
        assert update_call.args[0]["preset_type"] == "pipeline"
        mock_supabase_client.table.return_value.eq.assert_any_call("is_default", True)

    async def test_update_default_preset_invalid_config(
        self, preset_service, mock_supabase_client
    ):
        """A bad config is rejected before touching the DB."""
        result, error = await preset_service.update_default_preset(
            {"engine_mode": "pipeline"}  # missing stt/llm/tts
        )
        assert result is None
        assert error is not None
        mock_supabase_client.table.assert_not_called()

    async def test_update_default_preset_not_found(
        self, preset_service, mock_supabase_client
    ):
        """No is_default row -> (None, 'Default not found')."""
        mock_supabase_client.table.return_value.execute.return_value = MagicMock(
            data=[]
        )
        result, error = await preset_service.update_default_preset(
            {"engine_mode": "realtime"}
        )
        assert result is None
        assert error == "Default not found"

    async def test_update_default_preset_supabase_exception(
        self, preset_service, mock_supabase_client
    ):
        mock_supabase_client.table.return_value.execute.side_effect = RuntimeError(
            "boom"
        )
        result, error = await preset_service.update_default_preset(
            {"engine_mode": "realtime"}
        )
        assert result is None
        assert "boom" in error

    async def test_upsert_rejects_reserved_default_name(
        self, preset_service, mock_supabase_client
    ):
        """Authoring a preset named 'System Default' is rejected (reserved)."""
        from shared.voice_agents.preset_models import RESERVED_DEFAULT_NAME

        data = PresetCreate(
            name=RESERVED_DEFAULT_NAME, config={"engine_mode": "realtime"}
        )
        result, error = await preset_service.upsert_preset(data)
        assert result is None
        assert error is not None
        assert "reserved" in error.lower()
        mock_supabase_client.table.assert_not_called()

    async def test_update_preset_rejects_default_row(
        self, preset_service, mock_supabase_client
    ):
        """The generic update path refuses the system-default row."""
        mock_supabase_client.table.return_value.execute.return_value = MagicMock(
            data=[{"id": str(uuid4()), "is_default": True}]
        )
        result, error = await preset_service.update_preset(
            uuid4(), PresetUpdate(name="X")
        )
        assert result is None
        assert error is not None
        # The generic update was NOT issued (only the guard fetch ran).
        mock_supabase_client.table.return_value.update.assert_not_called()

    async def test_publish_preset_rejects_default_row(
        self, preset_service, mock_supabase_client
    ):
        """Publishing the system-default row is rejected (it is not publishable)."""
        mock_supabase_client.table.return_value.execute.return_value = MagicMock(
            data=[{"id": str(uuid4()), "is_default": True}]
        )
        result, error = await preset_service.publish_preset(uuid4(), True)
        assert result is None
        assert error is not None
        mock_supabase_client.table.return_value.update.assert_not_called()

    async def test_delete_preset_rejects_default_row(
        self, preset_service, mock_supabase_client
    ):
        """Deleting the system-default row is rejected."""
        mock_supabase_client.table.return_value.execute.return_value = MagicMock(
            data=[{"id": str(uuid4()), "is_default": True}]
        )
        result, error = await preset_service.delete_preset(uuid4())
        assert result is None
        assert error is not None
        # No delete issued, and no usage/delete beyond the existence fetch.
        mock_supabase_client.table.return_value.delete.assert_not_called()


class TestBuildPresetCatalog:
    """White-label catalog builder (org-facing readiness, no config leak)."""

    def test_build_catalog_omits_config_and_includes_readiness(self):
        from types import SimpleNamespace

        from shared.voice_agents.preset_service import PresetService

        published = Preset(**_row(PresetType.PIPELINE, name="Professional Voice"))
        default = Preset(
            **_row(PresetType.REALTIME, name="System Default", is_default=True)
        )
        org = SimpleNamespace(provider_credentials="enc")

        with patch(
            "shared.voice_agents.key_resolver.is_preset_ready",
            side_effect=lambda cfg, o, use_platform_credits=False: (
                cfg.engine_mode == "realtime"
            ),
        ):
            catalog = PresetService.build_preset_catalog(
                [published],
                default,
                org,
                credentials_self_service=True,
            )

        assert catalog.default_is_ready is True
        assert len(catalog.presets) == 1
        assert catalog.presets[0].name == "Professional Voice"
        assert catalog.presets[0].is_ready is False
        assert catalog.credentials_self_service is True
        dumped = catalog.presets[0].model_dump()
        assert "config" not in dumped
        assert "preset_type" not in dumped
