"""
Tests for voice agent routes.
"""

import json
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID

import pytest
from opentelemetry import trace
from starlette.requests import Request


class TestAgentRoutes:
    """Test cases for agent routes."""

    @pytest.mark.asyncio
    async def test_get_agent_system_prompt_success(self):
        """Test successful retrieval of generated system prompt."""
        from src.voice_agents.routes import get_agent_system_prompt
        from shared.voice_agents.models import VoiceAgent
        from shared.organization.models import Organization

        # Create test data
        test_agent_id = UUID("00000000-0000-0000-0000-000000000001")
        test_org_id = UUID("00000000-0000-0000-0000-000000000002")
        test_user_id = UUID("00000000-0000-0000-0000-000000000003")

        agent = VoiceAgent(
            id=test_agent_id,
            organization_id=test_org_id,
            name="Test Agent",
            phone_number="+1234567890",
            persona="Support Specialist",
            tone="Professional",
            mission="Help customers with their inquiries",
            custom_instructions="Always be polite and helpful",
            is_active=True,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )

        org = Organization(
            id=test_org_id,
            name="Test Organization",
            slug="test-org",
            description="A test organization",
            industry="Technology",
            location="123 Test St",
            business_details="We provide excellent tech support",
            is_active=True,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )

        # Mock user profile
        mock_user_profile = Mock()
        mock_user_profile.has_role = Mock(return_value=True)

        # Mock voice_agent_service
        with patch("src.voice_agents.routes.voice_agent_service") as mock_voice_service:
            mock_voice_service.get_agent_by_id = AsyncMock(return_value=(agent, None))

            # Mock OrganizationService
            with patch("src.voice_agents.routes.OrganizationService") as mock_org_service_class:
                mock_org_service = Mock()
                mock_org_service.get_organization_by_id = AsyncMock(return_value=(org, None))
                mock_org_service_class.return_value = mock_org_service

                # Call the endpoint
                result = await get_agent_system_prompt(
                    agent_id=test_agent_id,
                    user_data=(test_user_id, mock_user_profile),
                )

                # Verify the result contains expected sections
                assert "Support Specialist" in result
                assert "Test Organization" in result
                assert "Professional" in result
                assert "Help customers" in result
                assert "tech support" in result
                assert "polite and helpful" in result

    @pytest.mark.asyncio
    async def test_get_agent_system_prompt_agent_not_found(self):
        """Test system prompt retrieval when agent doesn't exist."""
        from src.voice_agents.routes import get_agent_system_prompt
        from fastapi import HTTPException

        test_agent_id = UUID("00000000-0000-0000-0000-000000000001")
        test_user_id = UUID("00000000-0000-0000-0000-000000000003")

        mock_user_profile = Mock()
        mock_user_profile.has_role = Mock(return_value=True)

        with patch("src.voice_agents.routes.voice_agent_service") as mock_voice_service:
            mock_voice_service.get_agent_by_id = AsyncMock(
                return_value=(None, "Agent not found")
            )

            with pytest.raises(HTTPException) as exc_info:
                await get_agent_system_prompt(
                    agent_id=test_agent_id,
                    user_data=(test_user_id, mock_user_profile),
                )

            assert exc_info.value.status_code == 404
            assert "Agent not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_agent_system_prompt_permission_denied(self):
        """Test system prompt retrieval without proper permissions."""
        from src.voice_agents.routes import get_agent_system_prompt
        from fastapi import HTTPException
        from shared.voice_agents.models import VoiceAgent

        test_agent_id = UUID("00000000-0000-0000-0000-000000000001")
        test_org_id = UUID("00000000-0000-0000-0000-000000000002")
        test_user_id = UUID("00000000-0000-0000-0000-000000000003")

        agent = VoiceAgent(
            id=test_agent_id,
            organization_id=test_org_id,
            name="Test Agent",
            phone_number="+1234567890",
            is_active=True,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )

        # Mock user profile that denies all permissions
        mock_user_profile = Mock()
        mock_user_profile.has_role = Mock(return_value=False)

        with patch("src.voice_agents.routes.voice_agent_service") as mock_voice_service:
            mock_voice_service.get_agent_by_id = AsyncMock(return_value=(agent, None))

            with pytest.raises(HTTPException) as exc_info:
                await get_agent_system_prompt(
                    agent_id=test_agent_id,
                    user_data=(test_user_id, mock_user_profile),
                )

            assert exc_info.value.status_code == 403
            assert "Insufficient permissions" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_agent_system_prompt_org_not_found(self):
        """Test system prompt retrieval when organization doesn't exist."""
        from src.voice_agents.routes import get_agent_system_prompt
        from fastapi import HTTPException
        from shared.voice_agents.models import VoiceAgent

        test_agent_id = UUID("00000000-0000-0000-0000-000000000001")
        test_org_id = UUID("00000000-0000-0000-0000-000000000002")
        test_user_id = UUID("00000000-0000-0000-0000-000000000003")

        agent = VoiceAgent(
            id=test_agent_id,
            organization_id=test_org_id,
            name="Test Agent",
            phone_number="+1234567890",
            is_active=True,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )

        mock_user_profile = Mock()
        mock_user_profile.has_role = Mock(return_value=True)

        with patch("src.voice_agents.routes.voice_agent_service") as mock_voice_service:
            mock_voice_service.get_agent_by_id = AsyncMock(return_value=(agent, None))

            with patch("src.voice_agents.routes.OrganizationService") as mock_org_service_class:
                mock_org_service = Mock()
                mock_org_service.get_organization_by_id = AsyncMock(
                    return_value=(None, "Organization not found")
                )
                mock_org_service_class.return_value = mock_org_service

                with pytest.raises(HTTPException) as exc_info:
                    await get_agent_system_prompt(
                        agent_id=test_agent_id,
                        user_data=(test_user_id, mock_user_profile),
                    )

                assert exc_info.value.status_code == 500
                assert "Could not fetch organization" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_agent_system_prompt_uses_markdown_when_set(self):
        """Test system prompt uses instructions_markdown when available."""
        from src.voice_agents.routes import get_agent_system_prompt
        from shared.voice_agents.models import VoiceAgent
        from shared.organization.models import Organization

        test_agent_id = UUID("00000000-0000-0000-0000-000000000001")
        test_org_id = UUID("00000000-0000-0000-0000-000000000002")
        test_user_id = UUID("00000000-0000-0000-0000-000000000003")

        agent = VoiceAgent(
            id=test_agent_id,
            organization_id=test_org_id,
            name="Test Agent",
            persona="Should NOT appear in output",
            instructions_markdown="# Custom Agent\n\nYou are a receptionist for {{org.name}}.",
            is_active=True,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )

        org = Organization(
            id=test_org_id,
            name="Pleasant Pediatrics",
            slug="test-org",
            is_active=True,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )

        mock_user_profile = Mock()
        mock_user_profile.has_role = Mock(return_value=True)

        with patch("src.voice_agents.routes.voice_agent_service") as mock_voice_service:
            mock_voice_service.get_agent_by_id = AsyncMock(return_value=(agent, None))

            with patch("src.voice_agents.routes.OrganizationService") as mock_org_service_class:
                mock_org_service = Mock()
                mock_org_service.get_organization_by_id = AsyncMock(return_value=(org, None))
                mock_org_service_class.return_value = mock_org_service

                result = await get_agent_system_prompt(
                    agent_id=test_agent_id,
                    user_data=(test_user_id, mock_user_profile),
                )

                # Markdown content should be used with template vars rendered
                assert "Custom Agent" in result
                assert "Pleasant Pediatrics" in result
                # Field-based persona should NOT appear
                assert "Should NOT appear" not in result
                # Guardrails always appended
                assert "SYSTEM GUARDRAILS" in result

    @pytest.mark.asyncio
    async def test_generate_markdown_from_fields(self):
        """Test generate-markdown endpoint converts fields to markdown."""
        from src.voice_agents.routes import generate_markdown_from_fields
        from shared.voice_agents.models import VoiceAgent
        from shared.organization.models import Organization

        test_agent_id = UUID("00000000-0000-0000-0000-000000000001")
        test_org_id = UUID("00000000-0000-0000-0000-000000000002")
        test_user_id = UUID("00000000-0000-0000-0000-000000000003")

        agent = VoiceAgent(
            id=test_agent_id,
            organization_id=test_org_id,
            name="Test Agent",
            persona="a friendly dental receptionist",
            tone="warm, professional",
            mission="Help patients schedule appointments",
            custom_instructions="Always confirm appointment details",
            is_active=True,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )

        org = Organization(
            id=test_org_id,
            name="Pleasant Pediatrics",
            slug="test-org",
            industry="dental",
            location="Phoenix, AZ",
            business_details="Family dental office",
            is_active=True,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )

        mock_user_profile = Mock()
        mock_user_profile.has_role = Mock(return_value=True)

        with patch("src.voice_agents.routes.voice_agent_service") as mock_voice_service:
            mock_voice_service.get_agent_by_id = AsyncMock(return_value=(agent, None))

            with patch("src.voice_agents.routes.OrganizationService") as mock_org_service_class:
                mock_org_service = Mock()
                mock_org_service.get_organization_by_id = AsyncMock(return_value=(org, None))
                mock_org_service_class.return_value = mock_org_service

                result = await generate_markdown_from_fields(
                    agent_id=test_agent_id,
                    user_data=(test_user_id, mock_user_profile),
                )

                # Should have markdown sections
                assert "# Identity and Persona" in result
                assert "dental receptionist" in result
                assert "warm, professional" in result
                assert "# Mission" in result
                assert "schedule appointments" in result
                assert "# Business Context" in result
                assert "dental" in result
                assert "Phoenix, AZ" in result
                assert "# Additional Instructions" in result
                assert "confirm appointment details" in result


