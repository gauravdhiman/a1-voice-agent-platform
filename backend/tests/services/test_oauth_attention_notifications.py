"""Tests for OAuth connection-attention notifications."""

import logging
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from src.notifications.oauth_attention_notifier import (
    OAuthAttentionNotificationPhase,
    OAuthAttentionNotifier,
)
from src.services.token_refresh_service import OAuthRefreshRequest, TokenRefreshService

from shared.voice_agents.tool_service import ToolService


def _member(name: str, role_names: list[str]):
    """Create the small member shape used by the organization role service."""
    return SimpleNamespace(
        id=uuid4(),
        email=f"{name.lower().replace(' ', '.')}@example.com",
        first_name=name.split()[0],
        last_name=name.split()[-1],
        roles=[SimpleNamespace(name=role_name) for role_name in role_names],
    )


def _agent_tool(
    expires_in_minutes: int,
    *,
    has_refresh_token: bool,
    auth_config: dict | None = None,
):
    """Create a tool connection with the context needed by notifications."""
    sensitive_config = {
        "access_token": "access-token-that-must-not-be-notified",
        "expires_at": (
            datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes)
        ).timestamp(),
    }
    if has_refresh_token:
        sensitive_config["refresh_token"] = "refresh-token-that-must-not-be-notified"

    return SimpleNamespace(
        id=uuid4(),
        agent_id=uuid4(),
        organization_id=uuid4(),
        agent_name="Support Agent",
        sensitive_config=sensitive_config,
        tool=SimpleNamespace(
            name="Example MCP",
            auth_config=auth_config
            or {
                "client_id": "client-id",
                "token_url": "https://oauth.example.com/token",
            },
        ),
    )


def _notifier(**kwargs):
    """Build a notifier with isolated platform configuration and channel queue."""
    kwargs.setdefault(
        "platform_settings_service",
        SimpleNamespace(get_platform_admin_email=AsyncMock(return_value=None)),
    )
    kwargs.setdefault("platform_channel_outbox", SimpleNamespace(enqueue=AsyncMock()))
    kwargs.setdefault(
        "organization_settings_service",
        SimpleNamespace(
            get_settings=AsyncMock(return_value=SimpleNamespace(alert_email=None))
        ),
    )
    return OAuthAttentionNotifier(**kwargs)


@pytest.mark.asyncio
async def test_auth_tool_loader_keeps_agent_and_organization_context():
    """Background OAuth checks receive context without changing public responses."""
    tool_service = ToolService()
    mock_client = MagicMock()
    tool_service.supabase_config = MagicMock()
    tool_service.supabase_config.client = mock_client
    tool_service.supabase_config.is_configured.return_value = True
    agent_id = uuid4()
    organization_id = uuid4()
    tool_id = uuid4()
    row = {
        "id": str(uuid4()),
        "agent_id": str(agent_id),
        "tool_id": str(tool_id),
        "config": None,
        "sensitive_config": "encrypted",
        "unselected_functions": None,
        "is_enabled": True,
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "last_refreshed_at": None,
        "voice_agents": {
            "name": "Support Agent",
            "organization_id": str(organization_id),
        },
        "tool": {
            "id": str(tool_id),
            "name": "Example MCP",
            "requires_auth": True,
            "auth_type": "oauth2",
            "auth_config": {"token_url": "https://oauth.example.com/token"},
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        },
    }
    result_query = mock_client.table.return_value.select.return_value.eq.return_value
    result_query.range.return_value.execute.return_value.data = [row]

    with patch(
        "shared.voice_agents.tool_service.decrypt_data",
        return_value={
            "access_token": "access",
            "refresh_token": "refresh",
            "expires_at": 1.0,
        },
    ):
        tools, error = await tool_service.get_all_agent_tools_with_auth()

    assert error is None
    assert tools[0].agent_name == "Support Agent"
    assert tools[0].organization_id == organization_id

    row["tool"]["auth_type"] = "api_key"
    row["tool"]["auth_config"] = {"header": "X-API-Key"}
    with patch(
        "shared.voice_agents.tool_service.decrypt_data",
        return_value={"api_key": "api-key"},
    ):
        non_oauth_tools, error = await tool_service.get_all_agent_tools_with_auth()

    assert error is None
    assert non_oauth_tools == []


