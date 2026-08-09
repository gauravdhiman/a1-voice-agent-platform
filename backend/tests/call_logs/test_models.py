"""Regression tests for call-log data compatibility."""

from datetime import datetime, timezone
from uuid import uuid4

from src.call_logs.models import CallLog


def test_call_log_accepts_legacy_rows_without_duration() -> None:
    """Legacy call rows with an unknown duration remain reportable."""
    now = datetime.now(timezone.utc)
    call_log = CallLog(
        id=uuid4(),
        call_sid="CAlegacy",
        organization_id=uuid4(),
        agent_id=None,
        caller_number="+15555550100",
        called_number="+15555550101",
        status="completed",
        duration=None,
        started_at=now,
        ended_at=None,
        created_at=now,
        updated_at=now,
    )

    assert call_log.duration is None
