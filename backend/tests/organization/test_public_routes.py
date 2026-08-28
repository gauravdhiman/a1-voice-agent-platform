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

from shared.billing.voice_session_entitlement import VoiceSessionEntitlementError

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
async def test_list_agents_returns_active_published_agents(mock_supabase):
    """The public listing delegates to the service's publish/active filter."""
    _org_svc, table = mock_supabase
    chain = table.select.return_value.eq.return_value.limit.return_value
    chain.execute.return_value = Mock(data=[_org_row()])
    published_agent = SimpleNamespace(
        id=AGENT_ID,
        name="Published Agent",
        persona="Receptionist",
        mission="Book appointments",
    )

    with patch(
        "src.organization.public_routes.voice_agent_service.get_public_page_agents",
        new=AsyncMock(return_value=([published_agent], None)),
    ):
        result = await list_public_org_agents(SLUG, x_public_access_token=None)

    assert len(result.agents) == 1
    assert result.agents[0].name == "Published Agent"
    assert result.agents[0].persona == "Receptionist"


@pytest.mark.asyncio
async def test_public_call_token_rejects_unpublished_agent(mock_supabase):
    """Visitors cannot start calls for agents not explicitly published."""
    _org_svc, table = mock_supabase
    chain = table.select.return_value.eq.return_value.limit.return_value
    chain.execute.return_value = Mock(data=[_org_row()])

    agent = SimpleNamespace(
        id=AGENT_ID,
        organization_id=ORG_ID,
        is_active=True,
        is_published_on_public_page=False,
        is_demo=False,
    )

    with patch(
        "src.organization.public_routes.voice_agent_service.get_agent_by_id",
        new=AsyncMock(return_value=(agent, None)),
    ):
        with pytest.raises(HTTPException) as exc:
            await generate_public_call_token(SLUG, AGENT_ID, None)

    assert exc.value.status_code == 400
    assert "not available" in exc.value.detail


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
        return_value=("voice.jwt.token", "ws://localhost:7860/ws", "sess-public-1"),
    ), patch(
        "src.organization.public_routes.assert_voice_session_allowed",
        new=AsyncMock(),
        create=True,
    ):
        result = await generate_public_call_token(
            SLUG, AGENT_ID, x_public_access_token=None
        )

    assert result.token == "voice.jwt.token"
    assert result.wsUrl == "ws://localhost:7860/ws"
    assert result.sessionId == "sess-public-1"


@pytest.mark.asyncio
async def test_public_demo_call_token_reserves_budget_and_returns_remaining(
    mock_supabase,
):
    from shared.billing.voice_session_entitlement import DemoCallReservation

    _org_svc, table = mock_supabase
    chain = table.select.return_value.eq.return_value.limit.return_value
    chain.execute.return_value = Mock(data=[_org_row()])
    agent = SimpleNamespace(
        id=AGENT_ID,
        organization_id=ORG_ID,
        is_active=True,
        is_published_on_public_page=True,
        is_demo=True,
        demo_calls_remaining=3,
        demo_max_call_duration_seconds=600,
    )

    with patch(
        "src.organization.public_routes.voice_agent_service.get_agent_by_id",
        new=AsyncMock(return_value=(agent, None)),
    ), patch(
        "src.organization.public_routes.reserve_demo_call_if_needed",
        new=AsyncMock(
            return_value=DemoCallReservation("reservation-1", "session-1", 2, 600)
        ),
    ) as reserve, patch(
        "src.organization.public_routes.public_page_service.generate_call_token",
        return_value=("voice.jwt.token", "ws://localhost:7860/ws", "session-1"),
    ), patch(
        "src.organization.public_routes.assert_voice_session_allowed",
        new=AsyncMock(),
    ):
        result = await generate_public_call_token(SLUG, AGENT_ID, None)

    reserve.assert_awaited_once_with(agent)
    assert result.demo_calls_remaining == 2
    assert result.demo_max_call_duration_seconds == 600


@pytest.mark.asyncio
async def test_public_demo_call_token_returns_exhausted_trial_message(mock_supabase):
    _org_svc, table = mock_supabase
    chain = table.select.return_value.eq.return_value.limit.return_value
    chain.execute.return_value = Mock(data=[_org_row()])
    agent = SimpleNamespace(
        id=AGENT_ID,
        organization_id=ORG_ID,
        is_active=True,
        is_published_on_public_page=True,
        is_demo=True,
    )

    with patch(
        "src.organization.public_routes.voice_agent_service.get_agent_by_id",
        new=AsyncMock(return_value=(agent, None)),
    ), patch(
        "src.organization.public_routes.reserve_demo_call_if_needed",
        new=AsyncMock(
            side_effect=VoiceSessionEntitlementError(
                "DEMO_CALL_LIMIT_REACHED", "all demo calls used"
            )
        ),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await generate_public_call_token(SLUG, AGENT_ID, None)

    assert exc_info.value.status_code == 429
    assert exc_info.value.detail["code"] == "DEMO_TRIAL_EXHAUSTED"


@pytest.mark.asyncio
async def test_public_call_token_returns_safe_unavailable_error(mock_supabase):
    """Public-page visitors receive safe availability guidance."""
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
        "src.organization.public_routes.assert_voice_session_allowed",
        new=AsyncMock(
            side_effect=VoiceSessionEntitlementError(
                "INSUFFICIENT_CREDITS",
                "Insufficient credits to start a voice call.",
            )
        ),
        create=True,
    ):
        with pytest.raises(HTTPException) as exc:
            await generate_public_call_token(SLUG, AGENT_ID, None)

    assert exc.value.status_code == 503
    assert exc.value.detail["code"] == "VOICE_ASSISTANT_UNAVAILABLE"
    assert "contact the business" in exc.value.detail["message"].lower()
