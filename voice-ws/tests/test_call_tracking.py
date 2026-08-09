"""Tests for call finalization, duration capture, and credit linkage."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from src.call_tracking import end_call_tracking, start_call_tracking


class _Query:
    """Small Supabase query double that records updates and inserts."""

    def __init__(self, client: "_Client", table: str):
        self.client = client
        self.table = table
        self.operation = "select"
        self.payload = None

    def select(self, *_args, **_kwargs):
        self.operation = "select"
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def update(self, payload):
        self.operation = "update"
        self.payload = payload
        return self

    def insert(self, payload):
        self.operation = "insert"
        self.payload = payload
        return self

    def execute(self):
        if self.operation == "select" and self.table == "call_logs":
            return _Result(
                [
                    {
                        "id": "existing-call-log",
                        "call_sid": "CA123",
                        "organization_id": str(self.client.organization_id),
                        "started_at": self.client.started_at.isoformat(),
                    }
                ]
            )
        if self.operation == "select" and self.table == "credit_events":
            return _Result(
                [
                    {
                        "id": str(self.client.event_id),
                        "credit_cost": 10,
                    }
                ]
            )
        if self.operation == "insert" and self.table == "credit_transactions":
            self.client.transaction_payload = self.payload
            return _Result([{"id": str(self.client.transaction_id)}])
        if self.operation == "insert" and self.table == "call_logs":
            self.client.inserts.append(self.payload)
            return _Result([])
        if self.operation == "update":
            self.client.updates.append((self.table, self.payload))
        return _Result([])


class _Rpc:
    def __init__(self, client: "_Client"):
        self.client = client

    def execute(self):
        self.client.rpc_payload = self.client.rpc_args
        return _Result(
            {
                "success": True,
                "balance_after": 80,
                "plan_used": 20,
                "purchased_used": 0,
                "transaction_id": str(self.client.transaction_id),
            }
        )


class _Result:
    def __init__(self, data):
        self.data = data


class _Client:
    def __init__(self):
        self.organization_id = uuid4()
        self.event_id = uuid4()
        self.transaction_id = uuid4()
        self.started_at = datetime.now(timezone.utc) - timedelta(seconds=61)
        self.updates = []
        self.inserts = []
        self.rpc_args = None
        self.rpc_payload = None

    def table(self, table: str):
        return _Query(self, table)

    def rpc(self, *_args, **_kwargs):
        self.rpc_args = _kwargs or (_args[1] if len(_args) > 1 else {})
        return _Rpc(self)


@pytest.mark.asyncio
async def test_start_call_tracking_reuses_existing_twilio_call_log():
    """PSTN sessions reuse the backend row instead of creating a duplicate."""
    client = _Client()

    from src import call_tracking

    original_client = call_tracking.supabase_config._client
    call_tracking.supabase_config._client = client
    try:
        call_log_id = await start_call_tracking(
            session_id="voice-session-1",
            call_sid="CA123",
            organization_id=client.organization_id,
            agent_id=uuid4(),
        )
    finally:
        call_tracking.supabase_config._client = original_client

    assert call_log_id == "existing-call-log"
    assert client.inserts == []


@pytest.mark.asyncio
async def test_end_call_tracking_records_duration_and_credit_transaction():
    """A completed call is linked to its metered credit transaction."""
    client = _Client()

    from src import call_tracking

    original_client = call_tracking.supabase_config._client
    call_tracking.supabase_config._client = client
    try:
        await end_call_tracking("call-log-1")
    finally:
        call_tracking.supabase_config._client = original_client

    assert client.rpc_payload["p_credits_needed"] == 20
    assert client.rpc_payload["p_call_log_id"] == "call-log-1"
    assert any(
        payload.get("credits_consumed") == 20
        for table, payload in client.updates
        if table == "call_logs"
    )
    duration_updates = [
        payload
        for table, payload in client.updates
        if table == "call_logs" and "duration" in payload
    ]
    assert duration_updates[0]["duration"] >= 60
