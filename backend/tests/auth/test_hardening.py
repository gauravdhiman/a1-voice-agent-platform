"""Tests for Epic E auth hardening: audit trail, reset flow, Turnstile."""

from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.auth.audit import log_auth_event


def _request():
    from starlette.requests import Request

    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/auth/signup",
            "headers": [(b"user-agent", b"test-agent/1.0")],
            "query_string": b"",
            "server": ("testserver", 80),
            "scheme": "http",
            "client": ("127.0.0.1", 50000),
        }
    )


def _chain_client(rows=None):
    response = MagicMock()
    response.data = rows if rows is not None else []
    node = MagicMock()
    node.execute = MagicMock(return_value=response)
    for method in ("select", "insert", "update", "order", "limit", "eq"):
        getattr(node, method).return_value = node
    client = MagicMock()
    client.table.return_value = node
    return client


class TestLogAuthEvent:
    @pytest.mark.asyncio
    async def test_appends_bounded_row(self):
        """Audit writes email/IP/UA metadata without raising."""
        client = _chain_client([{"id": "1"}])
        await log_auth_event(
            "signup_denied",
            email="  X@Y.com ",
            request=_request(),
            metadata={"reason": "signup_disabled"},
            supabase=client,
        )
        client.table.assert_called_with("auth_audit_events")
        node = client.table.return_value
        inserted = node.insert.call_args[0][0]
        assert inserted["event"] == "signup_denied"
        assert inserted["email"] == "x@y.com"
        assert inserted["ip"] == "127.0.0.1"
        assert inserted["user_agent"] == "test-agent/1.0"
        assert inserted["metadata"] == {"reason": "signup_disabled"}

    @pytest.mark.asyncio
    async def test_never_raises_without_client_or_on_failure(self):
        """Audit is best-effort: missing client and DB errors are silent."""
        await log_auth_event("signin", email="x@y.com", request=_request())
        failing = _chain_client()
        failing.table.return_value.insert.side_effect = RuntimeError("db down")
        await log_auth_event("signin", email="x@y.com", supabase=failing)


class TestPasswordResetRoute:
    @pytest.mark.asyncio
    async def test_unknown_email_returns_safe_message(self):
        """No oracle: unknown and known emails share one response."""
        from src.auth.password_reset import SAFE_RESET_MESSAGE
        from src.auth.routes import request_password_reset
        from src.notifications.platform_settings_models import (
            ResendVerificationRequest,
        )

        with patch(
            "src.auth.password_reset.password_reset_service.request_reset",
            new=AsyncMock(return_value=(False, None)),
        ), patch("src.auth.routes.log_auth_event", new=AsyncMock()), patch(
            "src.auth.routes.organization_service"
        ):
            result = await request_password_reset(
                request=_request(),
                body=ResendVerificationRequest(email="ghost@example.com"),
            )
            assert result.message == SAFE_RESET_MESSAGE

    @pytest.mark.asyncio
    async def test_known_email_audits_dispatch(self):
        """Dispatched resets audit with dispatched=true."""
        from src.auth.routes import request_password_reset
        from src.notifications.platform_settings_models import (
            ResendVerificationRequest,
        )

        with patch(
            "src.auth.password_reset.password_reset_service.request_reset",
            new=AsyncMock(return_value=(True, None)),
        ), patch(
            "src.auth.routes.log_auth_event", new=AsyncMock()
        ) as mock_audit, patch(
            "src.auth.routes.organization_service"
        ):
            await request_password_reset(
                request=_request(),
                body=ResendVerificationRequest(email="sam@example.com"),
            )
            _, kwargs = mock_audit.call_args
            assert kwargs["metadata"] == {"dispatched": True}


class TestPasswordResetService:
    @pytest.mark.asyncio
    async def test_missing_account_sends_nothing(self):
        """Unknown emails short-circuit before any provider access."""
        from src.auth.password_reset import password_reset_service

        with patch(
            "src.auth.service.auth_service._find_auth_user_by_email",
            new=AsyncMock(return_value=None),
        ):
            sent, error = await password_reset_service.request_reset(
                "ghost@example.com"
            )
            assert sent is False
            assert error is None

    @pytest.mark.asyncio
    async def test_existing_account_gets_recovery_link_email(self):
        """Known accounts receive the recovery link through Resend."""
        from src.auth.password_reset import password_reset_service

        user = Mock()
        user.id = uuid4()
        user.user_metadata = {"first_name": "Sam"}
        link = Mock()
        link.properties = Mock(action_link="https://recovery.example/abc")
        admin = Mock()
        admin.generate_link = Mock(return_value=link)
        client = Mock()
        client.auth = Mock(admin=admin)
        sent_response = Mock(success=True, message="sent")

        with patch(
            "src.auth.service.auth_service._find_auth_user_by_email",
            new=AsyncMock(return_value=user),
        ), patch.object(
            type(password_reset_service),
            "supabase",
            new_callable=lambda: property(lambda self: client),
        ), patch(
            "src.auth.password_reset.notification_service"
        ) as mock_notifications:
            mock_notifications.send_notification = AsyncMock(return_value=sent_response)
            sent, error = await password_reset_service.request_reset("sam@example.com")
            assert sent is True
            assert error is None
            admin.generate_link.assert_called_once()
            payload = admin.generate_link.call_args[0][0]
            assert payload["type"] == "recovery"
            assert payload["email"] == "sam@example.com"
            assert payload["options"]["redirect_to"].endswith("/auth/reset-password")
            notify_payload = mock_notifications.send_notification.call_args[0][0]
            assert notify_payload.event_key == "user.password_reset"
            assert (
                notify_payload.template_variables["reset_url"]
                == "https://recovery.example/abc"
            )


class TestAuditListRoute:
    @pytest.mark.asyncio
    async def test_regular_user_is_denied(self):
        """Audit reads are platform-admin only, enforced in the route."""
        from src.auth.routes import list_audit_events

        profile = Mock()
        profile.has_role = Mock(return_value=False)
        with pytest.raises(HTTPException) as exc_info:
            await list_audit_events(
                request=_request(),
                user_data=(uuid4(), profile),
                event=None,
                limit=100,
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_platform_admin_lists_events(self):
        """Admins receive newest-first rows."""
        from src.auth.routes import list_audit_events

        profile = Mock()
        profile.has_role = Mock(side_effect=lambda role: role == "platform_admin")
        rows = [
            {
                "id": str(uuid4()),
                "user_id": None,
                "email": "x@y.com",
                "event": "signin_denied",
                "ip": "127.0.0.1",
                "user_agent": "t",
                "metadata": {},
                "created_at": "2026-09-05T00:00:00+00:00",
            }
        ]
        with patch("src.auth.routes.organization_service") as mock_org:
            mock_org.supabase = _chain_client(rows)
            result = await list_audit_events(
                request=_request(),
                user_data=(uuid4(), profile),
                event=None,
                limit=100,
            )
            assert len(result) == 1
            assert result[0].event == "signin_denied"