@pytest.mark.asyncio
async def test_auth_tool_loader_distinguishes_missing_tokens_from_decryption_failure():
    """A readable config without tokens is not an encryption-key incident."""
    tool_service = ToolService()
    mock_client = MagicMock()
    tool_service.supabase_config = MagicMock()
    tool_service.supabase_config.client = mock_client
    tool_service.supabase_config.is_configured.return_value = True
    row = {
        "id": str(uuid4()),
        "agent_id": str(uuid4()),
        "tool_id": str(uuid4()),
        "config": None,
        "sensitive_config": "encrypted",
        "is_enabled": True,
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "voice_agents": {"name": "Agent", "organization_id": str(uuid4())},
        "tool": {
            "id": str(uuid4()),
            "requires_auth": True,
            "auth_type": "oauth2",
            "name": "Calendar",
            "auth_config": {"token_url": "https://oauth.example.com/token"},
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        },
    }
    result_query = mock_client.table.return_value.select.return_value.eq.return_value
    result_query.range.return_value.execute.return_value.data = [row]

    with patch(
        "shared.voice_agents.tool_service.decrypt_data",
        return_value={"oauth_client_id": "client-id"},
    ):
        tools, error = await tool_service.get_all_agent_tools_with_auth()

    assert error is None
    assert len(tools) == 1
    assert tools[0].oauth_credentials_unreadable is False


@pytest.mark.asyncio
async def test_auth_tool_loader_paginates_past_database_page_limit():
    """A refresh cycle visits rows across PostgREST response pages."""
    tool_service = ToolService()
    mock_client = MagicMock()
    tool_service.supabase_config = MagicMock()
    tool_service.supabase_config.client = mock_client
    tool_service.OAUTH_REFRESH_SCAN_PAGE_SIZE = 2
    row_template = {
        "agent_id": str(uuid4()),
        "tool_id": str(uuid4()),
        "config": None,
        "sensitive_config": "encrypted",
        "unselected_functions": None,
        "is_enabled": True,
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "last_refreshed_at": None,
        "voice_agents": {"name": "Agent", "organization_id": str(uuid4())},
        "tool": {
            "requires_auth": True,
            "auth_type": "oauth2",
            "name": "Calendar",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        },
    }
    rows = [dict(row_template, id=str(uuid4())) for _ in range(3)]
    range_query = (
        mock_client.table.return_value.select.return_value.eq.return_value.range
    )
    range_query.side_effect = [
        SimpleNamespace(execute=MagicMock(return_value=SimpleNamespace(data=rows[:2]))),
        SimpleNamespace(execute=MagicMock(return_value=SimpleNamespace(data=rows[2:]))),
    ]

    with patch(
        "shared.voice_agents.tool_service.decrypt_data",
        return_value={
            "access_token": "access",
            "refresh_token": "refresh",
        },
    ), patch("shared.voice_agents.tool_service.AgentTool") as agent_model, patch(
        "shared.voice_agents.tool_service.PlatformTool"
    ):
        tools, error = await tool_service.get_all_agent_tools_with_auth()

    assert error is None
    assert len(tools) == 3
    assert range_query.call_args_list[0].args == (0, 1)
    assert range_query.call_args_list[1].args == (2, 3)
    assert agent_model.call_count == 3


