"""Tests for callback escalation persistence and the runtime record hook."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from shared.voice_agents.callback_service import (
    CallbackEscalationService,
    record_callback_tool_outcome,
)
from shared.voice_agents.tools.base.tool_context import ToolContext

ORG_ID = "11111111-1111-1111-1111-111111111111"
AGENT_ID = "22222222-2222-2222-2222-222222222222"


def _chain_client(rows=None, explode=False):
    """Fake service-role client emulating the fluent query chain."""
    response = MagicMock()
    response.data = rows if rows is not None else []
    execute = MagicMock(return_value=response)
    if explode:
        execute.side_effect = RuntimeError("db down")
    node = MagicMock()
    node.execute = execute
    for method in ("select", "insert", "update", "order", "limit", "eq"):
        getattr(node, method).return_value = node
    client = MagicMock()
    client.table.return_value = node
    return client


def _stored_row(**overrides):
    row = {
        "id": str(uuid4()),
        "organization_id": ORG_ID,
        "agent_id": AGENT_ID,
        "session_id": "session-1",
        "caller_phone": "+14805550100",
        "caller_name": "Sam",
        "reason": "Water heater is leaking.",
        "urgency": "urgent",
        "status": "new",
        "notified": True,
        "created_at": "2026-09-04T00:00:00+00:00",
        "acknowledged_at": None,
    }
    row.update(overrides)
    return row


def _context(**overrides):
    data = {
        "organization_id": ORG_ID,
        "agent_id": AGENT_ID,
        "session_id": "session-1",
    }
    data.update(overrides)
    return ToolContext(**data)


class TestRecordCallbackToolOutcome:
    @pytest.mark.asyncio
    async def test_notified_result_is_stored(self):
        """An accepted callback becomes exactly one dashboard row."""
        service = CallbackEscalationService(client=_chain_client([_stored_row()]))
        with patch(
            "shared.voice_agents.callback_service.callback_escalation_service",
            service,
        ):
            stored = await record_callback_tool_outcome(
                context=_context(),
                function_name="request_human_callback",
                arguments={
                    "callback_phone": "+14805550100",
                    "reason": "Water heater is leaking.",
                    "urgency": "urgent",
                },
                result={"status": "notified", "notified": True},
            )
        assert stored is True
        service.client.table.assert_called_with("callback_escalations")

    @pytest.mark.asyncio
    async def test_demo_sessions_are_skipped(self):
        """Demo calls never pollute the owner dashboard."""
        service = CallbackEscalationService(client=_chain_client([_stored_row()]))
        with patch(
            "shared.voice_agents.callback_service.callback_escalation_service",
            service,
        ):
            stored = await record_callback_tool_outcome(
                context=_context(is_demo=True, demo_slug="dental"),
                function_name="request_human_callback",
                arguments={
                    "callback_phone": "+14805550100",
                    "reason": "Cleaning.",
                },
                result={"status": "notified", "notified": True},
            )
        assert stored is False
        service.client.table.assert_not_called()

    @pytest.mark.asyncio
    async def test_other_tools_and_failures_are_skipped(self):
        """Only accepted callback results produce rows."""
        service = CallbackEscalationService(client=_chain_client([_stored_row()]))
        with patch(
            "shared.voice_agents.callback_service.callback_escalation_service",
            service,
        ):
            assert (
                await record_callback_tool_outcome(
                    context=_context(),
                    function_name="send_resend_email",
                    arguments={},
                    result={"status": "accepted"},
                )
                is False
            )
            assert (
                await record_callback_tool_outcome(
                    context=_context(),
                    function_name="request_human_callback",
                    arguments={
                        "callback_phone": "+14805550100",
                        "reason": "Billing.",
                    },
                    result={"status": "error"},
                )
                is False
            )
            assert (
                await record_callback_tool_outcome(
                    context=None,
                    function_name="request_human_callback",
                    arguments={},
                    result={"status": "notified"},
                )
                is False
            )
        service.client.table.assert_not_called()

    @pytest.mark.asyncio
    async def test_storage_failure_never_raises(self):
        """A down database must not break the call (email already went out)."""
        service = CallbackEscalationService(client=_chain_client(explode=True))
        with patch(
            "shared.voice_agents.callback_service.callback_escalation_service",
            service,
        ):
            stored = await record_callback_tool_outcome(
                context=_context(),
                function_name="request_human_callback",
                arguments={
                    "callback_phone": "+14805550100",
                    "reason": "Billing.",
                },
                result={"status": "notified", "notified": True},
            )
        assert stored is False


class TestListForOrganization:
    @pytest.mark.asyncio
    async def test_lists_newest_first_rows(self):
        """Dashboard reads return stored rows in query order."""
        service = CallbackEscalationService(
            client=_chain_client([_stored_row(), _stored_row()])
        )
        rows = await service.list_for_organization(organization_id=ORG_ID)
        assert len(rows) == 2
        assert rows[0]["caller_phone"] == "+14805550100"
        service.client.table.assert_called_with("callback_escalations")