# ---------------------------------------------------------------------------
# Tests for the declarative `require_permission` factory wired into
# `create_agent` (Task #22 — Phase 5 reference migration).
# ---------------------------------------------------------------------------

CREATE_AGENT_TEST_ORG = UUID("00000000-0000-0000-0000-0000000000a1")
CREATE_AGENT_OTHER_ORG = UUID("00000000-0000-0000-0000-0000000000b2")
CREATE_AGENT_TEST_USER = UUID("00000000-0000-0000-0000-0000000000c3")


def _agent_profile(
    is_platform_admin: bool = False,
    is_org_admin_on: str | None = None,
):
    """Build a UserProfile mock for create_agent permission tests."""
    profile = Mock()
    profile.has_role = Mock(
        side_effect=lambda role, org_id=None: (
            (role == "platform_admin" and is_platform_admin)
            or (role == "org_admin" and org_id == is_org_admin_on)
        )
    )
    # The permission check in the factory is `agent:create` on the
    # body's organization_id. By default this profile holds no
    # permissions — only the role-based bypass (org_admin or
    # platform_admin) lets it through. Tests that need a different
    # permission matrix can pass `has_perm` here.
    profile.has_permission = Mock(return_value=False)
    return profile


def _agent_create_body(org_id: UUID) -> dict:
    return {
        "organization_id": str(org_id),
        "name": "Test Agent",
        "phone_number": "+15555550100",
        "persona": "Support Specialist",
        "tone": "Professional",
        "mission": "Help customers",
        "is_active": True,
    }


