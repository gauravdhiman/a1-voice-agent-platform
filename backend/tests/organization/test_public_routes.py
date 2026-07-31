"""Route tests for the public organization page API."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.organization.public_routes import (
    PublicAccessRequest,
    generate_public_call_token,
    get_public_org_summary,
    list_public_org_agents,
    verify_public_org_access,
)

ORG_ID = str(uuid4())
AGENT_ID = uuid4()
SLUG = "acme"


def _org_row(**over):
    base = {
        "id": ORG_ID,
        "name": "Acme Corp",
        "description": "We help customers",
        "slug": SLUG,
        "is_active": True,
        "public_page_enabled": True,
        "public_page_passphrase_enabled": False,
        "public_page_passphrase_hash": None,
    }
    base.update(over)
    return base


@pytest.fixture
def mock_supabase():
    with patch("src.organization.public_routes.organization_service") as org_svc:
        table = Mock()
        org_svc.supabase.table.return_value = table
        yield org_svc, table


@pytest.mark.asyncio
async def test_get_public_org_summary(mock_supabase):
    _org_svc, table = mock_supabase
    chain = table.select.return_value.eq.return_value.limit.return_value
    chain.execute.return_value = Mock(data=[_org_row()])

    result = await get_public_org_summary(SLUG)
    assert result.name == "Acme Corp"
    assert result.slug == SLUG
    assert result.passphrase_required is False


@pytest.mark.asyncio
async def test_public_page_disabled_returns_404(mock_supabase):
    _org_svc, table = mock_supabase
    chain = table.select.return_value.eq.return_value.limit.return_value
    chain.execute.return_value = Mock(data=[_org_row(public_page_enabled=False)])

    with pytest.raises(HTTPException) as exc:
        await get_public_org_summary(SLUG)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_verify_passphrase_issues_token(mock_supabase):
    from shared.organization.public_page_security import hash_public_page_passphrase

    _org_svc, table = mock_supabase
    chain = table.select.return_value.eq.return_value.limit.return_value
    chain.execute.return_value = Mock(
        data=[
            _org_row(
                public_page_passphrase_enabled=True,
                public_page_passphrase_hash=hash_public_page_passphrase("hello"),
            )
        ]
    )

    with patch(
        "src.organization.public_routes.public_page_service.generate_access_token",
        return_value="token-123",
    ):
        result = await verify_public_org_access(
            SLUG, PublicAccessRequest(passphrase="hello")
        )
    assert result.access_token == "token-123"


@pytest.mark.asyncio
async def test_list_agents_requires_token_when_passphrase_enabled(mock_supabase):
    _org_svc, table = mock_supabase
    chain = table.select.return_value.eq.return_value.limit.return_value
    chain.execute.return_value = Mock(
        data=[_org_row(public_page_passphrase_enabled=True)]
    )

    with pytest.raises(HTTPException) as exc:
        await list_public_org_agents(SLUG, x_public_access_token=None)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_generate_call_token_for_published_agent(mock_supabase):
    _org_svc, table = mock_supabase
    chain = table.select.return_value.eq.return_value.limit.return_value
    chain.execute.return_value = Mock(data=[_org_row()])

    agent = SimpleNamespace(
        id=AGENT_ID,
        organization_id=ORG_ID,
        is_active=True,
        is_published_on_public_page=True,
    )

    with patch(
        "src.organization.public_routes.voice_agent_service.get_agent_by_id",
        new=AsyncMock(return_value=(agent, None)),
    ), patch(
        "src.organization.public_routes.public_page_service.generate_call_token",
        return_value=("lk-token", "wss://livekit", f"public_{AGENT_ID}_abc"),
    ):
        result = await generate_public_call_token(
            SLUG, AGENT_ID, x_public_access_token=None
        )

    assert result.livekit_token == "lk-token"
    assert result.room_name.startswith("public_")
