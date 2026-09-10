"""Tests for private interest-lead capture (Epic A: gated entry + funnel).

- Public submission always returns the same envelope (no email oracle).
- Admin listing/status changes require ``platform_admin``.
- Service maps storage rows to models and hides internals on failure.
"""

from unittest.mock import AsyncMock, MagicMock, Mock, patch
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from src.leads.models import InterestLeadCreate

LEAD_ID = uuid4()


def _lead_row(**overrides: Any) -> dict[str, Any]:
    row = {
        "id": str(LEAD_ID),
        "name": "Sam Owner",
        "business_name": "Bright Smiles Dental",
        "email": "sam@example.com",
        "phone": "+14805550100",
        "vertical": "dental",
        "message": "Miss after-hours calls",
        "source": "request-demo",
        "demo_slug": None,
        "status": "new",
        "created_at": "2026-09-03T00:00:00+00:00",
        "contacted_at": None,
    }
    row.update(overrides)
    return row


def _submit_payload(**overrides: Any) -> InterestLeadCreate:
    data: dict[str, Any] = {
        "name": "Sam Owner",
        "business_name": "Bright Smiles Dental",
        "email": "sam@example.com",
        "phone": "+14805550100",
        "vertical": "dental",
        "message": "Miss after-hours calls",
    }
    data.update(overrides)
    return InterestLeadCreate(**data)


def _chain_client(response=None, explode=False):
    """Fake service-role client emulating the fluent query chain."""
    resp = MagicMock()
    resp.data = response if response is not None else []
    execute = MagicMock(return_value=resp)
    if explode:
        execute.side_effect = RuntimeError("db down")
    node = MagicMock()
    node.execute = execute
    for method in ("select", "insert", "update", "order", "limit", "eq"):
        getattr(node, method).return_value = node
    client = MagicMock()
    client.table.return_value = node
    return client


def _platform_admin_profile():
    profile = Mock()
    profile.has_role = Mock(side_effect=lambda role: role == "platform_admin")
    profile.has_permission = Mock(return_value=True)
    return profile


def _regular_profile():
    profile = Mock()
    profile.has_role = Mock(return_value=False)
    profile.has_permission = Mock(return_value=False)
    return profile


def _request():
    from starlette.requests import Request

    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/public/leads",
            "headers": [],
            "query_string": b"",
            "server": ("testserver", 80),
            "scheme": "http",
            "client": ("127.0.0.1", 50000),
        }
    )


class TestSubmitInterestLeadRoute:
    @pytest.mark.asyncio
    async def test_submit_returns_ack_envelope(self):
        from src.leads.routes import submit_interest_lead

        with patch(
            "src.leads.routes.lead_service.submit_lead",
            new=AsyncMock(return_value=(Mock(), None)),
        ):
            ack = await submit_interest_lead(
                request=_request(), body=_submit_payload()
            )
            assert ack.received is True

    @pytest.mark.asyncio
    async def test_submit_failure_is_safe_500(self):
        from src.leads.routes import submit_interest_lead

        with patch(
            "src.leads.routes.lead_service.submit_lead",
            new=AsyncMock(return_value=(None, "Could not record your request.")),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await submit_interest_lead(
                    request=_request(), body=_submit_payload()
                )
            assert exc_info.value.status_code == 500
            assert "sam@example.com" not in str(exc_info.value.detail)


class TestAdminLeadRoutes:
    @pytest.mark.asyncio
    async def test_regular_user_cannot_list_leads(self):
        from src.leads.routes import list_interest_leads

        with pytest.raises(HTTPException) as exc_info:
            await list_interest_leads(
                request=_request(),
                user_data=(uuid4(), _regular_profile()),
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_platform_admin_lists_leads(self):
        from src.leads.routes import list_interest_leads

        sentinel = [Mock()]
        with patch(
            "src.leads.routes.lead_service.list_leads",
            new=AsyncMock(return_value=(sentinel, None)),
        ):
            result = await list_interest_leads(
                request=_request(),
                user_data=(uuid4(), _platform_admin_profile()),
            )
            assert result is sentinel

    @pytest.mark.asyncio
    async def test_regular_user_cannot_change_status(self):
        from src.leads.routes import mark_interest_lead_status
        from src.leads.routes import LeadStatusUpdate

        with pytest.raises(HTTPException) as exc_info:
            await mark_interest_lead_status(
                LEAD_ID,
                LeadStatusUpdate(status="contacted"),
                request=_request(),
                user_data=(uuid4(), _regular_profile()),
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_missing_lead_maps_to_404(self):
        from src.leads.routes import mark_interest_lead_status
        from src.leads.routes import LeadStatusUpdate

        with patch(
            "src.leads.routes.lead_service.mark_status",
            new=AsyncMock(return_value=(None, "Lead not found.")),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await mark_interest_lead_status(
                    LEAD_ID,
                    LeadStatusUpdate(status="contacted"),
                    request=_request(),
                    user_data=(uuid4(), _platform_admin_profile()),
                )
            assert exc_info.value.status_code == 404


class TestLeadService:
    @pytest.mark.asyncio
    async def test_submit_persists_and_returns_model(self):
        from src.leads.service import LeadService

        service = LeadService()
        service.supabase_config = Mock()
        service.supabase_config.is_configured.return_value = True
        service.supabase_config.service_client = _chain_client([_lead_row()])
        lead, error = await service.submit_lead(_submit_payload())
        assert error is None
        assert lead is not None
        assert lead.email == "sam@example.com"
        assert lead.status == "new"

    @pytest.mark.asyncio
    async def test_submit_hides_storage_failure(self):
        from src.leads.service import LeadService

        service = LeadService()
        service.supabase_config = Mock()
        service.supabase_config.is_configured.return_value = True
        service.supabase_config.service_client = _chain_client(explode=True)
        lead, error = await service.submit_lead(_submit_payload())
        assert lead is None
        assert error is not None

    @pytest.mark.asyncio
    async def test_list_applies_status_filter(self):
        from src.leads.service import LeadService

        service = LeadService()
        service.supabase_config = Mock()
        service.supabase_config.is_configured.return_value = True
        client = _chain_client([_lead_row(status="contacted")])
        service.supabase_config.service_client = client
        leads, error = await service.list_leads(status="contacted", limit=10)
        assert error is None
        assert [lead.status for lead in leads] == ["contacted"]
        client.table.assert_called_with("interest_leads")

    @pytest.mark.asyncio
    async def test_mark_status_missing_row(self):
        from src.leads.service import LeadService

        service = LeadService()
        service.supabase_config = Mock()
        service.supabase_config.is_configured.return_value = True
        service.supabase_config.service_client = _chain_client([])
        lead, error = await service.mark_status(UUID(str(LEAD_ID)), "invited")
        assert lead is None
        assert error == "Lead not found."