@pytest.mark.asyncio
async def test_notifier_sends_one_email_per_org_admin_without_token_values():
    """OAuth notices go to org admins and never include credential values."""
    sender_call = AsyncMock(return_value=SimpleNamespace(success=True))
    sender = SimpleNamespace(send_notification=sender_call)
    role_service = MagicMock()
    org_admin = _member("Org Admin", ["org_admin"])
    regular_member = _member("Regular Member", ["member"])
    role_service.get_users_by_organization = AsyncMock(
        return_value=([org_admin, regular_member], None)
    )
    notifier = _notifier(
        notification_sender=sender,
        user_role_service=role_service,
        organization_name_resolver=AsyncMock(return_value="Example Organization"),
    )
    tool = _agent_tool(expires_in_minutes=20, has_refresh_token=False)

    result = await notifier.notify(
        tool,
        phase=OAuthAttentionNotificationPhase.EXPIRING,
        minutes_until_expiry=20,
        reason="This connection cannot be renewed automatically.",
    )

    assert result.sent == 1
    role_service.get_users_by_organization.assert_awaited_once_with(
        tool.organization_id
    )
    sender_call.assert_awaited_once()
    request = sender_call.await_args.args[0]
    assert request.event_key == "tools.oauth_reauthorization_required"
    assert request.organization_id == tool.organization_id
    assert request.user_id == org_admin.id
    assert request.template_variables["organization_name"] == "Example Organization"
    assert request.template_variables["agent_name"] == "Support Agent"
    assert "access-token" not in repr(request.template_variables)
    assert "refresh-token" not in repr(request.template_variables)
    assert request.idempotency_key.startswith(f"oauth-attention:{tool.id}:v0:expiring:")


@pytest.mark.asyncio
async def test_notifier_sends_optional_shared_organization_alert_email():
    """A shared inbox gets an additional email without replacing admin emails."""
    sender_call = AsyncMock(return_value=SimpleNamespace(success=True))
    admin = _member("Org Admin", ["org_admin"])
    role_service = SimpleNamespace(
        get_users_by_organization=AsyncMock(return_value=([admin], None))
    )
    notifier = _notifier(
        notification_sender=SimpleNamespace(send_notification=sender_call),
        user_role_service=role_service,
        organization_name_resolver=AsyncMock(return_value="Example Organization"),
        organization_settings_service=SimpleNamespace(
            get_settings=AsyncMock(
                return_value=SimpleNamespace(alert_email="operations@example.com")
            )
        ),
    )

    result = await notifier.notify(
        _agent_tool(expires_in_minutes=10, has_refresh_token=False),
        phase=OAuthAttentionNotificationPhase.EXPIRING,
        minutes_until_expiry=10,
        reason="Reconnect the tool to restore access.",
    )

    assert result.sent == 2
    assert {call.args[0].recipient_email for call in sender_call.await_args_list} == {
        admin.email,
        "operations@example.com",
    }
    shared_request = next(
        call.args[0]
        for call in sender_call.await_args_list
        if call.args[0].recipient_email == "operations@example.com"
    )
    assert shared_request.user_id is None
    assert "organization-email:operations@example.com" in shared_request.idempotency_key


@pytest.mark.asyncio
async def test_notifier_deduplicates_shared_email_matching_an_admin():
    """A case-only shared-email match does not deliver the same event twice."""
    sender_call = AsyncMock(return_value=SimpleNamespace(success=True))
    admin = _member("Org Admin", ["org_admin"])
    role_service = SimpleNamespace(
        get_users_by_organization=AsyncMock(return_value=([admin], None))
    )
    notifier = _notifier(
        notification_sender=SimpleNamespace(send_notification=sender_call),
        user_role_service=role_service,
        organization_settings_service=SimpleNamespace(
            get_settings=AsyncMock(
                return_value=SimpleNamespace(alert_email=admin.email.upper())
            )
        ),
    )

    result = await notifier.notify(
        _agent_tool(expires_in_minutes=10, has_refresh_token=False),
        phase=OAuthAttentionNotificationPhase.EXPIRING,
        minutes_until_expiry=10,
        reason="Reconnect the tool to restore access.",
    )

    assert result.sent == 1
    sender_call.assert_awaited_once()


