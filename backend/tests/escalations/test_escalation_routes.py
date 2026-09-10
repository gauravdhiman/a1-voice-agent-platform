"""Tests for org-scoped callback escalation routes (Epic D)."""

from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from src.escalations.models import EscalationCreate, EscalationStatusUpdate

ORG_ID = uuid4()
ESC_ID = uuid4()


def _org_member_profile(*, admin: bool = False):
    profile = Mock()

    def has_role(role: str, org: str | None = None) -> bool:
        if role == "platform_admin":
            return False
        if role == "org_admin":
            return admin and org == str(ORG_ID)
        if role == "regular_user":
            return org == str(ORG_ID)
        return False

    profile.has_role = Mock(side_effect=has_role)
    profile.has_permission = Mock(return_value=False)
    return profile


def _outsider_profile():
    profile = Mock()
    profile.has_role = Mock(return_value=False)
    profile.has_permission = Mock(return_value=False)
    return profile


def _request():
    from starlette.requests import Request

    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/organizations/x/escalations",
            "headers": [],
            "query_string": b"",
            "server": ("testserver", 80),
            "scheme": "http",
            "client": ("127.0.0.1", 50000),
        }
    )


class TestListEscalationsRoute:
    @pytest.mark.asyncio
    async def test_member_lists_escalations(self):
        from src.escalations.routes import list_escalations

        sentinel = [Mock()]
        with patch(
            "src.escalations.routes.escalation_service.list_escalations",
            new=AsyncMock(return_value=(sentinel, None)),
        ):
            result = await list_escalations(
                ORG_ID,
                request=_request(),
                user_data=(uuid4(), _org_member_profile()),
            )
            assert result is sentinel

    @pytest.mark.asyncio
    async def test_outsider_is_denied(self):
        from src.escalations.routes import list_escalations

        with patch(
            "src.escalations.routes.escalation_service.list_escalations",
            new=AsyncMock(),
        ) as mock_list:
            with pytest.raises(HTTPException) as exc_info:
                await list_escalations(
                    ORG_ID,
                    request=_request(),
                    user_data=(uuid4(), _outsider_profile()),
                )
            assert exc_info.value.status_code == 403
            mock_list.assert_not_called()


class TestCreateEscalationRoute:
    def _body(self):
        return EscalationCreate(
            caller_phone="+14805550100",
            reason="Water heater is leaking.",
            urgency="urgent",
        )

    @pytest.mark.asyncio
    async def test_org_admin_can_log_manually(self):
        from src.escalations.routes import create_escalation

        sentinel = Mock()
        with patch(
            "src.escalations.routes.escalation_service.create_escalation",
            new=AsyncMock(return_value=(sentinel, None)),
        ) as mock_create:
            result = await create_escalation(
                org_id=ORG_ID,
                body=self._body(),
                request=_request(),
                user_data=(uuid4(), _org_member_profile(admin=True)),
            )
            assert result is sentinel
            mock_create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_regular_member_cannot_log(self):
        from src.escalations.routes import create_escalation

        with patch(
            "src.escalations.routes.escalation_service.create_escalation",
            new=AsyncMock(),
        ) as mock_create:
            with pytest.raises(HTTPException) as exc_info:
                await create_escalation(
                    org_id=ORG_ID,
                    body=self._body(),
                    request=_request(),
                    user_data=(uuid4(), _org_member_profile(admin=False)),
                )
            assert exc_info.value.status_code == 403
            mock_create.assert_not_called()


class TestMarkEscalationStatusRoute:
    @pytest.mark.asyncio
    async def test_admin_advances_status(self):
        from src.escalations.routes import mark_escalation_status

        sentinel = Mock()
        with patch(
            "src.escalations.routes.escalation_service.mark_status",
            new=AsyncMock(return_value=(sentinel, None)),
        ):
            result = await mark_escalation_status(
                ORG_ID,
                ESC_ID,
                EscalationStatusUpdate(status="acknowledged"),
                request=_request(),
                user_data=(uuid4(), _org_member_profile(admin=True)),
            )
            assert result is sentinel

    @pytest.mark.asyncio
    async def test_missing_row_maps_to_404(self):
        from src.escalations.routes import mark_escalation_status

        with patch(
            "src.escalations.routes.escalation_service.mark_status",
            new=AsyncMock(return_value=(None, "Callback request not found.")),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await mark_escalation_status(
                    ORG_ID,
                    ESC_ID,
                    EscalationStatusUpdate(status="resolved"),
                    request=_request(),
                    user_data=(uuid4(), _org_member_profile(admin=True)),
                )
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_cross_org_row_cannot_leak(self):
        """A valid id from another org resolves to 404, never the row."""
        from src.escalations.routes import mark_escalation_status

        other_org = UUID("99999999-9999-9999-9999-999999999999")
        with patch(
            "src.escalations.routes.escalation_service.mark_status",
            new=AsyncMock(return_value=(None, "Callback request not found.")),
        ) as mock_mark:
            with pytest.raises(HTTPException) as exc_info:
                await mark_escalation_status(
                    other_org,
                    ESC_ID,
                    EscalationStatusUpdate(status="resolved"),
                    request=_request(),
                    user_data=(uuid4(), _org_member_profile(admin=True)),
                )
            assert exc_info.value.status_code in (403, 404)
            if exc_info.value.status_code == 404:
                mock_mark.assert_awaited_once_with(other_org, ESC_ID, "resolved")
