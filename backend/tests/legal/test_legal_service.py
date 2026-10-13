"""Tests for the legal document versioning service.

Covers the draft/publish lifecycle contract and acceptance capture:

- Drafts copy the current published content as a baseline and are unique per
  document key.
- Publishing demotes the predecessor before promoting the draft so the
  single-current partial unique index is never violated.
- Publish optionally enqueues one durable outbox row per pre-existing user;
  enqueue failure never fails the publish.
- Acceptance rows are idempotent on ``(user_id, document_key, version_number)``
  and skip documents without a published version.
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from src.legal.models import LegalPublishRequest
from src.legal.service import (
    ACCEPTANCES_TABLE,
    LEGAL_DOCUMENT_TITLES,
    OUTBOX_TABLE,
    PUBLISH_EVENTS_TABLE,
    VERSIONS_TABLE,
    LegalDocumentService,
)

TEST_USER_ID = UUID("00000000-0000-0000-0000-000000000009")
TEST_ADMIN_ID = UUID("00000000-0000-0000-0000-000000000010")


class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    """Chainable query builder mimicking the Supabase fluent API."""

    def __init__(self, table: "_FakeTable") -> None:
        self._table = table
        self._op = "select"
        self._payload = None
        self._filters: list[tuple[str, str, object]] = []
        self._order = None
        self._desc = False
        self._limit = None
        self._single = False
        self._upsert_kwargs: dict = {}

    def select(self, _columns: str = "*"):
        self._op = "select"
        return self

    def insert(self, payload):
        self._op = "insert"
        self._payload = payload
        return self

    def update(self, fields):
        self._op = "update"
        self._payload = fields
        return self

    def delete(self):
        self._op = "delete"
        return self

    def upsert(self, payload, **kwargs):
        self._op = "upsert"
        self._payload = payload
        self._upsert_kwargs = kwargs
        return self

    def eq(self, column, value):
        self._filters.append(("eq", column, value))
        return self

    def is_(self, column, value):
        self._filters.append(("is_", column, value))
        return self

    def order(self, column, desc: bool = False):
        self._order = column
        self._desc = desc
        return self

    def limit(self, count: int):
        self._limit = count
        return self

    def single(self):
        self._single = True
        return self

    def _matches(self, row) -> bool:
        for op, column, value in self._filters:
            if op == "eq":
                if row.get(column) != value:
                    return False
            elif op == "is_":
                if value == "null" and row.get(column) is not None:
                    return False
        return True

    def execute(self) -> _Result:
        return self._table.run(self)


class _FakeTable:
    """In-memory table recording writes for assertions."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.rows: list[dict] = []
        self.ops: list[tuple] = []
        self.raise_on_insert: Exception | None = None

    def query(self) -> _Query:
        return _Query(self)

    def run(self, query: _Query) -> _Result:
        self.ops.append(
            (
                query._op,
                query._payload,
                list(query._filters),
                dict(query._upsert_kwargs),
            )
        )
        if query._op == "select":
            rows = [row for row in self.rows if query._matches(row)]
            if query._order:
                rows.sort(key=lambda row: row.get(query._order), reverse=query._desc)
            if query._limit is not None:
                rows = rows[: query._limit]
            if query._single:
                return _Result(rows[0] if rows else None)
            return _Result(rows)
        if query._op == "insert":
            if self.raise_on_insert is not None:
                raise self.raise_on_insert
            payloads = (
                query._payload if isinstance(query._payload, list) else [query._payload]
            )
            inserted = []
            for payload in payloads:
                row = dict(payload)
                row.setdefault("id", str(uuid4()))
                self.rows.append(row)
                inserted.append(dict(row))
            return _Result(inserted)
        if query._op == "update":
            matched = [row for row in self.rows if query._matches(row)]
            for row in matched:
                row.update(query._payload)
            return _Result([dict(row) for row in matched])
        if query._op == "delete":
            matched = [row for row in self.rows if query._matches(row)]
            self.rows = [row for row in self.rows if not query._matches(row)]
            return _Result([dict(row) for row in matched])
        if query._op == "upsert":
            payloads = (
                query._payload if isinstance(query._payload, list) else [query._payload]
            )
            affected = []
            for payload in payloads:
                existing = next(
                    (
                        row
                        for row in self.rows
                        if row.get("user_id") == payload.get("user_id")
                        and row.get("document_key") == payload.get("document_key")
                        and row.get("version_number") == payload.get("version_number")
                    ),
                    None,
                )
                if existing is not None and query._upsert_kwargs.get(
                    "ignore_duplicates"
                ):
                    continue
                row = dict(payload)
                row.setdefault("id", str(uuid4()))
                self.rows.append(row)
                affected.append(dict(row))
            return _Result(affected)
        raise AssertionError(f"unknown op {query._op}")


