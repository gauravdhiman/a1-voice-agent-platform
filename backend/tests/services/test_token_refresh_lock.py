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
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4

from shared.voice_agents.tool_service import ToolService
from shared.voice_agents.tool_models import AgentTool, PlatformTool
from src.services.token_refresh_service import TokenRefreshService


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
        with patch.object(svc, "_refresh_oauth_token", new_callable=AsyncMock) as m_oauth:
            result = await svc._check_and_refresh_token(at)
            assert result is False
            # Must NOT hit the OAuth provider when locked out.
            m_oauth.assert_not_awaited()
            tool_service.release_refresh_lock.assert_not_awaited()

    async def test_refreshes_then_releases_on_success(self):
        tool_service = MagicMock()
        tool_service.claim_refresh_lock = AsyncMock(return_value="claim-1")
        tool_service.release_refresh_lock = AsyncMock(return_value=True)
        tool_service.update_agent_tool = AsyncMock(return_value=(MagicMock(), None))
        svc = TokenRefreshService(tool_service)

        at = _agent_tool()
        with patch("src.services.token_refresh_service.get_oauth_manager") as gm:
            mgr = MagicMock()
            mgr.extract_oauth_config.return_value = ("google", "https://oauth.example.com/token")
            gm.return_value = mgr
            with patch.object(svc, "_refresh_oauth_token", new_callable=AsyncMock) as m_oauth:
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
        svc = TokenRefreshService(tool_service)

        at = _agent_tool()
        with patch("src.services.token_refresh_service.get_oauth_manager") as gm:
            mgr = MagicMock()
            mgr.extract_oauth_config.return_value = ("google", "https://oauth.example.com/token")
            gm.return_value = mgr
            with patch.object(svc, "_refresh_oauth_token", new_callable=AsyncMock) as m_oauth:
                m_oauth.return_value = None  # OAuth refresh fails
                result = await svc._check_and_refresh_token(at)
                assert result is False
                tool_service.release_refresh_lock.assert_awaited_once()
