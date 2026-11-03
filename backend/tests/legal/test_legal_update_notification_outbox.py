"""Tests for the legal document update notification outbox.

Pins the durable-delivery contract:

- Successful sends mark the row processed and clear ``last_error``.
- Failed sends stay retryable and record a truncated ``last_error``.
- Rows exhausted at ``MAX_ATTEMPTS`` are skipped for ops, never dropped.
- Retry claims are serialized on ``last_attempt_at`` and gated by bounded
  exponential backoff.
- The outgoing notification request carries the documented template variables
  and a per-user idempotency key.
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from src.legal.update_outbox import (
    DOCUMENT_URL_PATHS,
    EVENT_KEY,
    MAX_ATTEMPTS,
    OUTBOX_TABLE,
    LegalUpdateNotificationOutbox,
)

TEST_USER_ID = UUID("00000000-0000-0000-0000-000000000081")
TEST_VERSION_ID = UUID("00000000-0000-0000-0000-000000000082")


class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, table: "_FakeOutboxTable") -> None:
        self._table = table
        self._op = "select"
        self._payload = None
        self._filters: list[tuple] = []
        self._limit = None

    def select(self, _columns="*"):
        self._op = "select"
        return self

    def update(self, fields):
        self._op = "update"
        self._payload = fields
        return self

    def eq(self, column, value):
        self._filters.append(("eq", column, value))
        return self

    def is_(self, column, value):
        self._filters.append(("is_", column, value))
        return self

    def order(self, _column, desc: bool = False):
        return self

    def limit(self, count: int):
        self._limit = count
        return self

    def _matches(self, row) -> bool:
        for op, column, value in self._filters:
            if op == "eq" and row.get(column) != value:
                return False
            if op == "is_" and value == "null" and row.get(column) is not None:
                return False
        return True

    def execute(self) -> _Result:
        self._table.ops.append(
            (self._op, self._payload, list(self._filters), self._limit)
        )
        if self._op == "select":
            if self._table.raise_on_select is not None:
                raise self._table.raise_on_select
            rows = [row for row in self._table.rows if self._matches(row)]
            rows.sort(key=lambda row: str(row.get("created_at")))
            if self._limit is not None:
                rows = rows[: self._limit]
            return _Result([dict(row) for row in rows])
        if self._op == "update":
            if self._table.lose_claim and any(
                f[1] == "last_attempt_at" for f in self._filters
            ):
                return _Result([])
            matched = [row for row in self._table.rows if self._matches(row)]
            for row in matched:
                row.update(self._payload)
            return _Result([dict(row) for row in matched])
        raise AssertionError(f"unknown op {self._op}")


class _FakeOutboxTable:
    def __init__(self) -> None:
        self.rows: list[dict] = []
        self.ops: list[tuple] = []
        self.raise_on_select: Exception | None = None
        self.lose_claim = False

    def query(self) -> _Query:
        return _Query(self)


class FakeSupabase:
    def __init__(self) -> None:
        self.outbox = _FakeOutboxTable()

    def table(self, name: str) -> _Query:
        assert name == OUTBOX_TABLE
        return self.outbox.query()


def _make_outbox(client: FakeSupabase) -> LegalUpdateNotificationOutbox:
    return LegalUpdateNotificationOutbox(
        supabase_config_override=SimpleNamespace(service_client=client, client=client)
    )


def _row(**overrides) -> dict:
    now = datetime.now(timezone.utc)
    row = {
        "id": str(uuid4()),
        "dispatch_id": str(uuid4()),
        "legal_document_version_id": str(TEST_VERSION_ID),
        "document_key": "terms",
        "version_number": 2,
        "user_id": str(TEST_USER_ID),
        "recipient_email": "user@example.com",
        "recipient_name": "Ada Lovelace",
        "summary_of_changes": "Clarified retention",
        "attempt_count": 0,
        "last_attempt_at": None,
        "last_error": None,
        "created_at": (now - timedelta(minutes=1)).isoformat(),
        "processed_at": None,
    }
    row.update(overrides)
    return row


def _response(success: bool, message: str = "") -> SimpleNamespace:
    return SimpleNamespace(success=success, message=message)


@pytest.fixture
def client() -> FakeSupabase:
    return FakeSupabase()


@pytest.fixture
def outbox(client: FakeSupabase) -> LegalUpdateNotificationOutbox:
    return _make_outbox(client)


class TestProcessPendingSuccess:
    @pytest.mark.asyncio
    async def test_success_marks_row_processed_and_counts(self, client, outbox):
        row = _row()
        client.outbox.rows.append(row)

        with patch(
            "src.legal.update_outbox.notification_service"
        ) as mock_notifications, patch(
            "src.legal.update_outbox.settings"
        ) as mock_settings:
            mock_settings.app_base_url = "https://app.example.com"
            mock_notifications.send_notification = AsyncMock(
                return_value=_response(True)
            )
            summary = await outbox.process_pending()

        assert summary == {"claimed": 1, "succeeded": 1, "failed": 0, "skipped": 0}
        stored = client.outbox.rows[0]
        assert stored["processed_at"] is not None
        assert stored["last_error"] is None
        assert stored["attempt_count"] == 1
        assert stored["last_attempt_at"] is not None

    @pytest.mark.asyncio
    async def test_process_pending_respects_limit(self, client, outbox):
        client.outbox.rows.append(_row(created_at="2026-10-12T00:00:00+00:00"))
        client.outbox.rows.append(_row(created_at="2026-10-12T00:01:00+00:00"))

        with patch(
            "src.legal.update_outbox.notification_service"
        ) as mock_notifications, patch(
            "src.legal.update_outbox.settings"
        ) as mock_settings:
            mock_settings.app_base_url = "https://app.example.com"
            mock_notifications.send_notification = AsyncMock(
                return_value=_response(True)
            )
            summary = await outbox.process_pending(limit=1)

        assert summary["succeeded"] == 1
        assert sum(1 for row in client.outbox.rows if row["processed_at"]) == 1

    @pytest.mark.asyncio
    async def test_select_failure_is_reported(self, client, outbox):
        client.outbox.raise_on_select = RuntimeError("db down")
        summary = await outbox.process_pending()
        assert summary == {"claimed": 0, "succeeded": 0, "failed": 1, "skipped": 0}


class TestProcessPendingFailures:
    @pytest.mark.asyncio
    async def test_send_failure_records_truncated_error_and_keeps_row_pending(
        self, client, outbox
    ):
        client.outbox.rows.append(_row())

        with patch(
            "src.legal.update_outbox.notification_service"
        ) as mock_notifications, patch(
            "src.legal.update_outbox.settings"
        ) as mock_settings:
            mock_settings.app_base_url = "https://app.example.com"
            mock_notifications.send_notification = AsyncMock(
                return_value=_response(False, "x" * 1500)
            )
            summary = await outbox.process_pending()

        assert summary == {"claimed": 1, "succeeded": 0, "failed": 1, "skipped": 0}
        stored = client.outbox.rows[0]
        assert stored["processed_at"] is None
        assert stored["last_error"] == ("x" * 1500)[:1000]
        assert stored["attempt_count"] == 1

    @pytest.mark.asyncio
    async def test_send_exception_is_treated_as_retryable_failure(self, client, outbox):
        client.outbox.rows.append(_row())

        with patch(
            "src.legal.update_outbox.notification_service"
        ) as mock_notifications, patch(
            "src.legal.update_outbox.settings"
        ) as mock_settings:
            mock_settings.app_base_url = "https://app.example.com"
            mock_notifications.send_notification = AsyncMock(
                side_effect=RuntimeError("smtp exploded")
            )
            summary = await outbox.process_pending()

        assert summary["failed"] == 1
        assert client.outbox.rows[0]["last_error"] == "smtp exploded"

    @pytest.mark.asyncio
    async def test_exhausted_retries_are_skipped_for_ops(self, client, outbox):
        client.outbox.rows.append(
            _row(attempt_count=MAX_ATTEMPTS, last_error="still broken")
        )

        with patch(
            "src.legal.update_outbox.notification_service"
        ) as mock_notifications:
            mock_notifications.send_notification = AsyncMock()
            summary = await outbox.process_pending()

        assert summary == {"claimed": 0, "succeeded": 0, "failed": 0, "skipped": 1}
        mock_notifications.send_notification.assert_not_awaited()
        stored = client.outbox.rows[0]
        assert stored["processed_at"] is None
        assert stored["attempt_count"] == MAX_ATTEMPTS


class TestClaimContract:
    @pytest.mark.asyncio
    async def test_backoff_gate_skips_recent_attempt(self, client, outbox):
        recent = datetime.now(timezone.utc) - timedelta(seconds=5)
        client.outbox.rows.append(
            _row(attempt_count=1, last_attempt_at=recent.isoformat())
        )

        with patch(
            "src.legal.update_outbox.notification_service"
        ) as mock_notifications:
            mock_notifications.send_notification = AsyncMock()
            summary = await outbox.process_pending()

        assert summary["skipped"] == 1
        assert summary["claimed"] == 0
        mock_notifications.send_notification.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_backoff_escalates_with_attempt_count(self, client, outbox):
        """attempt_count=4 backs off 60*2^4=960s: 800s-old waits, 1000s-old runs."""
        now = datetime.now(timezone.utc)
        waiting = _row(
            attempt_count=4, last_attempt_at=(now - timedelta(seconds=800)).isoformat()
        )
        due = _row(
            attempt_count=4, last_attempt_at=(now - timedelta(seconds=1000)).isoformat()
        )
        client.outbox.rows.extend([waiting, due])

        with patch(
            "src.legal.update_outbox.notification_service"
        ) as mock_notifications, patch(
            "src.legal.update_outbox.settings"
        ) as mock_settings:
            mock_settings.app_base_url = "https://app.example.com"
            mock_notifications.send_notification = AsyncMock(
                return_value=_response(True)
            )
            summary = await outbox.process_pending()

        assert summary == {"claimed": 1, "succeeded": 1, "failed": 0, "skipped": 1}
        by_state = {row["id"]: row for row in client.outbox.rows}
        assert by_state[waiting["id"]]["attempt_count"] == 4
        assert by_state[waiting["id"]]["processed_at"] is None
        assert by_state[due["id"]]["attempt_count"] == 5
        assert by_state[due["id"]]["processed_at"] is not None

    @pytest.mark.asyncio
    async def test_claim_uses_null_guard_for_fresh_rows(self, client, outbox):
        client.outbox.rows.append(_row(last_attempt_at=None))

        with patch(
            "src.legal.update_outbox.notification_service"
        ) as mock_notifications, patch(
            "src.legal.update_outbox.settings"
        ) as mock_settings:
            mock_settings.app_base_url = "https://app.example.com"
            mock_notifications.send_notification = AsyncMock(
                return_value=_response(True)
            )
            await outbox.process_pending()

        claim_ops = [
            op
            for op in client.outbox.ops
            if op[0] == "update" and any(f[1] == "last_attempt_at" for f in op[2])
        ]
        assert claim_ops, "claim must condition on last_attempt_at"
        assert ("is_", "last_attempt_at", "null") in claim_ops[0][2]

    @pytest.mark.asyncio
    async def test_claim_uses_expected_last_attempt_for_retry(self, client, outbox):
        prior = datetime.now(timezone.utc) - timedelta(hours=3)
        prior_iso = prior.isoformat()
        client.outbox.rows.append(_row(attempt_count=2, last_attempt_at=prior_iso))

        with patch(
            "src.legal.update_outbox.notification_service"
        ) as mock_notifications, patch(
            "src.legal.update_outbox.settings"
        ) as mock_settings:
            mock_settings.app_base_url = "https://app.example.com"
            mock_notifications.send_notification = AsyncMock(
                return_value=_response(True)
            )
            await outbox.process_pending()

        claim_ops = [
            op
            for op in client.outbox.ops
            if op[0] == "update" and any(f[1] == "last_attempt_at" for f in op[2])
        ]
        assert claim_ops
        assert ("eq", "last_attempt_at", prior_iso) in claim_ops[0][2]
        assert client.outbox.rows[0]["attempt_count"] == 3

    @pytest.mark.asyncio
    async def test_lost_claim_is_skipped_and_not_sent(self, client, outbox):
        client.outbox.rows.append(_row())
        client.outbox.lose_claim = True

        with patch(
            "src.legal.update_outbox.notification_service"
        ) as mock_notifications:
            mock_notifications.send_notification = AsyncMock()
            summary = await outbox.process_pending()

        assert summary == {"claimed": 0, "succeeded": 0, "failed": 0, "skipped": 1}
        mock_notifications.send_notification.assert_not_awaited()
        assert client.outbox.rows[0]["processed_at"] is None


class TestSendRowRequest:
    @pytest.mark.asyncio
    async def test_request_carries_template_variables_and_idempotency_key(self, outbox):
        row = _row()
        captured = {}

        async def capture(request):
            captured["request"] = request
            return _response(True)

        with patch(
            "src.legal.update_outbox.notification_service"
        ) as mock_notifications, patch(
            "src.legal.update_outbox.settings"
        ) as mock_settings:
            mock_settings.app_base_url = "https://app.example.com"
            mock_notifications.send_notification = AsyncMock(side_effect=capture)
            response = await outbox._send_row(row)

        assert response.success is True
        request = captured["request"]
        assert request.event_key == EVENT_KEY
        assert request.recipient_email == "user@example.com"
        assert request.recipient_name == "Ada Lovelace"
        assert request.user_id == TEST_USER_ID
        assert request.idempotency_key == f"legal:terms:2:{TEST_USER_ID}"
        assert request.template_variables == {
            "user_name": "Ada Lovelace",
            "document_title": "Terms & Conditions",
            "version_number": 2,
            "summary_of_changes": "Clarified retention",
            "document_url": f"https://app.example.com{DOCUMENT_URL_PATHS['terms']}",
        }
        assert request.log_metadata == {
            "document_key": "terms",
            "version_number": 2,
            "dispatch_id": row["dispatch_id"],
        }

    @pytest.mark.asyncio
    async def test_request_defaults_placeholders_for_missing_fields(self, outbox):
        row = _row(
            recipient_name=None,
            summary_of_changes=None,
            document_key="privacy",
            user_id=str(TEST_USER_ID),
        )
        captured = {}

        async def capture(request):
            captured["request"] = request
            return _response(True)

        with patch(
            "src.legal.update_outbox.notification_service"
        ) as mock_notifications, patch(
            "src.legal.update_outbox.settings"
        ) as mock_settings:
            mock_settings.app_base_url = "https://app.example.com"
            mock_notifications.send_notification = AsyncMock(side_effect=capture)
            await outbox._send_row(row)

        request = captured["request"]
        assert request.template_variables["user_name"] == "there"
        assert request.template_variables["summary_of_changes"] == (
            "See the updated document for details."
        )
        assert request.template_variables["document_title"] == "Privacy Policy"
        assert request.template_variables["document_url"] == (
            f"https://app.example.com{DOCUMENT_URL_PATHS['privacy']}"
        )