class _FakeAuthAdmin:
    def __init__(self) -> None:
        self.users: list = []
        self.raise_on_list: Exception | None = None
        self.calls: list[tuple[int, int]] = []

    def list_users(self, *, page: int, per_page: int):
        self.calls.append((page, per_page))
        if self.raise_on_list is not None:
            raise self.raise_on_list
        return SimpleNamespace(users=list(self.users))


class FakeSupabase:
    """Fake Supabase client routing table access to in-memory tables."""

    def __init__(self) -> None:
        self.tables = {
            VERSIONS_TABLE: _FakeTable(VERSIONS_TABLE),
            PUBLISH_EVENTS_TABLE: _FakeTable(PUBLISH_EVENTS_TABLE),
            ACCEPTANCES_TABLE: _FakeTable(ACCEPTANCES_TABLE),
            OUTBOX_TABLE: _FakeTable(OUTBOX_TABLE),
        }
        self.auth = SimpleNamespace(admin=_FakeAuthAdmin())

    def table(self, name: str) -> _Query:
        return self.tables[name].query()


def _make_service(client: FakeSupabase) -> LegalDocumentService:
    service = LegalDocumentService()
    service._supabase_config = SimpleNamespace(service_client=client, client=client)
    return service


def _user(user_id, email, created_at, *, first_name="Ada", last_name="Lovelace"):
    return SimpleNamespace(
        id=str(user_id),
        email=email,
        created_at=created_at,
        user_metadata={"first_name": first_name, "last_name": last_name},
    )


