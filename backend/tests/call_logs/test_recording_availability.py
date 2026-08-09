"""Tests for recording availability enrichment on call-log responses."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.call_logs.service import CallLogService


class _Result:
    """Minimal PostgREST result object."""

    def __init__(self, data, count=None):
        self.data = data
        self.count = count


class _Query:
    """Query double for call-log and artifact availability reads."""

    def __init__(self, client, table):
        self.client = client
        self.table = table

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def range(self, *_args, **_kwargs):
        return self

    def in_(self, *_args, **_kwargs):
        return self

    def execute(self):
        if self.table == "call_artifacts" and self.client.fail_artifacts:
            raise RuntimeError("call_artifacts table is unavailable")
        if self.table == "call_artifacts":
            return _Result([{"call_log_id": str(self.client.call_id)}])
        return _Result([self.client.call_row], count=1)


class _Client:
    """Supabase client double for availability enrichment."""

    def __init__(self, fail_artifacts=False):
        self.call_id = uuid4()
        self.fail_artifacts = fail_artifacts
        now = datetime.now(timezone.utc).isoformat()
        self.call_row = {
            "id": str(self.call_id),
            "call_sid": "CA-recording",
            "organization_id": str(uuid4()),
            "agent_id": None,
            "caller_number": None,
            "called_number": None,
            "status": "completed",
            "duration": 10,
            "credits_consumed": 10,
            "credit_transaction_id": None,
            "started_at": now,
            "ended_at": now,
            "created_at": now,
            "updated_at": now,
        }

    def table(self, table):
        return _Query(self, table)


@pytest.mark.asyncio
async def test_list_call_logs_marks_completed_recordings_available():
    """Completed recording artifacts produce a Listen-capable call row."""
    client = _Client()
    from shared.config import supabase_config

    original_client = supabase_config._client
    supabase_config._client = client
    try:
        result, error = await CallLogService().list_call_logs(
            organization_id=uuid4(), page=1, page_size=25
        )
    finally:
        supabase_config._client = original_client

    assert error is None
    assert result.items[0].recording_available is True


@pytest.mark.asyncio
async def test_list_call_logs_fails_closed_when_artifact_table_is_unavailable():
    """Older environments remain usable while the artifact migration is pending."""
    client = _Client(fail_artifacts=True)
    from shared.config import supabase_config

    original_client = supabase_config._client
    supabase_config._client = client
    try:
        result, error = await CallLogService().list_call_logs(
            organization_id=uuid4(), page=1, page_size=25
        )
    finally:
        supabase_config._client = original_client

    assert error is None
    assert result.items[0].recording_available is False
