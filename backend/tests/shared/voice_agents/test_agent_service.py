"""Tests for the shared ``VoiceAgentService`` update path.

Regression: ``update_agent`` built the Supabase update payload with
``model_dump(exclude_unset=True)``, which left ``preset_id`` as a ``UUID``
object. Postgrest JSON-serializes the payload with the stdlib ``json`` module,
so saving an agent with a ``preset_id`` failed with ``Object of type UUID is
not JSON serializable`` (HTTP 400). The payload handed to ``.update()`` must be
JSON-serializable.

The route tests mock ``update_agent`` entirely, so they never exercise this
path — these service-level tests do.
"""

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from shared.voice_agents.models import VoiceAgentUpdate
from shared.voice_agents.service import VoiceAgentService


@pytest.fixture
def agent_service(mock_supabase_client):
    """Create a VoiceAgentService wired to the mocked Supabase client."""
    with patch("shared.voice_agents.service.supabase_config") as mock_cfg:
        mock_cfg.client = mock_supabase_client
        return VoiceAgentService()


def _agent_row(agent_id, org_id, preset_id=None):
    """Build a raw voice_agents row dict as Supabase would return it."""
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": str(agent_id),
        "organization_id": str(org_id),
        "name": "Test Agent",
        "phone_number": None,
        "is_active": True,
        "persona": None,
        "tone": None,
        "mission": None,
        "use_platform_credits": False,
        "custom_instructions": None,
        "instructions_markdown": None,
        "preset_id": str(preset_id) if preset_id else None,
        "created_at": now,
        "updated_at": now,
    }


class TestUpdateAgentSerialization:
    """update_agent must send a JSON-serializable payload to Supabase."""

    @pytest.mark.asyncio
    async def test_preset_id_serialized_as_string_in_update_payload(
        self, agent_service, mock_supabase_client
    ):
        """A preset_id UUID must be serialized to str in the update payload."""
        agent_id = uuid4()
        org_id = uuid4()
        preset_id = uuid4()

        table_mock = mock_supabase_client.table.return_value
        table_mock.execute.return_value = MagicMock(
            data=[_agent_row(agent_id, org_id, preset_id)]
        )

        result, error = await agent_service.update_agent(
            agent_id, VoiceAgentUpdate(preset_id=preset_id)
        )

        assert error is None
        assert result is not None
        # The dict handed to .update() must carry preset_id as a str, not a UUID.
        update_data = table_mock.update.call_args.args[0]
        assert isinstance(update_data["preset_id"], str)
        assert update_data["preset_id"] == str(preset_id)
        # The whole payload must round-trip through stdlib json — this is what
        # Postgrest does, and what failed with "Object of type UUID is not JSON
        # serializable" before the fix.
        json.dumps(update_data)

    @pytest.mark.asyncio
    async def test_clearing_preset_id_to_none_is_json_serializable(
        self, agent_service, mock_supabase_client
    ):
        """Explicitly clearing preset_id to None stays JSON-serializable."""
        agent_id = uuid4()
        org_id = uuid4()

        table_mock = mock_supabase_client.table.return_value
        table_mock.execute.return_value = MagicMock(
            data=[_agent_row(agent_id, org_id, preset_id=None)]
        )

        result, error = await agent_service.update_agent(
            agent_id, VoiceAgentUpdate(preset_id=None)
        )

        assert error is None
        assert result is not None
        update_data = table_mock.update.call_args.args[0]
        assert update_data["preset_id"] is None
        json.dumps(update_data)


class TestUpdateAgentPublicPagePublish:
    """Deactivating an agent must also unpublish it from the public page."""

    @pytest.mark.asyncio
    async def test_deactivating_agent_clears_public_page_publish(
        self, agent_service, mock_supabase_client
    ):
        """Setting is_active=False must also set is_published_on_public_page=False.

        Prevents the loophole where a user activates + publishes, then deactivates
        while leaving the agent published on the org public page.
        """
        agent_id = uuid4()
        org_id = uuid4()
        row = _agent_row(agent_id, org_id)
        row["is_active"] = False
        row["is_published_on_public_page"] = False

        table_mock = mock_supabase_client.table.return_value
        table_mock.execute.return_value = MagicMock(data=[row])

        result, error = await agent_service.update_agent(
            agent_id, VoiceAgentUpdate(is_active=False)
        )

        assert error is None
        assert result is not None
        update_data = table_mock.update.call_args.args[0]
        assert update_data["is_active"] is False
        assert update_data["is_published_on_public_page"] is False

    @pytest.mark.asyncio
    async def test_activating_agent_does_not_force_public_page_publish(
        self, agent_service, mock_supabase_client
    ):
        """Setting is_active=True alone must not touch public-page publish."""
        agent_id = uuid4()
        org_id = uuid4()

        table_mock = mock_supabase_client.table.return_value
        table_mock.execute.return_value = MagicMock(
            data=[_agent_row(agent_id, org_id)]
        )

        result, error = await agent_service.update_agent(
            agent_id, VoiceAgentUpdate(is_active=True)
        )

        assert error is None
        assert result is not None
        update_data = table_mock.update.call_args.args[0]
        assert update_data["is_active"] is True
        assert "is_published_on_public_page" not in update_data