@pytest.mark.asyncio
async def test_notifier_uses_a_distinct_idempotency_key_after_expiry():
    """The expired notice is independent from the earlier warning."""
    sender_call = AsyncMock(return_value=SimpleNamespace(success=True))
    sender = SimpleNamespace(send_notification=sender_call)
    admin = _member("Org Admin", ["org_admin"])
    role_service = MagicMock()
    role_service.get_users_by_organization = AsyncMock(return_value=([admin], None))
    notifier = _notifier(
        notification_sender=sender,
        user_role_service=role_service,
        organization_name_resolver=AsyncMock(return_value="Example Organization"),
    )
    tool = _agent_tool(expires_in_minutes=-5, has_refresh_token=False)

    result = await notifier.notify(
        tool,
        phase=OAuthAttentionNotificationPhase.EXPIRED,
        minutes_until_expiry=-5,
        reason="This connection has expired and must be connected again.",
    )

    assert result.sent == 1
    request = sender_call.await_args.args[0]
    assert request.template_variables["status_text"] == "has expired"
    assert request.idempotency_key.startswith(f"oauth-attention:{tool.id}:v0:expired:")


@pytest.mark.asyncio
async def test_notifier_emails_platform_admin_and_queues_safe_channel_alerts():
    """Organization and platform admins receive durable, credential-free alerts."""
    sender_call = AsyncMock(return_value=SimpleNamespace(success=True))
    sender = SimpleNamespace(send_notification=sender_call)
    role_service = SimpleNamespace(
        get_users_by_organization=AsyncMock(
            return_value=([_member("Org Admin", ["org_admin"])], None)
        )
    )
    platform_settings = SimpleNamespace(
        get_platform_admin_email=AsyncMock(return_value="platform@example.com")
    )
    channel_outbox = SimpleNamespace(enqueue=AsyncMock())
    notifier = OAuthAttentionNotifier(
        notification_sender=sender,
        user_role_service=role_service,
        organization_name_resolver=AsyncMock(return_value="Example Organization"),
        platform_settings_service=platform_settings,
        platform_channel_outbox=channel_outbox,
        organization_settings_service=SimpleNamespace(
            get_settings=AsyncMock(return_value=SimpleNamespace(alert_email=None))
        ),
    )
    tool = _agent_tool(expires_in_minutes=-1, has_refresh_token=True)
    tool.oauth_credential_version = 12
    tool.oauth_refresh_error_code = "provider_invalid_grant"

    result = await notifier.notify(
        tool,
        phase=OAuthAttentionNotificationPhase.ACTION_REQUIRED,
        minutes_until_expiry=None,
        reason="Reconnect the tool to restore access.",
        immediate=True,
    )

    assert result.sent == 2
    assert {call.args[0].recipient_email for call in sender_call.await_args_list} == {
        "org.admin@example.com",
        "platform@example.com",
    }
    channel_outbox.enqueue.assert_awaited_once()
    payload = channel_outbox.enqueue.await_args.kwargs["payload"]
    assert payload["status_text"] == "requires immediate administrator action"
    assert "access-token" not in repr(payload)
    assert "refresh-token" not in repr(payload)


@pytest.mark.asyncio
async def test_unusable_token_notifies_immediately_outside_expiry_window():
    """A stored unrecoverable state bypasses the normal expiry notification window."""
    tool = _agent_tool(expires_in_minutes=180, has_refresh_token=True)
    tool.oauth_refresh_status = "outcome_unknown"
    tool.oauth_refresh_error_code = "provider_request_outcome_unknown"
    tool_service = SimpleNamespace(
        get_all_agent_tools_with_auth=AsyncMock(return_value=([tool], None))
    )
    notifier = SimpleNamespace(notify=AsyncMock())
    service = TokenRefreshService(tool_service, oauth_attention_notifier=notifier)

    with patch("src.services.token_refresh_service.settings") as mock_settings:
        mock_settings.token_refresh_max_concurrent_refreshes = 2
        mock_settings.token_refresh_attention_window_minutes = 30
        await service._refresh_expired_tokens()

    notifier.notify.assert_awaited_once()
    assert notifier.notify.await_args.kwargs["phase"] is (
        OAuthAttentionNotificationPhase.ACTION_REQUIRED
    )
    assert notifier.notify.await_args.kwargs["immediate"] is True
    assert (
        "Do not retry the old permission" in notifier.notify.await_args.kwargs["reason"]
    )