def _make_post_request(body: dict) -> Request:
    body_bytes = json.dumps(body).encode("utf-8")

    async def receive():
        return {
            "type": "http.request",
            "body": body_bytes,
            "more_body": False,
        }

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "query_string": b"",
        "headers": [
            (b"content-type", b"application/json"),
            (b"authorization", b"Bearer mock-jwt-token"),
        ],
        "server": ("testserver", 80),
        "client": ("testclient", 50000),
    }
    return Request(scope, receive=receive)


class TestCreateAgentDeclarativePermission:
    """Reference migration: `create_agent` uses
    `Depends(require_permission("agent", "create", org_id_source="body",
    body_field="organization_id"))` instead of an inline `has_role`
    ladder.

    Contract:
      - platform_admin → 201 (any org_id)
      - org_admin on the body's org_id → 201
      - org_admin on a DIFFERENT org → 403
      - regular user → 403
    """

    @pytest.mark.asyncio
    async def test_platform_admin_allowed(self):
        from src.voice_agents.routes import create_agent
        from shared.voice_agents.models import VoiceAgent, VoiceAgentCreate

        profile = _agent_profile(is_platform_admin=True)
        body = _agent_create_body(CREATE_AGENT_TEST_ORG)
        request = _make_post_request(body)
        agent_data = VoiceAgentCreate(**body)

        with patch("src.auth.dependencies.get_authenticated_user") as mock_auth, \
             patch("src.voice_agents.routes.voice_agent_service") as mock_svc:
            mock_auth.return_value = (CREATE_AGENT_TEST_USER, profile)
            created = VoiceAgent(
                id=UUID("00000000-0000-0000-0000-0000000000d4"),
                organization_id=CREATE_AGENT_TEST_ORG,
                name=body["name"],
                phone_number=body["phone_number"],
                persona=body["persona"],
                tone=body["tone"],
                mission=body["mission"],
                custom_instructions=None,
                is_active=True,
                created_at="2026-07-06T00:00:00",
                updated_at="2026-07-06T00:00:00",
            )
            mock_svc.create_agent = AsyncMock(return_value=(created, None))

            result = await create_agent(
                agent_data=agent_data,
                request=request,
                _auth=mock_auth.return_value,
            )
            assert result is not None
            mock_svc.create_agent.assert_called_once()

    @pytest.mark.asyncio
    async def test_org_admin_on_body_org_allowed(self):
        from src.voice_agents.routes import create_agent
        from shared.voice_agents.models import VoiceAgentCreate

        profile = _agent_profile(is_org_admin_on=str(CREATE_AGENT_TEST_ORG))
        body = _agent_create_body(CREATE_AGENT_TEST_ORG)
        request = _make_post_request(body)
        agent_data = VoiceAgentCreate(**body)

        with patch("src.auth.dependencies.get_authenticated_user") as mock_auth, \
             patch("src.voice_agents.routes.voice_agent_service") as mock_svc:
            mock_auth.return_value = (CREATE_AGENT_TEST_USER, profile)
            created = Mock()
            created.id = UUID("00000000-0000-0000-0000-0000000000d4")
            created.organization_id = CREATE_AGENT_TEST_ORG
            mock_svc.create_agent = AsyncMock(return_value=(created, None))

            result = await create_agent(
                agent_data=agent_data,
                request=request,
                _auth=mock_auth.return_value,
            )
            assert result is not None
            mock_svc.create_agent.assert_called_once()

    @pytest.mark.asyncio
    async def test_org_admin_on_other_org_forbidden(self):
        """org_admin on ORG B, body says ORG A → 403.
        Uses TestClient with dependency_overrides so the
        `require_permission` factory actually runs."""
        from fastapi import APIRouter, Depends, FastAPI
        from fastapi.testclient import TestClient
        from src.voice_agents.routes import create_agent
        from src.auth.dependencies import require_permission

        profile = _agent_profile(is_org_admin_on=str(CREATE_AGENT_OTHER_ORG))

        # Build a minimal app with the create_agent route re-wired to
        # the factory. The wrapper calls the real `create_agent` so
        # the production route body runs end-to-end, but auth is
        # mediated by the factory via Depends() so dependency_overrides
        # takes effect.
        local_tracer = trace.get_tracer("test.create_agent")
        from shared.voice_agents.models import VoiceAgentCreate
        from src.voice_agents.routes import create_agent as real_create_agent

        async def _handler(
            agent_data: VoiceAgentCreate,
            request: Request,
            _auth=Depends(require_permission(
                "agent", "create",
                org_id_source="body", body_field="organization_id",
            )),
        ):
            # Forward to the real create_agent body, with the resolved
            # _auth tuple. The real route's own _auth default is unused
            # because we pass _auth explicitly here.
            return await real_create_agent(
                agent_data=agent_data, request=request, _auth=_auth,
            )

        router = APIRouter()
        router.post("/", response_model=None)(_handler)
        app = FastAPI()
        app.include_router(router)

        async def _override_auth():
            return (CREATE_AGENT_TEST_USER, profile)

        from src.auth.dependencies import get_authenticated_user as dep_get_auth
        app.dependency_overrides[dep_get_auth] = _override_auth

        client = TestClient(app)
        body = _agent_create_body(CREATE_AGENT_TEST_ORG)
        response = client.post(
            "/",
            json=body,
            headers={"authorization": "Bearer mock-jwt-token"},
        )
        assert response.status_code == 403, response.text

    @pytest.mark.asyncio
    async def test_regular_user_forbidden(self):
        """Regular user → 403 via TestClient + dependency_overrides."""
        from fastapi import APIRouter, Depends, FastAPI
        from fastapi.testclient import TestClient
        from src.voice_agents.routes import create_agent as real_create_agent
        from src.auth.dependencies import require_permission

        profile = _agent_profile()  # no admin anywhere

        local_tracer = trace.get_tracer("test.create_agent")
        from shared.voice_agents.models import VoiceAgentCreate

        async def _handler(
            agent_data: VoiceAgentCreate,
            request: Request,
            _auth=Depends(require_permission(
                "agent", "create",
                org_id_source="body", body_field="organization_id",
            )),
        ):
            return await real_create_agent(
                agent_data=agent_data, request=request, _auth=_auth,
            )

        router = APIRouter()
        router.post("/", response_model=None)(_handler)
        app = FastAPI()
        app.include_router(router)

        async def _override_auth():
            return (CREATE_AGENT_TEST_USER, profile)

        from src.auth.dependencies import get_authenticated_user as dep_get_auth
        app.dependency_overrides[dep_get_auth] = _override_auth

        client = TestClient(app)
        body = _agent_create_body(CREATE_AGENT_TEST_ORG)
        response = client.post(
            "/",
            json=body,
            headers={"authorization": "Bearer mock-jwt-token"},
        )
        assert response.status_code == 403, response.text
