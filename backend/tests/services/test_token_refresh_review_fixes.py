"""
TDD tests for the issues raised in docs/06_review/token-refresh-lock-review.md.

Red first (these assert behavior that does not exist yet), then implementation
makes them green:

- #1 DB-update failure after a successful (rotated) OAuth refresh must NOT be
  reported as success — it loses the rotated refresh token. The caller must log
  CRITICAL and return False; the lock is still released.
- #2 `get_all_agent_tools_with_auth` must exclude disabled tools.
- #5 Tokens are refreshed concurrently (parallel with concurrency limit).
- #7 The OAuth refresh HTTP call must set a timeout (no indefinite hangs).

Additionally covers the refactored helper methods:
- ``_is_token_expiring`` — expiry logic extracted from ``_check_and_refresh_token``
- ``_resolve_oauth_config`` — OAuth config resolution extracted
- ``_perform_token_refresh`` — lock → refresh → persist → release
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from src.services.token_refresh_service import TokenRefreshService

from shared.voice_agents.tool_models import AgentTool, PlatformTool
from shared.voice_agents.tool_service import ToolService


@pytest.fixture(autouse=True)
def allow_test_oauth_hosts(monkeypatch):
    """Keep endpoint tests deterministic while exercising DNS safeguards."""
    monkeypatch.setattr(
        "shared.voice_agents.tools.base.oauth_support._resolve_oauth_host",
        lambda _host: ["93.184.216.34"],
    )


def _agent_tool(
    expires_in_minutes: int = 1,
    has_refresh_token: bool = True,
    has_auth_config: bool = True,
    is_enabled: bool = True,
):
    """Build a mock AgentTool with configurable properties."""
    pt = MagicMock(spec=PlatformTool)
    pt.name = "Test Tool"
    pt.auth_config = (
        {
            "client_id": "cid",
            "client_secret": "csec",
            "token_url": "https://oauth.example.com/token",
        }
        if has_auth_config
        else None
    )
    now = datetime.now(timezone.utc)
    at = MagicMock(spec=AgentTool)
    at.id = uuid4()
    at.oauth_credential_version = 2
    at.oauth_refresh_status = "ready"
    at.oauth_refresh_error_code = None
    at.oauth_credentials_unreadable = False
    at.tool = pt
    at.is_enabled = is_enabled
    sensitive_config = {
        "access_token": "a",
        "expires_at": (now + timedelta(minutes=expires_in_minutes)).timestamp(),
    }
    if has_refresh_token:
        sensitive_config["refresh_token"] = "r"
    at.sensitive_config = sensitive_config
    return at


# ─── _is_token_expiring ────────────────────────────────────────────────────


class TestIsTokenExpiring:
    def test_returns_false_when_no_sensitive_config(self):
        svc = TokenRefreshService(MagicMock())
        at = _agent_tool()
        at.sensitive_config = None
        needs_refresh, _ = svc._is_token_expiring(at)
        assert needs_refresh is False

    def test_returns_false_when_no_expires_at(self):
        svc = TokenRefreshService(MagicMock())
        at = _agent_tool()
        at.sensitive_config = {"access_token": "a"}
        needs_refresh, _ = svc._is_token_expiring(at)
        assert needs_refresh is False

    def test_returns_true_when_already_expired_with_refresh_token(self):
        svc = TokenRefreshService(MagicMock())
        at = _agent_tool(expires_in_minutes=-5)
        needs_refresh, minutes = svc._is_token_expiring(at)
        assert needs_refresh is True
        assert minutes is not None
        assert minutes < 0

    def test_returns_false_when_token_valid_for_long_time(self):
        svc = TokenRefreshService(MagicMock())
        at = _agent_tool(expires_in_minutes=120)
        needs_refresh, _ = svc._is_token_expiring(at)
        assert needs_refresh is False

    def test_returns_true_when_token_expiring_within_window(self):
        svc = TokenRefreshService(MagicMock())
        at = _agent_tool(expires_in_minutes=10)  # within default 15-min window
        needs_refresh, minutes = svc._is_token_expiring(at)
        assert needs_refresh is True
        assert minutes is not None
        assert 9 < minutes < 11  # roughly 10 minutes

    def test_returns_true_when_token_exactly_at_threshold(self):
        svc = TokenRefreshService(MagicMock())
        # Set expiry to exactly the threshold (15 minutes from now)
        now = datetime.now(timezone.utc)
        at = _agent_tool()
        at.sensitive_config["expires_at"] = (now + timedelta(minutes=15)).timestamp()
        needs_refresh, _ = svc._is_token_expiring(at)
        assert needs_refresh is True


# ─── _resolve_oauth_config ──────────────────────────────────────────────────


class TestResolveOauthConfig:
    def test_explicitly_manual_provider_is_never_auto_refreshed(self):
        """Provider metadata can opt out when it cannot issue refresh grants."""
        svc = TokenRefreshService(MagicMock())
        at = _agent_tool()
        at.tool.auth_config["auto_refresh_supported"] = False

        with patch("src.services.token_refresh_service.get_oauth_manager") as gm:
            mgr = MagicMock()
            mgr.extract_oauth_config.return_value = (
                "vendor",
                "https://oauth.example.com/token",
            )
            gm.return_value = mgr

            request = svc._resolve_oauth_config(at)

        assert request is None
        mgr.get_credentials.assert_not_called()

    def test_returns_none_when_no_refresh_token(self):
        svc = TokenRefreshService(MagicMock())
        at = _agent_tool(has_refresh_token=False)
        request = svc._resolve_oauth_config(at)
        assert request is None

    def test_returns_none_when_no_auth_config(self):
        svc = TokenRefreshService(MagicMock())
        at = _agent_tool(has_auth_config=False)
        request = svc._resolve_oauth_config(at)
        assert request is None

    def test_returns_none_when_no_token_url(self):
        svc = TokenRefreshService(MagicMock())
        at = _agent_tool()
        at.tool.auth_config = {"client_id": "cid"}  # no token_url
        with patch("src.services.token_refresh_service.get_oauth_manager") as gm:
            mgr = MagicMock()
            mgr.extract_oauth_config.return_value = ("google", None)
            gm.return_value = mgr
            request = svc._resolve_oauth_config(at)
        assert request is None

    def test_falls_back_to_tool_metadata_when_credentials_fail(self):
        svc = TokenRefreshService(MagicMock())
        at = _agent_tool()
        with patch("src.services.token_refresh_service.get_oauth_manager") as gm:
            mgr = MagicMock()
            mgr.extract_oauth_config.return_value = (
                "google",
                "https://oauth.example.com/token",
            )
            mgr.get_credentials.side_effect = ValueError("bad creds")
            gm.return_value = mgr
            request = svc._resolve_oauth_config(at)
        assert request is not None
        assert request.data == {
            "grant_type": "refresh_token",
            "refresh_token": "r",
            "client_id": "cid",
            "client_secret": "csec",
        }

    def test_returns_oauth_data_and_url_on_success(self):
        svc = TokenRefreshService(MagicMock())
        at = _agent_tool()
        with patch("src.services.token_refresh_service.get_oauth_manager") as gm:
            mgr = MagicMock()
            mgr.extract_oauth_config.return_value = (
                "google",
                "https://oauth.example.com/token",
            )
            mgr.get_auth_data.return_value = {
                "grant_type": "refresh_token",
                "refresh_token": "r",
            }
            gm.return_value = mgr
            request = svc._resolve_oauth_config(at)
        assert request is not None
        assert request.data == {"grant_type": "refresh_token", "refresh_token": "r"}
        assert request.token_url == "https://oauth.example.com/token"


# ─── _perform_token_refresh ─────────────────────────────────────────────────


class TestPerformTokenRefresh:
    async def test_returns_false_when_lock_not_acquired(self):
        tool_service = MagicMock()
        tool_service.claim_refresh_lock = AsyncMock(return_value=None)
        tool_service.release_refresh_lock = AsyncMock(return_value=True)
        svc = TokenRefreshService(tool_service)
        at = _agent_tool()
        result = await svc._perform_token_refresh(
            at,
            {"grant_type": "refresh_token"},
            "https://oauth.example.com/token",
        )
        assert result is False
        tool_service.release_refresh_lock.assert_not_awaited()

    async def test_returns_false_when_refresh_fails(self):
        tool_service = MagicMock()
        tool_service.claim_refresh_lock = AsyncMock(return_value="claim-1")
        tool_service.release_refresh_lock = AsyncMock(return_value=True)
        tool_service.begin_oauth_refresh = AsyncMock(return_value=True)
        tool_service.set_oauth_refresh_status = AsyncMock(return_value=True)
        tool_service.begin_oauth_refresh = AsyncMock(return_value=True)
        tool_service.persist_refreshed_oauth_credentials = AsyncMock(return_value=True)
        svc = TokenRefreshService(tool_service)
        at = _agent_tool()
        with patch.object(
            svc, "_refresh_oauth_token", new_callable=AsyncMock, return_value=None
        ):
            result = await svc._perform_token_refresh(
                at,
                {"grant_type": "refresh_token"},
                "https://oauth.example.com/token",
            )
        assert result is False
        tool_service.release_refresh_lock.assert_awaited_once()

    async def test_returns_false_when_db_update_fails(self):
        tool_service = MagicMock()
        tool_service.claim_refresh_lock = AsyncMock(return_value="claim-1")
        tool_service.release_refresh_lock = AsyncMock(return_value=True)
        tool_service.begin_oauth_refresh = AsyncMock(return_value=True)
        tool_service.set_oauth_refresh_status = AsyncMock(return_value=True)
        tool_service.begin_oauth_refresh = AsyncMock(return_value=True)
        tool_service.set_oauth_refresh_status = AsyncMock(return_value=True)
        svc = TokenRefreshService(tool_service)
        at = _agent_tool()
        with patch.object(
            svc,
            "_refresh_oauth_token",
            new_callable=AsyncMock,
            return_value={"access_token": "new", "expires_in": 3600},
        ), patch.object(
            tool_service,
            "persist_refreshed_oauth_credentials",
            new_callable=AsyncMock,
            return_value=False,
        ):
            result = await svc._perform_token_refresh(
                at,
                {"grant_type": "refresh_token"},
                "https://oauth.example.com/token",
            )
        assert result is False
        tool_service.release_refresh_lock.assert_awaited_once()

    async def test_returns_true_on_success(self):
        tool_service = MagicMock()
        tool_service.claim_refresh_lock = AsyncMock(return_value="claim-1")
        tool_service.release_refresh_lock = AsyncMock(return_value=True)
        tool_service.begin_oauth_refresh = AsyncMock(return_value=True)
        tool_service.persist_refreshed_oauth_credentials = AsyncMock(return_value=True)
        svc = TokenRefreshService(tool_service)
        at = _agent_tool()
        with patch.object(
            svc,
            "_refresh_oauth_token",
            new_callable=AsyncMock,
            return_value={"access_token": "new", "expires_in": 3600},
        ), patch.object(
            tool_service,
            "persist_refreshed_oauth_credentials",
            new_callable=AsyncMock,
            return_value=True,
        ):
            result = await svc._perform_token_refresh(
                at,
                {"grant_type": "refresh_token"},
                "https://oauth.example.com/token",
            )
        assert result is True
        tool_service.release_refresh_lock.assert_awaited_once()


# ─── Original review fix tests (kept for regression) ───────────────────────


@pytest.mark.asyncio
class TestReviewFix1DbUpdateFailure:
    async def test_db_update_failure_after_refresh_returns_false_and_logs_critical(
        self, caplog
    ):
        tool_service = MagicMock()
        tool_service.claim_refresh_lock = AsyncMock(return_value="claim-1")
        tool_service.release_refresh_lock = AsyncMock(return_value=True)
        tool_service.get_agent_tool_with_sensitive_config = AsyncMock(
            return_value=(None, None)
        )
        tool_service.begin_oauth_refresh = AsyncMock(return_value=True)
        tool_service.set_oauth_refresh_status = AsyncMock(return_value=True)
        tool_service.persist_refreshed_oauth_credentials = AsyncMock(return_value=False)
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
                m_oauth.return_value = {
                    "access_token": "new",
                    "refresh_token": "rotated",
                    "expires_in": 3600,
                }
                caplog.set_level(
                    logging.CRITICAL, logger="src.services.token_refresh_service"
                )
                result = await svc._check_and_refresh_token(at)

        assert result is False
        assert any(r.levelno == logging.CRITICAL for r in caplog.records)
        tool_service.release_refresh_lock.assert_awaited_once()


@pytest.mark.asyncio
class TestReviewFix2ExcludeDisabledTools:
    async def test_get_all_agent_tools_with_auth_excludes_disabled(self):
        ts = ToolService()
        mock_client = MagicMock()
        enabled_row = {
            "id": "t1",
            "agent_id": "a1",
            "tool_id": "p1",
            "config": None,
            "sensitive_config": "enc",
            "unselected_functions": None,
            "is_enabled": True,
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
            "last_refreshed_at": None,
            "tool": {"requires_auth": True, "auth_type": "oauth2"},
        }
        disabled_row = dict(enabled_row, id="t2", is_enabled=False)
        query = mock_client.table.return_value.select.return_value.eq.return_value
        query.range.return_value.execute.return_value.data = [
            enabled_row,
            disabled_row,
        ]
        ts.supabase_config = MagicMock()
        ts.supabase_config.client = mock_client

        with patch(
            "shared.voice_agents.tool_service.decrypt_data",
            return_value={"access_token": "x", "refresh_token": "r", "expires_at": 1.0},
        ), patch("shared.voice_agents.tool_service.AgentTool") as MAT, patch(
            "shared.voice_agents.tool_service.PlatformTool"
        ):
            tools, err = await ts.get_all_agent_tools_with_auth()

        assert err is None
        assert MAT.call_count == 1
        mock_client.table.return_value.select.return_value.eq.assert_called_once_with(
            "is_enabled", True
        )


@pytest.mark.asyncio
class TestReviewFix5ParallelRefresh:
    async def test_refresh_expired_tokens_runs_concurrently(self):
        tool_service = MagicMock()
        tool_service.get_all_agent_tools_with_auth = AsyncMock(return_value=([], None))
        svc = TokenRefreshService(tool_service)

        # Create 3 mock agent tools
        tools = [_agent_tool(expires_in_minutes=10) for _ in range(3)]
        tool_service.get_all_agent_tools_with_auth = AsyncMock(
            return_value=(tools, None)
        )

        call_order = []

        async def fake_check(at):
            call_order.append(("start", at.tool.name))
            await asyncio.sleep(0.01)  # simulate async work
            call_order.append(("end", at.tool.name))
            return True

        with patch.object(
            svc, "_check_and_refresh_token", side_effect=fake_check
        ), patch("src.services.token_refresh_service.settings") as mock_settings:
            mock_settings.token_refresh_max_concurrent_refreshes = 2
            mock_settings.token_refresh_check_interval_minutes = 5
            mock_settings.token_refresh_expiry_window_minutes = 15
            await svc._refresh_expired_tokens()

        # All tasks ran.
        start_count = sum(1 for op, _ in call_order if op == "start")
        end_count = sum(1 for op, _ in call_order if op == "end")
        assert start_count == 3
        assert end_count == 3

        # Concurrency: with a semaphore of 2, at least 2 tasks must START before
        # the first one ENDS (a sequential loop would have exactly 1 start before
        # the first end).
        first_end_idx = next(i for i, (op, _) in enumerate(call_order) if op == "end")
        starts_before_first_end = sum(
            1 for op, _ in call_order[:first_end_idx] if op == "start"
        )
        assert starts_before_first_end >= 2

    async def test_refresh_expired_tokens_handles_exceptions_gracefully(self):
        tool_service = MagicMock()
        tools = [_agent_tool(expires_in_minutes=10) for _ in range(2)]
        tool_service.get_all_agent_tools_with_auth = AsyncMock(
            return_value=(tools, None)
        )
        svc = TokenRefreshService(tool_service)

        call_count = 0

        async def fake_check(at):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("boom")
            return True

        with patch.object(
            svc, "_check_and_refresh_token", side_effect=fake_check
        ), patch("src.services.token_refresh_service.settings") as mock_settings:
            mock_settings.token_refresh_max_concurrent_refreshes = 5
            mock_settings.token_refresh_check_interval_minutes = 5
            mock_settings.token_refresh_expiry_window_minutes = 15
            # Should not raise — exceptions are caught per-tool
            await svc._refresh_expired_tokens()


@pytest.mark.asyncio
class TestReviewFix7HttpTimeout:
    async def test_refresh_oauth_token_sets_timeout(self):
        svc = TokenRefreshService(MagicMock())
        token_url = "https://oauth.example.com/token"
        oauth_data = {"grant_type": "refresh_token", "refresh_token": "r"}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "new", "expires_in": 3600}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            await svc._refresh_oauth_token(token_url, oauth_data)
            args, kwargs = mock_client_class.call_args
            assert "timeout" in kwargs and kwargs["timeout"] is not None


@pytest.mark.asyncio
class TestReviewFix3LeaseConfigurable:
    async def test_claim_uses_configured_lease_seconds(self):
        tool_service = MagicMock()
        tool_service.claim_refresh_lock = AsyncMock(return_value=None)
        svc = TokenRefreshService(tool_service)

        at = _agent_tool()
        with patch("src.services.token_refresh_service.settings") as mock_settings:
            mock_settings.token_refresh_expiry_window_minutes = 15
            mock_settings.token_refresh_check_interval_minutes = 5
            mock_settings.token_refresh_lock_lease_seconds = 240
            mock_settings.token_refresh_max_concurrent_refreshes = 5
            await svc._check_and_refresh_token(at)

        tool_service.claim_refresh_lock.assert_awaited_once()
        assert tool_service.claim_refresh_lock.await_args.kwargs["lease_seconds"] == 240