@pytest.mark.asyncio
async def test_refresh_cycle_notifies_manual_connection_within_thirty_minutes():
    """Manual connections are detected by the same scheduler as refreshable ones."""
    tool_service = MagicMock()
    tool = _agent_tool(expires_in_minutes=20, has_refresh_token=False)
    tool_service.get_all_agent_tools_with_auth = AsyncMock(return_value=([tool], None))
    notifier = MagicMock()
    notifier.notify = AsyncMock()
    service = TokenRefreshService(tool_service, oauth_attention_notifier=notifier)

    with patch("src.services.token_refresh_service.settings") as mock_settings:
        mock_settings.token_refresh_max_concurrent_refreshes = 5
        mock_settings.token_refresh_expiry_window_minutes = 15
        mock_settings.token_refresh_attention_window_minutes = 30
        await service._refresh_expired_tokens()

    notifier.notify.assert_awaited_once()
    assert (
        notifier.notify.await_args.kwargs["phase"]
        is OAuthAttentionNotificationPhase.EXPIRING
    )


@pytest.mark.asyncio
async def test_refresh_cycle_notifies_manual_connection_after_expiry():
    """Expired manual connections produce the stronger follow-up notice."""
    tool_service = MagicMock()
    tool = _agent_tool(expires_in_minutes=-5, has_refresh_token=False)
    tool_service.get_all_agent_tools_with_auth = AsyncMock(return_value=([tool], None))
    notifier = MagicMock()
    notifier.notify = AsyncMock()
    service = TokenRefreshService(tool_service, oauth_attention_notifier=notifier)

    with patch("src.services.token_refresh_service.settings") as mock_settings:
        mock_settings.token_refresh_max_concurrent_refreshes = 5
        mock_settings.token_refresh_expiry_window_minutes = 15
        mock_settings.token_refresh_attention_window_minutes = 30
        await service._refresh_expired_tokens()

    notifier.notify.assert_awaited_once()
    assert (
        notifier.notify.await_args.kwargs["phase"]
        is OAuthAttentionNotificationPhase.EXPIRED
    )


@pytest.mark.asyncio
async def test_refresh_cycle_notifies_when_manual_expiry_cannot_be_verified():
    """Missing expiry metadata is actionable instead of silently ignored."""
    tool_service = MagicMock()
    tool = _agent_tool(expires_in_minutes=20, has_refresh_token=False)
    tool.sensitive_config.pop("expires_at")
    tool_service.get_all_agent_tools_with_auth = AsyncMock(return_value=([tool], None))
    notifier = MagicMock()
    notifier.notify = AsyncMock()
    service = TokenRefreshService(tool_service, oauth_attention_notifier=notifier)

    with patch("src.services.token_refresh_service.settings") as mock_settings:
        mock_settings.token_refresh_max_concurrent_refreshes = 5
        mock_settings.token_refresh_expiry_window_minutes = 15
        mock_settings.token_refresh_attention_window_minutes = 30
        await service._refresh_expired_tokens()

    notifier.notify.assert_awaited_once()
    assert (
        notifier.notify.await_args.kwargs["phase"]
        is OAuthAttentionNotificationPhase.EXPIRING
    )
    assert notifier.notify.await_args.kwargs["minutes_until_expiry"] is None