def _published_row(document_key="terms", version_number=1, content="# v1"):
    return {
        "id": str(uuid4()),
        "document_key": document_key,
        "version_number": version_number,
        "status": "published",
        "content_markdown": content,
        "summary_of_changes": None,
        "is_current": True,
        "published_at": datetime.now(timezone.utc).isoformat(),
        "published_by": str(TEST_ADMIN_ID),
        "created_by": str(TEST_ADMIN_ID),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def _draft_row(document_key="terms", version_number=2, content="# draft"):
    row = _published_row(document_key, version_number, content)
    row.update(
        {
            "status": "draft",
            "is_current": False,
            "published_at": None,
            "published_by": None,
        }
    )
    return row


@pytest.fixture
def client() -> FakeSupabase:
    return FakeSupabase()


@pytest.fixture
def service(client: FakeSupabase) -> LegalDocumentService:
    return _make_service(client)


class TestDraftLifecycle:
    @pytest.mark.asyncio
    async def test_create_draft_copies_current_published_content(self, client, service):
        current = _published_row(content="# published baseline")
        client.tables[VERSIONS_TABLE].rows.append(current)

        created = await service.create_draft("terms", created_by=TEST_ADMIN_ID)

        assert created.content_markdown == "# published baseline"
        assert created.version_number == 2
        assert created.status.value == "draft"
        assert created.is_current is False
        assert created.created_by == TEST_ADMIN_ID

    @pytest.mark.asyncio
    async def test_create_draft_without_current_starts_empty(self, service):
        created = await service.create_draft("terms", content_markdown=None)
        assert created.content_markdown == ""
        assert created.version_number == 1

    @pytest.mark.asyncio
    async def test_create_draft_rejects_second_open_draft(self, client, service):
        client.tables[VERSIONS_TABLE].rows.append(_draft_row())
        with pytest.raises(
            ValueError, match=r"draft version of 'terms' already exists"
        ):
            await service.create_draft("terms", content_markdown="# dup")

    @pytest.mark.asyncio
    async def test_update_draft_rejects_published_version(self, client, service):
        published = _published_row()
        client.tables[VERSIONS_TABLE].rows.append(published)
        with pytest.raises(ValueError, match="is not a draft"):
            await service.update_draft(UUID(published["id"]), content_markdown="# nope")

    @pytest.mark.asyncio
    async def test_update_draft_missing_version_mentions_not_found(self, service):
        with pytest.raises(ValueError, match="not found"):
            await service.update_draft(uuid4(), content_markdown="# nope")

    @pytest.mark.asyncio
    async def test_delete_draft_rejects_published_version(self, client, service):
        published = _published_row()
        client.tables[VERSIONS_TABLE].rows.append(published)
        with pytest.raises(ValueError, match="is not a draft"):
            await service.delete_draft(UUID(published["id"]))

    @pytest.mark.asyncio
    async def test_delete_draft_removes_draft_row(self, client, service):
        draft = _draft_row()
        client.tables[VERSIONS_TABLE].rows.append(draft)
        await service.delete_draft(UUID(draft["id"]))
        assert client.tables[VERSIONS_TABLE].rows == []


class TestPublish:
    @pytest.mark.asyncio
    async def test_publish_demotes_predecessor_then_promotes_draft(
        self, client, service
    ):
        previous = _published_row(version_number=1)
        draft = _draft_row(version_number=2, content="# v2")
        client.tables[VERSIONS_TABLE].rows.extend([previous, draft])

        result = await service.publish_version(
            UUID(draft["id"]), LegalPublishRequest(notify_users=False), TEST_ADMIN_ID
        )

        prev_after = client.tables[VERSIONS_TABLE].rows[0]
        draft_after = client.tables[VERSIONS_TABLE].rows[1]
        assert prev_after["is_current"] is False
        assert prev_after["status"] == "deprecated"
        assert draft_after["is_current"] is True
        assert draft_after["status"] == "published"
        assert result.version.status.value == "published"
        assert result.version.is_current is True

        # Demotion happens before promotion to honor the single-current index.
        version_ops = client.tables[VERSIONS_TABLE].ops
        update_targets = [op[1] for op in version_ops if op[0] == "update"]
        assert update_targets[0] == {
            "is_current": False,
            "status": "deprecated",
            "updated_at": update_targets[0]["updated_at"],
        }
        assert update_targets[1]["status"] == "published"
        assert update_targets[1]["is_current"] is True

    @pytest.mark.asyncio
    async def test_publish_without_notify_skips_outbox(self, client, service):
        draft = _draft_row()
        client.tables[VERSIONS_TABLE].rows.append(draft)

        result = await service.publish_version(
            UUID(draft["id"]), LegalPublishRequest(notify_users=False), TEST_ADMIN_ID
        )

        assert result.notified_count == 0
        assert result.dispatch_id is None
        assert client.tables[OUTBOX_TABLE].rows == []
        events = client.tables[PUBLISH_EVENTS_TABLE].rows
        assert len(events) == 1
        assert events[0]["notify_users"] is False
        assert events[0]["notified_count"] == 0
        assert events[0]["dispatch_id"] is None
        assert events[0]["previous_legal_document_version_id"] is None
        assert result.publish_event_id == UUID(events[0]["id"])

    @pytest.mark.asyncio
    async def test_publish_enqueues_one_row_per_eligible_user(self, client, service):
        draft = _draft_row(version_number=3, content="# v3")
        draft["summary_of_changes"] = "Clarified retention"
        client.tables[VERSIONS_TABLE].rows.append(draft)
        cutoff = datetime.now(timezone.utc)
        client.auth.admin.users = [
            _user(uuid4(), "old@example.com", (cutoff - timedelta(days=2)).isoformat()),
            _user(uuid4(), "new@example.com", (cutoff + timedelta(days=1)).isoformat()),
            _user(uuid4(), None, (cutoff - timedelta(days=1)).isoformat()),
        ]

        result = await service.publish_version(
            UUID(draft["id"]), LegalPublishRequest(notify_users=True), TEST_ADMIN_ID
        )

        outbox = client.tables[OUTBOX_TABLE].rows
        assert len(outbox) == 1
        assert result.notified_count == 1
        row = outbox[0]
        assert row["recipient_email"] == "old@example.com"
        assert row["recipient_name"] == "Ada Lovelace"
        assert row["summary_of_changes"] == "Clarified retention"
        assert row["document_key"] == "terms"
        assert row["version_number"] == 3
        assert row["legal_document_version_id"] == draft["id"]
        assert result.dispatch_id is not None
        assert row["dispatch_id"] == str(result.dispatch_id)
        assert client.tables[PUBLISH_EVENTS_TABLE].rows[0]["notified_count"] == 1
        assert client.tables[PUBLISH_EVENTS_TABLE].rows[0]["dispatch_id"] == str(
            result.dispatch_id
        )

    @pytest.mark.asyncio
    async def test_outbox_insert_failure_does_not_fail_publish(self, client, service):
        draft = _draft_row()
        client.tables[VERSIONS_TABLE].rows.append(draft)
        client.auth.admin.users = [
            _user(uuid4(), "user@example.com", "2020-01-01T00:00:00+00:00")
        ]
        client.tables[OUTBOX_TABLE].raise_on_insert = RuntimeError("outbox down")

        result = await service.publish_version(
            UUID(draft["id"]), LegalPublishRequest(notify_users=True), TEST_ADMIN_ID
        )

        assert result.notified_count == 0
        assert result.dispatch_id is not None
        events = client.tables[PUBLISH_EVENTS_TABLE].rows
        assert len(events) == 1
        assert events[0]["notified_count"] == 0
        assert events[0]["notify_users"] is True


class TestRecordUserAcceptance:
    @pytest.mark.asyncio
    async def test_records_one_row_per_published_document(self, client, service):
        terms = _published_row("terms", 1)
        privacy = _published_row("privacy", 2)
        client.tables[VERSIONS_TABLE].rows.extend([terms, privacy])

        created = await service.record_user_acceptance(
            TEST_USER_ID,
            source="signup",
            user_agent="Mozilla/5.0",
            ip_address="203.0.113.9",
        )

        assert created == 2
        rows = client.tables[ACCEPTANCES_TABLE].rows
        assert {row["document_key"] for row in rows} == set(LEGAL_DOCUMENT_TITLES)
        for row in rows:
            assert row["user_id"] == str(TEST_USER_ID)
            assert row["source"] == "signup"
            assert row["user_agent"] == "Mozilla/5.0"
            assert row["ip_address"] == "203.0.113.9"
        by_key = {row["document_key"]: row for row in rows}
        assert by_key["terms"]["legal_document_version_id"] == terms["id"]
        assert by_key["terms"]["version_number"] == 1
        assert by_key["privacy"]["legal_document_version_id"] == privacy["id"]
        assert by_key["privacy"]["version_number"] == 2

    @pytest.mark.asyncio
    async def test_skips_documents_without_published_version(self, client, service):
        client.tables[VERSIONS_TABLE].rows.append(_published_row("terms", 1))

        created = await service.record_user_acceptance(TEST_USER_ID, source="oauth")

        assert created == 1
        rows = client.tables[ACCEPTANCES_TABLE].rows
        assert [row["document_key"] for row in rows] == ["terms"]
        assert rows[0]["source"] == "oauth"

    @pytest.mark.asyncio
    async def test_acceptance_upsert_is_idempotent_on_user_key_version(
        self, client, service
    ):
        client.tables[VERSIONS_TABLE].rows.append(_published_row("terms", 1))

        first = await service.record_user_acceptance(TEST_USER_ID, source="signup")
        second = await service.record_user_acceptance(TEST_USER_ID, source="signup")

        assert (first, second) == (1, 0)
        assert len(client.tables[ACCEPTANCES_TABLE].rows) == 1
        upserts = [
            op for op in client.tables[ACCEPTANCES_TABLE].ops if op[0] == "upsert"
        ]
        assert upserts, "acceptance capture must go through upsert"
        for _op, _payload, _filters, kwargs in upserts:
            assert kwargs["on_conflict"] == "user_id,document_key,version_number"
            assert kwargs["ignore_duplicates"] is True

    @pytest.mark.asyncio
    async def test_no_published_documents_returns_zero(self, service):
        created = await service.record_user_acceptance(TEST_USER_ID, source="signup")
        assert created == 0

    @pytest.mark.asyncio
    async def test_upsert_failure_for_one_key_does_not_abort_the_rest(
        self, client, service, monkeypatch
    ):
        terms = _published_row("terms", 1)
        privacy = _published_row("privacy", 1)
        client.tables[VERSIONS_TABLE].rows.extend([terms, privacy])

        original_run = type(client.tables[ACCEPTANCES_TABLE]).run
        calls = {"count": 0}

        def flaky_run(table, query):
            if query._op == "upsert":
                calls["count"] += 1
                if calls["count"] == 1:
                    raise RuntimeError("write failed")
            return original_run(table, query)

        monkeypatch.setattr(type(client.tables[ACCEPTANCES_TABLE]), "run", flaky_run)
        created = await service.record_user_acceptance(TEST_USER_ID, source="oauth")

        assert created == 1
        assert [
            row["document_key"] for row in client.tables[ACCEPTANCES_TABLE].rows
        ] == ["privacy"]
