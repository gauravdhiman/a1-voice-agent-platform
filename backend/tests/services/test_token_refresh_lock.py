"""
TDD tests for the Postgres-backed token-refresh distributed lock.

These define the contract BEFORE implementation (red), then implementation makes
them green:

- ``ToolService.claim_refresh_lock``: atomic per-agent_tool lease via the
  ``claim_token_refresh`` Postgres function. Returns a claim id when acquired,
  ``None`` when another instance holds it (or on error — fail-closed).
- ``ToolService.release_refresh_lock``: release only if the row still belongs to
  this caller (claim id match).
- ``TokenRefreshService._check_and_refresh_token``: acquires the lease before the
  external OAuth call, skips when locked, and always releases in a ``finally``
  (success or failure).
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from src.services.token_refresh_service import TokenRefreshService

from shared.voice_agents.tool_models import AgentTool, PlatformTool
from shared.voice_agents.tool_service import ToolService

# ─── fixtures ──────────────────────────────────────────────────────────────


def _tool_service_with_rpc(rpc_data):
    """Build a ToolService whose supabase.rpc(...).execute().data == rpc_data."""
    ts = ToolService()
    mock_client = MagicMock()
    mock_client.rpc.return_value.execute.return_value.data = rpc_data
    ts.supabase_config = MagicMock()
    ts.supabase_config.client = mock_client
    return ts, mock_client


def _agent_tool():
    platform_tool = MagicMock(spec=PlatformTool)
    platform_tool.name = "Test Tool"
    platform_tool.auth_config = {
        "client_id": "cid",
        "client_secret": "csec",
        "token_url": "https://oauth.example.com/token",
    }
    now = datetime.now(timezone.utc)
    at = MagicMock(spec=AgentTool)
    at.id = uuid4()
    at.oauth_credential_version = 4
    at.oauth_refresh_status = "ready"
    at.oauth_refresh_error_code = None
    at.oauth_credentials_unreadable = False
    at.tool = platform_tool
    at.sensitive_config = {
        "access_token": "a",
        "refresh_token": "r",
        "expires_at": (now + timedelta(minutes=1)).timestamp(),
    }
    return at


# ─── ToolService.claim_refresh_lock ────────────────────────────────────────


@pytest.mark.asyncio
class TestClaimRefreshLock:
    async def test_claim_returns_claim_id_when_granted(self):
        ts, client = _tool_service_with_rpc({"claimed": True, "claim": "x"})
        tool_id = uuid4()
        result = await ts.claim_refresh_lock(tool_id)
        assert result is not None
        # The claim id sent to the RPC equals the one returned.
        call = client.rpc.call_args
        assert call[0][0] == "claim_token_refresh"
        params = call[0][1] if len(call[0]) > 1 else call[1]
        assert params["p_tool_id"] == str(tool_id)
        assert params["p_claim"] == result
        assert params["p_lease_seconds"] >= 1

    async def test_claim_returns_none_when_held_by_another(self):
        ts, _ = _tool_service_with_rpc({"claimed": False, "claim": ""})
        assert await ts.claim_refresh_lock(uuid4()) is None

    async def test_claim_fail_closed_on_db_error(self):
        ts, client = _tool_service_with_rpc({"claimed": True, "claim": "x"})
        client.rpc.side_effect = RuntimeError("db down")
        # Fail-closed: do not refresh when the lock cannot be acquired/verified.
        assert await ts.claim_refresh_lock(uuid4()) is None


# ─── ToolService.release_refresh_lock ───────────────────────────────────────


@pytest.mark.asyncio
class TestReleaseRefreshLock:
    async def test_release_true_when_owned(self):
        ts, _ = _tool_service_with_rpc({"released": True})
        assert await ts.release_refresh_lock(uuid4(), "claim-1") is True

    async def test_release_false_when_not_owned(self):
        ts, _ = _tool_service_with_rpc({"released": False})
        assert await ts.release_refresh_lock(uuid4(), "claim-1") is False


@pytest.mark.asyncio
class TestRefreshDatabaseFence:
    async def test_begin_refresh_passes_claim_and_credential_generation(self):
        ts, client = _tool_service_with_rpc({"begun": True})
        tool_id = uuid4()

        result = await ts.begin_oauth_refresh(tool_id, "claim-7", 11, 120)

        assert result is True
        name, params = client.rpc.call_args.args
        assert name == "begin_token_refresh"
        assert params == {
            "p_tool_id": str(tool_id),
            "p_claim": "claim-7",
            "p_expected_version": 11,
            "p_lease_seconds": 120,
        }

    async def test_completion_encrypts_and_fences_rotated_credentials(self):
        ts, client = _tool_service_with_rpc({"updated": True})
        tool_id = uuid4()
        refreshed_at = datetime.now(timezone.utc)
        credentials = {"access_token": "never-send-plaintext"}

        with patch(
            "shared.voice_agents.tool_service.encrypt_data", return_value="encrypted"
        ) as encrypt:
            result = await ts.persist_refreshed_oauth_credentials(
                tool_id, "claim-9", 4, credentials, refreshed_at, 120
            )

        assert result is True
        encrypt.assert_called_once_with(credentials)
        name, params = client.rpc.call_args.args
        assert name == "complete_token_refresh"
        assert params["p_claim"] == "claim-9"
        assert params["p_expected_version"] == 4
        assert params["p_encrypted_config"] == "encrypted"
        assert "never-send-plaintext" not in repr(params)

    async def test_completion_returns_false_when_database_fence_rejects_write(self):
        ts, _ = _tool_service_with_rpc({"updated": False})

        result = await ts.persist_refreshed_oauth_credentials(
            uuid4(),
            "expired-claim",
            7,
            {"access_token": "token"},
            datetime.now(timezone.utc),
            120,
        )

        assert result is False

    async def test_readable_credential_recovery_is_version_fenced(self):
        ts, client = _tool_service_with_rpc({"updated": True})
        tool_id = uuid4()

        result = await ts.recover_oauth_credentials_unreadable(tool_id, 13)

        assert result is True
        name, params = client.rpc.call_args.args
        assert name == "recover_oauth_credentials_unreadable"
        assert params == {"p_tool_id": str(tool_id), "p_expected_version": 13}

    async def test_release_false_on_error(self):
        ts, client = _tool_service_with_rpc({"released": True})
        client.rpc.side_effect = RuntimeError("db down")
        assert await ts.release_refresh_lock(uuid4(), "claim-1") is False


# ─── TokenRefreshService lock integration ──────────────────────────────────


@pytest.mark.asyncio
class TestRefreshLockIntegration:
    async def test_skips_refresh_when_lock_not_acquired(self):
        tool_service = MagicMock()
        tool_service.claim_refresh_lock = AsyncMock(return_value=None)
        tool_service.release_refresh_lock = AsyncMock(return_value=False)
        svc = TokenRefreshService(tool_service)

        at = _agent_tool()
        with patch.object(
            svc, "_refresh_oauth_token", new_callable=AsyncMock
        ) as m_oauth:
            result = await svc._check_and_refresh_token(at)
            assert result is False
            # Must NOT hit the OAuth provider when locked out.
            m_oauth.assert_not_awaited()
            tool_service.release_refresh_lock.assert_not_awaited()

    async def test_refreshes_then_releases_on_success(self):
        tool_service = MagicMock()
        tool_service.claim_refresh_lock = AsyncMock(return_value="claim-1")
        tool_service.release_refresh_lock = AsyncMock(return_value=True)
        tool_service.get_agent_tool_with_sensitive_config = AsyncMock(
            return_value=(None, None)
        )
        svc = TokenRefreshService(tool_service)

        at = _agent_tool()
        tool_service.get_agent_tool_with_sensitive_config.return_value = (at, None)
        tool_service.begin_oauth_refresh = AsyncMock(return_value=True)
        tool_service.persist_refreshed_oauth_credentials = AsyncMock(return_value=True)
        tool_service.set_oauth_refresh_status = AsyncMock(return_value=True)
        with patch("src.services.token_refresh_service.get_oauth_manager") as gm:
            mgr = MagicMock()
            mgr.extract_oauth_config.return_value = (
                "google",
                "https://oauth.example.com/token",
            )
            gm.return_value = mgr
            with patch.object(
                svc, "_refresh_oauth_token", new_callable=AsyncMock
            ) as m_oauth:
                m_oauth.return_value = {"access_token": "new", "expires_in": 3600}
                result = await svc._check_and_refresh_token(at)
                assert result is True
                m_oauth.assert_awaited_once()
                tool_service.claim_refresh_lock.assert_awaited_once()
                # Lock released exactly once, with the same claim id.
                tool_service.release_refresh_lock.assert_awaited_once()
                released_args = tool_service.release_refresh_lock.await_args
                assert released_args[0][1] == "claim-1"

    async def test_releases_even_when_refresh_fails(self):
        tool_service = MagicMock()
        tool_service.claim_refresh_lock = AsyncMock(return_value="claim-1")
        tool_service.release_refresh_lock = AsyncMock(return_value=True)
        tool_service.get_agent_tool_with_sensitive_config = AsyncMock(
            return_value=(None, None)
        )
        tool_service.begin_oauth_refresh = AsyncMock(return_value=True)
        tool_service.set_oauth_refresh_status = AsyncMock(return_value=True)
        svc = TokenRefreshService(tool_service)

        at = _agent_tool()
        tool_service.get_agent_tool_with_sensitive_config.return_value = (at, None)
        with patch("src.services.token_refresh_service.get_oauth_manager") as gm:
            mgr = MagicMock()
            mgr.extract_oauth_config.return_value = (
                "google",
                "https://oauth.example.com/token",
            )
            gm.return_value = mgr
            with patch.object(
                svc, "_refresh_oauth_token", new_callable=AsyncMock
            ) as m_oauth:
                m_oauth.return_value = None  # OAuth refresh fails
                result = await svc._check_and_refresh_token(at)
                assert result is False
                tool_service.release_refresh_lock.assert_awaited_once()

    async def test_reload_after_lease_observes_newer_credentials(self):
        """Discard a scan snapshot if credentials changed before lease acquisition."""
        tool_service = MagicMock()
        tool_service.claim_refresh_lock = AsyncMock(return_value="claim-1")
        tool_service.release_refresh_lock = AsyncMock(return_value=True)
        svc = TokenRefreshService(tool_service)
        scanned = _agent_tool()
        fresh = _agent_tool()
        fresh.sensitive_config["expires_at"] = (
            datetime.now(timezone.utc) + timedelta(hours=2)
        ).timestamp()
        tool_service.get_agent_tool_with_sensitive_config = AsyncMock(
            return_value=(fresh, None)
        )
        tool_service.begin_oauth_refresh = AsyncMock(return_value=True)

        result = await svc._check_and_refresh_token(scanned)

        assert result is False
        tool_service.begin_oauth_refresh.assert_not_awaited()
        tool_service.release_refresh_lock.assert_awaited_once_with(
            scanned.id, "claim-1"
        )

    async def test_interrupted_refresh_is_marked_unknown_without_replaying_token(self):
        """An expired lease plus a refreshing marker requires reauthorization."""
        tool_service = MagicMock()
        tool_service.claim_refresh_lock = AsyncMock(return_value="claim-2")
        tool_service.release_refresh_lock = AsyncMock(return_value=True)
        svc = TokenRefreshService(tool_service)
        scanned = _agent_tool()
        fresh = _agent_tool()
        fresh.id = scanned.id
        fresh.oauth_refresh_status = "refreshing"
        tool_service.get_agent_tool_with_sensitive_config = AsyncMock(
            return_value=(fresh, None)
        )
        tool_service.set_oauth_refresh_status = AsyncMock(return_value=True)

        with patch.object(
            svc, "_refresh_oauth_token", new_callable=AsyncMock
        ) as refresh:
            result = await svc._check_and_refresh_token(scanned)

        assert result is False
        refresh.assert_not_awaited()
        tool_service.set_oauth_refresh_status.assert_awaited_once()
        assert (
            tool_service.set_oauth_refresh_status.await_args.args[3]
            == "outcome_unknown"
        )
        assert scanned.oauth_refresh_status == "outcome_unknown"

    async def test_new_authorization_wins_interrupted_refresh_race(self):
        """A callback racing lease takeover suppresses stale unknown-state alerts."""
        tool_service = MagicMock()
        scanned = _agent_tool()
        refreshing = _agent_tool()
        refreshing.id = scanned.id
        refreshing.oauth_refresh_status = "refreshing"
        latest = _agent_tool()
        latest.id = scanned.id
        latest.oauth_credential_version += 1
        latest.sensitive_config["expires_at"] = (
            datetime.now(timezone.utc) + timedelta(minutes=60)
        ).timestamp()

        tool_service.claim_refresh_lock = AsyncMock(return_value="claim-current")
        tool_service.release_refresh_lock = AsyncMock(return_value=True)
        tool_service.get_agent_tool_with_sensitive_config = AsyncMock(
            side_effect=[(refreshing, None), (latest, None)]
        )
        tool_service.set_oauth_refresh_status = AsyncMock(return_value=False)
        svc = TokenRefreshService(tool_service)

        with patch.object(
            svc, "_refresh_oauth_token", new_callable=AsyncMock
        ) as refresh:
            result = await svc._check_and_refresh_token(scanned)

        assert result is False
        assert scanned.oauth_credential_version == latest.oauth_credential_version
        assert scanned.oauth_refresh_status == "ready"
        assert (
            tool_service.set_oauth_refresh_status.await_args.args[1] == "claim-current"
        )
        tool_service.release_refresh_lock.assert_awaited_once_with(
            scanned.id, "claim-current"
        )
        refresh.assert_not_awaited()

    async def test_unreadable_credentials_are_marked_without_provider_call(self):
        """Lost decryption access is persisted for immediate admin notification."""
        tool_service = MagicMock()
        tool_service.mark_oauth_credentials_unreadable = AsyncMock(return_value=True)
        svc = TokenRefreshService(tool_service)
        at = _agent_tool()
        at.oauth_credentials_unreadable = True

        with patch.object(
            svc, "_refresh_oauth_token", new_callable=AsyncMock
        ) as refresh:
            result = await svc._check_and_refresh_token(at)

        assert result is False
        refresh.assert_not_awaited()
        tool_service.mark_oauth_credentials_unreadable.assert_awaited_once_with(
            at.id, at.oauth_credential_version
        )
        assert at.oauth_refresh_status == "credentials_unreadable"

    async def test_readable_credentials_clear_unreadable_state(self):
        """Restoring an encryption key lets scheduled refresh recover again."""
        tool_service = MagicMock()
        tool_service.recover_oauth_credentials_unreadable = AsyncMock(return_value=True)
        svc = TokenRefreshService(tool_service)
        at = _agent_tool()
        at.oauth_refresh_status = "credentials_unreadable"
        at.oauth_credentials_unreadable = False
        at.sensitive_config["expires_at"] = (
            datetime.now(timezone.utc) + timedelta(minutes=60)
        ).timestamp()

        result = await svc._check_and_refresh_token(at)

        assert result is False
        assert at.oauth_refresh_status == "ready"
        assert at.oauth_refresh_error_code is None
        tool_service.recover_oauth_credentials_unreadable.assert_awaited_once_with(
            at.id, at.oauth_credential_version
        )
        tool_service.claim_refresh_lock.assert_not_called()
