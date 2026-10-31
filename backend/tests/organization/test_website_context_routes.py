"""Route authorization and persistence tests for website context drafts."""

from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID

import pytest
from fastapi import HTTPException
from starlette.requests import Request

ORG_ID = UUID("00000000-0000-0000-0000-000000000020")
USER_ID = UUID("00000000-0000-0000-0000-000000000040")


def _request(client_ip: str) -> Request:
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": f"/api/v1/organizations/{ORG_ID}/business-context-from-website",
            "query_string": b"",
            "headers": [],
            "client": (client_ip, 50000),
            "server": ("testserver", 80),
        }
    )


def _profile(*, is_org_admin: bool) -> Mock:
    profile = Mock()
    profile.has_role = Mock(
        side_effect=lambda role, org_id=None: (
            role == "org_admin" and org_id == str(ORG_ID) and is_org_admin
        )
    )
    return profile


@pytest.mark.asyncio
async def test_regular_user_cannot_trigger_provider_calls() -> None:
    from src.organization.models import WebsiteBusinessContextRequest
    from src.organization.routes import generate_website_business_context

    service = Mock()
    service.generate = AsyncMock()
    with patch("src.organization.routes.website_business_context_service", service):
        with pytest.raises(HTTPException) as exc_info:
            await generate_website_business_context(
                org_id=ORG_ID,
                request=_request("192.0.2.31"),
                body=WebsiteBusinessContextRequest(website="https://example.com"),
                user_data=(USER_ID, _profile(is_org_admin=False)),
            )

    assert exc_info.value.status_code == 403
    service.generate.assert_not_awaited()


@pytest.mark.asyncio
async def test_admin_of_another_organization_cannot_trigger_provider_calls() -> None:
    from src.organization.models import WebsiteBusinessContextRequest
    from src.organization.routes import generate_website_business_context

    profile = Mock()
    profile.has_role = Mock(
        side_effect=lambda role, org_id=None: (
            role == "org_admin" and org_id == "00000000-0000-0000-0000-000000000099"
        )
    )
    service = Mock()
    service.generate = AsyncMock()

    with patch("src.organization.routes.website_business_context_service", service):
        with pytest.raises(HTTPException) as exc_info:
            await generate_website_business_context(
                org_id=ORG_ID,
                request=_request("192.0.2.34"),
                body=WebsiteBusinessContextRequest(website="https://example.com"),
                user_data=(USER_ID, profile),
            )

    assert exc_info.value.status_code == 403
    service.generate.assert_not_awaited()


@pytest.mark.asyncio
async def test_org_admin_receives_unsaved_draft_without_organization_write() -> None:
    from src.organization.models import WebsiteBusinessContextRequest
    from src.organization.routes import generate_website_business_context

    service = Mock()
    service.generate = AsyncMock(
        return_value={
            "business_details": "Editable draft",
            "pages_analyzed": 3,
            "page_limit_reached": False,
        }
    )
    organization_writer = Mock()

    with (
        patch("src.organization.routes.website_business_context_service", service),
        patch("src.organization.routes.organization_service", organization_writer),
    ):
        result = await generate_website_business_context(
            org_id=ORG_ID,
            request=_request("192.0.2.32"),
            body=WebsiteBusinessContextRequest(website="https://example.com/?ref=ad"),
            user_data=(USER_ID, _profile(is_org_admin=True)),
        )

    assert result == {
        "business_details": "Editable draft",
        "pages_analyzed": 3,
        "page_limit_reached": False,
    }
    service.generate.assert_awaited_once_with("https://example.com/")
    organization_writer.update_organization.assert_not_called()


@pytest.mark.asyncio
async def test_org_admin_cannot_request_private_website() -> None:
    from src.organization.models import WebsiteBusinessContextRequest
    from src.organization.routes import generate_website_business_context

    service = Mock()
    service.generate = AsyncMock()
    with patch("src.organization.routes.website_business_context_service", service):
        with pytest.raises(HTTPException) as exc_info:
            await generate_website_business_context(
                org_id=ORG_ID,
                request=_request("192.0.2.33"),
                body=WebsiteBusinessContextRequest(website="http://127.0.0.1"),
                user_data=(USER_ID, _profile(is_org_admin=True)),
            )

    assert exc_info.value.status_code == 422
    service.generate.assert_not_awaited()


@pytest.mark.parametrize(
    ("provider_error", "status_code", "detail", "client_ip"),
    [
        (
            "not_configured",
            503,
            "Website context generation is not available right now.",
            "192.0.2.41",
        ),
        (
            "provider_failure",
            502,
            "We could not prepare a draft from that website. Please try again.",
            "192.0.2.42",
        ),
    ],
)
@pytest.mark.asyncio
async def test_provider_failures_return_safe_messages(
    provider_error: str, status_code: int, detail: str, client_ip: str
) -> None:
    from src.organization.models import WebsiteBusinessContextRequest
    from src.organization.routes import generate_website_business_context
    from src.organization.website_context_service import (
        WebsiteContextNotConfigured,
        WebsiteContextProviderError,
    )

    error = (
        WebsiteContextNotConfigured("provider key detail")
        if provider_error == "not_configured"
        else WebsiteContextProviderError("provider response detail")
    )
    service = Mock()
    service.generate = AsyncMock(side_effect=error)
    with patch("src.organization.routes.website_business_context_service", service):
        with pytest.raises(HTTPException) as exc_info:
            await generate_website_business_context(
                org_id=ORG_ID,
                request=_request(client_ip),
                body=WebsiteBusinessContextRequest(website="https://example.com"),
                user_data=(USER_ID, _profile(is_org_admin=True)),
            )

    assert exc_info.value.status_code == status_code
    assert exc_info.value.detail == detail