@pytest.mark.asyncio
async def test_unknown_provider_with_standard_refresh_metadata_is_not_notified():
    """An unknown label is not treated as manual when standard renewal works."""
    tool_service = MagicMock()
    tool = _agent_tool(
        expires_in_minutes=20,
        has_refresh_token=True,
        auth_config={
            "provider": "future-vendor",
            "client_id": "client-id",
            "token_url": "https://oauth.example.com/token",
        },
    )
    tool_service.get_all_agent_tools_with_auth = AsyncMock(return_value=([tool], None))
    notifier = MagicMock()
    notifier.notify = AsyncMock()
    service = TokenRefreshService(tool_service, oauth_attention_notifier=notifier)

    with patch.object(
        service,
        "_resolve_oauth_config",
        return_value=OAuthRefreshRequest(
            data={"grant_type": "refresh_token"},
            token_url="https://oauth.example.com/token",
        ),
    ), patch("src.services.token_refresh_service.settings") as mock_settings:
        mock_settings.token_refresh_max_concurrent_refreshes = 5
        mock_settings.token_refresh_expiry_window_minutes = 15
        mock_settings.token_refresh_attention_window_minutes = 30
        await service._refresh_expired_tokens()

    notifier.notify.assert_not_awaited()


@pytest.mark.asyncio
async def test_failed_automatic_refresh_notifies_when_reauthentication_is_needed():
    """A failed standard refresh is actionable even when metadata is automatic."""
    tool_service = MagicMock()
    tool_service.get_all_agent_tools_with_auth = AsyncMock(return_value=([], None))
    tool = _agent_tool(
        expires_in_minutes=10,
        has_refresh_token=True,
        auth_config={
            "provider": "future-vendor",
            "client_id": "client-id",
            "token_url": "https://oauth.example.com/token",
        },
    )
    tool_service.get_all_agent_tools_with_auth = AsyncMock(return_value=([tool], None))
    notifier = MagicMock()
    notifier.notify = AsyncMock()
    service = TokenRefreshService(tool_service, oauth_attention_notifier=notifier)

    with patch.object(
        service,
        "_resolve_oauth_config",
        return_value=OAuthRefreshRequest(
            data={"grant_type": "refresh_token"},
            token_url="https://oauth.example.com/token",
        ),
    ), patch.object(
        service, "_perform_token_refresh", new_callable=AsyncMock, return_value=False
    ), patch(
        "src.services.token_refresh_service.settings"
    ) as mock_settings:
        mock_settings.token_refresh_max_concurrent_refreshes = 5
        mock_settings.token_refresh_expiry_window_minutes = 15
        mock_settings.token_refresh_attention_window_minutes = 30
        await service._refresh_expired_tokens()

    notifier.notify.assert_awaited_once()
    assert "renew" in notifier.notify.await_args.kwargs["reason"].lower()


@pytest.mark.asyncio
async def test_notifier_redacts_recipient_and_provider_errors(caplog):
    """OAuth delivery logs omit recipient addresses and raw provider failures."""
    caplog.set_level(logging.ERROR, logger="src.notifications.oauth_attention_notifier")
    admin = _member("Sensitive Admin", ["org_admin"])
    role_service = SimpleNamespace(
        get_users_by_organization=AsyncMock(return_value=([admin], None))
    )
    sender = SimpleNamespace(
        send_notification=AsyncMock(
            side_effect=RuntimeError("provider rejected secret@example.com")
        )
    )
    notifier = _notifier(
        notification_sender=sender,
        user_role_service=role_service,
        organization_name_resolver=AsyncMock(return_value="Example Organization"),
        organization_settings_service=SimpleNamespace(
            get_settings=AsyncMock(
                return_value=SimpleNamespace(alert_email="alerts@example.com")
            )
        ),
    )

    result = await notifier.notify(
        _agent_tool(expires_in_minutes=10, has_refresh_token=False),
        phase=OAuthAttentionNotificationPhase.EXPIRING,
        minutes_until_expiry=10,
        reason="Reconnect the tool to restore access.",
    )

    assert result.failed == 2
    assert admin.email not in caplog.text
    assert "alerts@example.com" not in caplog.text
    assert "secret@example.com" not in caplog.text
    assert "RuntimeError" in caplog.text
