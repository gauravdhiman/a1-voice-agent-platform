"""Tests for call-log failure preservation."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from src.call_logs.models import CallLogUpdate
from src.call_logs.service import CallLogService


@pytest.mark.asyncio
async def test_twilio_completion_does_not_clear_runtime_failure():
    """A late provider callback cannot hide a voice-ws failure marker."""
    organization_id = uuid4()
    agent_id = uuid4()
    now = datetime.now(timezone.utc).isoformat()
    updated_row = {
        "id": str(uuid4()),
        "call_sid": "CA123",
        "organization_id": str(organization_id),
        "agent_id": str(agent_id),
        "caller_number": None,
        "called_number": None,
        "status": "failed",
        "failure_code": "model_reasoning_required",
        "failure_message": "Review the voice preset configuration.",
        "duration": 12,
        "credits_consumed": 0,
        "credit_transaction_id": None,
        "started_at": now,
        "ended_at": now,
        "created_at": now,
        "updated_at": now,
    }

    query = MagicMock()
    query.select.return_value = query
    query.eq.return_value = query
    query.limit.return_value = query
    query.update.return_value = query
    query.is_.return_value = query
    query.execute.side_effect = [
        MagicMock(data=[]),
        MagicMock(
            data=[
                {
                    "id": updated_row["id"],
                    "failure_code": "model_reasoning_required",
                }
            ]
        ),
        MagicMock(data=[updated_row]),
    ]
    client = MagicMock()
    client.table.return_value = query

    with patch("src.call_logs.service.supabase_config") as config:
        config.client = client
        result, error = await CallLogService().update_call_log_by_sid(
            "CA123", CallLogUpdate(status="completed", duration=12)
        )

    assert error is None
    assert result is not None
    assert result.status == "failed"
    update_payload = query.update.call_args.args[0]
    assert update_payload["updated_at"]
    assert "status" not in update_payload
    assert "failure_code" not in update_payload
    query.is_.assert_called_with("failure_code", "null")


@pytest.mark.asyncio
async def test_twilio_completion_preserves_failure_written_during_retry():
    """A failure that wins during the conditional retry is still preserved."""
    organization_id = uuid4()
    agent_id = uuid4()
    now = datetime.now(timezone.utc).isoformat()
    updated_row = {
        "id": str(uuid4()),
        "call_sid": "CA456",
        "organization_id": str(organization_id),
        "agent_id": str(agent_id),
        "caller_number": None,
        "called_number": None,
        "status": "failed",
        "failure_code": "provider_authentication_error",
        "failure_message": "The provider rejected its credentials.",
        "duration": 12,
        "credits_consumed": 0,
        "credit_transaction_id": None,
        "started_at": now,
        "ended_at": now,
        "created_at": now,
        "updated_at": now,
    }

    query = MagicMock()
    query.select.return_value = query
    query.eq.return_value = query
    query.limit.return_value = query
    query.update.return_value = query
    query.is_.return_value = query
    query.execute.side_effect = [
        MagicMock(data=[]),
        MagicMock(data=[{"id": updated_row["id"], "failure_code": None}]),
        MagicMock(data=[]),
        MagicMock(
            data=[
                {
                    "id": updated_row["id"],
                    "failure_code": "provider_authentication_error",
                }
            ]
        ),
        MagicMock(data=[updated_row]),
    ]
    client = MagicMock()
    client.table.return_value = query

    with patch("src.call_logs.service.supabase_config") as config:
        config.client = client
        result, error = await CallLogService().update_call_log_by_sid(
            "CA456", CallLogUpdate(status="completed", duration=12)
        )

    assert error is None
    assert result is not None
    assert result.status == "failed"
    preserved_payload = query.update.call_args_list[-1].args[0]
    assert "status" not in preserved_payload
    assert "failure_code" not in preserved_payload
