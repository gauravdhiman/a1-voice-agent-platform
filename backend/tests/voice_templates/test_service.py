"""Unit tests for the voice-template service contract."""

from datetime import datetime, timezone
from unittest.mock import PropertyMock, patch
from uuid import UUID

import pytest

from src.voice_templates.models import VoiceTemplateCreate, VoiceTemplateUpdate
from src.voice_templates.service import VoiceTemplateService

TEMPLATE_ID = UUID("00000000-0000-0000-0000-000000000001")


def _row(*, active: bool = True) -> dict:
    """Return a Supabase-shaped voice template row."""
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": str(TEMPLATE_ID),
        "name": "Dental Receptionist",
        "industry": "dental",
        "description": "desc",
        "persona": None,
        "tone": "warm",
        "mission": "mission",
        "greeting": "hello",
        "custom_instructions": "# Procedures",
        "is_active": active,
        "created_at": now,
        "updated_at": now,
    }


class FakeQuery:
    """Minimal fluent Supabase query double for service tests."""

    def __init__(self, response_data: list[dict]):
        self.response_data = response_data
        self.calls: list[tuple[str, object, object]] = []

    def select(self, value: str):
        self.calls.append(("select", value, None))
        return self

    def eq(self, key: str, value: object):
        self.calls.append(("eq", key, value))
        return self

    def order(self, value: str):
        self.calls.append(("order", value, None))
        return self

    def insert(self, payload: dict):
        self.calls.append(("insert", payload, None))
        return self

    def update(self, payload: dict):
        self.calls.append(("update", payload, None))
        return self

    def delete(self):
        self.calls.append(("delete", None, None))
        return self

    def execute(self):
        return type("Response", (), {"data": self.response_data})()


class FakeSupabase:
    """Return a new query double for each table call."""

    def __init__(self, response_data: list[dict]):
        self.response_data = response_data
        self.queries: list[FakeQuery] = []

    def table(self, _: str) -> FakeQuery:
        query = FakeQuery(self.response_data)
        self.queries.append(query)
        return query


class ExplodingSupabase:
    """Supabase double that raises on every table access."""

    def table(self, _: str):
        raise RuntimeError("database unavailable")


def _with_supabase(supabase: FakeSupabase):
    """Patch the service property without requiring Supabase configuration."""
    return patch.object(
        VoiceTemplateService,
        "supabase",
        new_callable=PropertyMock,
        return_value=supabase,
    )


class TestVoiceTemplateService:
    """CRUD and public filtering behavior."""

    @pytest.mark.asyncio
    async def test_public_list_filters_inactive_rows(self):
        """The agent picker only receives active templates."""
        supabase = FakeSupabase([_row()])

        with _with_supabase(supabase):
            templates, error = await VoiceTemplateService().list_templates()

        assert error is None
        assert len(templates) == 1
        assert ("eq", "is_active", True) in supabase.queries[0].calls

    @pytest.mark.asyncio
    async def test_list_applies_industry_filter(self):
        """The public picker can narrow templates by industry."""
        supabase = FakeSupabase([_row()])

        with _with_supabase(supabase):
            templates, error = await VoiceTemplateService().list_templates(
                industry="dental"
            )

        assert error is None
        assert templates[0].industry == "dental"
        assert ("eq", "industry", "dental") in supabase.queries[0].calls

    @pytest.mark.asyncio
    async def test_get_template_returns_row_and_not_found(self):
        """Get returns a typed row and a stable missing-row message."""
        service = VoiceTemplateService()
        with _with_supabase(FakeSupabase([_row()])):
            template, error = await service.get_template_by_id(TEMPLATE_ID)
        assert template is not None
        assert error is None

        with _with_supabase(FakeSupabase([])):
            missing, missing_error = await service.get_template_by_id(TEMPLATE_ID)
        assert missing is None
        assert missing_error == "Voice template not found"

    @pytest.mark.asyncio
    async def test_admin_list_can_include_inactive_rows(self):
        """The admin catalog can inspect inactive templates."""
        supabase = FakeSupabase([_row(active=False)])

        with _with_supabase(supabase):
            templates, error = await VoiceTemplateService().list_templates(
                include_inactive=True
            )

        assert error is None
        assert templates[0].is_active is False
        assert ("eq", "is_active", True) not in supabase.queries[0].calls

    @pytest.mark.asyncio
    async def test_create_update_and_delete_return_errors_for_empty_results(self):
        """Empty database responses become stable service errors."""
        supabase = FakeSupabase([])
        service = VoiceTemplateService()

        with _with_supabase(supabase):
            created, create_error = await service.create_template(
                VoiceTemplateCreate(name="New", industry="dental")
            )
            updated, update_error = await service.update_template(
                TEMPLATE_ID,
                VoiceTemplateUpdate(description="Updated"),
            )
            deleted, delete_error = await service.delete_template(TEMPLATE_ID)

        assert created is None
        assert create_error == "Failed to create voice template"
        assert updated is None
        assert update_error == "Voice template not found"
        assert deleted is None
        assert delete_error == "Voice template not found"

    @pytest.mark.asyncio
    async def test_create_update_and_delete_persist_expected_rows(self):
        """Successful CRUD maps Supabase rows into typed responses."""
        supabase = FakeSupabase([_row()])
        service = VoiceTemplateService()

        with _with_supabase(supabase):
            created, create_error = await service.create_template(
                VoiceTemplateCreate(name="New", industry="dental")
            )
            updated, update_error = await service.update_template(
                TEMPLATE_ID,
                VoiceTemplateUpdate(description="Updated"),
            )
            deleted, delete_error = await service.delete_template(TEMPLATE_ID)

        assert created is not None
        assert create_error is None
        assert updated is not None
        assert update_error is None
        assert deleted is True
        assert delete_error is None
        all_calls = [call for query in supabase.queries for call in query.calls]
        assert any(call[0] == "insert" for call in all_calls)
        assert any(call[0] == "update" for call in all_calls)
        assert any(call[0] == "delete" for call in all_calls)

    @pytest.mark.asyncio
    async def test_database_exceptions_are_returned_as_errors(self):
        """Each CRUD operation converts database exceptions to service errors."""
        service = VoiceTemplateService()
        with _with_supabase(ExplodingSupabase()):
            listed, list_error = await service.list_templates()
            fetched, fetch_error = await service.get_template_by_id(TEMPLATE_ID)
            created, create_error = await service.create_template(
                VoiceTemplateCreate(name="New", industry="dental")
            )
            updated, update_error = await service.update_template(
                TEMPLATE_ID,
                VoiceTemplateUpdate(description="Updated"),
            )
            deleted, delete_error = await service.delete_template(TEMPLATE_ID)

        assert listed == [] and list_error == "database unavailable"
        assert fetched is None and fetch_error == "database unavailable"
        assert created is None and create_error == "database unavailable"
        assert updated is None and update_error == "database unavailable"
        assert deleted is None and delete_error == "database unavailable"

    @pytest.mark.asyncio
    async def test_unconfigured_supabase_is_reported(self):
        """The service reports missing local Supabase configuration."""
        service = VoiceTemplateService()
        with patch("src.voice_templates.service.supabase_config") as config:
            config.is_configured.return_value = False
            templates, error = await service.list_templates()

        assert templates == []
        assert error == "Supabase is not configured."
