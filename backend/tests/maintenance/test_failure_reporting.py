"""Scheduler-facing failures must not be reported as successful empty work."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from src.notifications.lead_notification_outbox import InterestLeadNotificationOutbox
from src.notifications.oauth_attention_outbox import OAuthAttentionOutbox
from src.services.token_refresh_service import TokenRefreshService


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "outbox_class", [InterestLeadNotificationOutbox, OAuthAttentionOutbox]
)
async def test_strict_outbox_propagates_database_claim_failure_safely(outbox_class):
    client = MagicMock()
    client.rpc.side_effect = RuntimeError("private database details")
    config = SimpleNamespace(service_client=client, client=None)
    outbox = outbox_class(supabase_config_override=config)
    with pytest.raises(RuntimeError) as caught:
        await outbox.process_pending(strict=True)
    assert "private database details" not in str(caught.value)
    assert await outbox.process_pending() == 0


@pytest.mark.asyncio
async def test_strict_oauth_pass_reports_failed_connection_scan():
    tool_service = MagicMock()
    tool_service.get_all_agent_tools_with_auth = AsyncMock(
        return_value=([], "private database details")
    )
    service = TokenRefreshService(tool_service)
    with pytest.raises(RuntimeError) as caught:
        await service.run_once(strict=True)
    assert "private database details" not in str(caught.value)
