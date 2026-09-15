"""Tests for public demo rating submission and the admin overview."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from starlette.requests import Request

TEST_AGENT_ID = UUID("00000000-0000-0000-0000-000000000101")
TEST_ORG_ID = UUID("00000000-0000-0000-0000-000000000020")


def _make_request() -> Request:
    """Build the minimal request object required by SlowAPI in direct tests."""
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/api/v1/public/demo/my-demo/feedback",
            "raw_path": b"/api/v1/public/demo/my-demo/feedback",
            "query_string": b"",
            "headers": [],
            "client": ("198.51.100.1", 50000),
            "server": ("testserver", 80),
        }
    )


def _make_profile(is_platform_admin: bool = False):
    profile = Mock()
    profile.has_role = Mock(
        side_effect=lambda role, oid=None: role == "platform_admin"
        and is_platform_admin
    )
    return profile


def _make_agent():
    agent = Mock()
    agent.id = TEST_AGENT_ID
    agent.organization_id = TEST_ORG_ID
    return agent


def _claims():
    return SimpleNamespace(
        session_id="session-1",
        agent_id=str(TEST_AGENT_ID),
        demo_slug="copper-ridge-service-request",
    )


class TestSubmitDemoFeedback:
    """POST /api/v1/public/demo/{slug}/feedback."""

    @pytest.mark.asyncio
    async def test_records_rating_for_verified_session(self):
        from src.voice_agents.demo_public_routes import (
            DemoFeedbackRequest,
            submit_demo_feedback,
        )

        with (
            patch(
                "src.voice_agents.demo_public_routes.verify_demo_outcome_token",
                return_value=_claims(),
            ),
            patch(
                "src.voice_agents.demo_public_routes.voice_agent_service"
            ) as agent_service,
            patch(
                "src.voice_agents.demo_public_routes.demo_feedback_service"
            ) as feedback_service,
        ):
            agent_service.get_demo_agent_by_slug = AsyncMock(
                return_value=(_make_agent(), None)
            )
            feedback_service.submit = AsyncMock(return_value=True)

            result = await submit_demo_feedback(
                "copper-ridge-service-request",
                _make_request(),
                DemoFeedbackRequest(rating=5),
                token="receipt-token",
            )

            assert result.received is True
            feedback_service.submit.assert_awaited_once_with(
                session_id="session-1",
                agent_id=str(TEST_AGENT_ID),
                organization_id=str(TEST_ORG_ID),
                demo_slug="copper-ridge-service-request",
                rating=5,
            )

    @pytest.mark.asyncio
    async def test_rejects_out_of_range_rating(self):
        from src.voice_agents.demo_public_routes import (
            DemoFeedbackRequest,
            submit_demo_feedback,
        )

        with pytest.raises(HTTPException) as exc_info:
            await submit_demo_feedback(
                "copper-ridge-service-request",
                _make_request(),
                DemoFeedbackRequest(rating=9),
                token="receipt-token",
            )
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_rejects_unknown_session_token(self):
        from src.voice_agents.demo_public_routes import (
            DemoFeedbackRequest,
            submit_demo_feedback,
        )

        with patch(
            "src.voice_agents.demo_public_routes.verify_demo_outcome_token",
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await submit_demo_feedback(
                    "copper-ridge-service-request",
                    _make_request(),
                    DemoFeedbackRequest(rating=4),
                    token="bad-token",
                )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_storage_failure_maps_to_500(self):
        from src.voice_agents.demo_public_routes import (
            DemoFeedbackRequest,
            submit_demo_feedback,
        )

        with (
            patch(
                "src.voice_agents.demo_public_routes.verify_demo_outcome_token",
                return_value=_claims(),
            ),
            patch(
                "src.voice_agents.demo_public_routes.voice_agent_service"
            ) as agent_service,
            patch(
                "src.voice_agents.demo_public_routes.demo_feedback_service"
            ) as feedback_service,
        ):
            agent_service.get_demo_agent_by_slug = AsyncMock(
                return_value=(_make_agent(), None)
            )
            feedback_service.submit = AsyncMock(return_value=False)

            with pytest.raises(HTTPException) as exc_info:
                await submit_demo_feedback(
                    "copper-ridge-service-request",
                    _make_request(),
                    DemoFeedbackRequest(rating=4),
                    token="receipt-token",
                )
        assert exc_info.value.status_code == 500


class TestListDemoFeedback:
    """GET /api/v1/leads/demo-feedback."""

    @pytest.mark.asyncio
    async def test_platform_admin_sees_summary_and_recent(self):
        from src.leads.routes import list_demo_feedback

        summary = [Mock(demo_slug="demo-one", count=2, average_rating=4.5)]
        recent = [
            Mock(
                id="feedback-1",
                session_id="session-1",
                agent_id="agent-1",
                organization_id="org-1",
                demo_slug="demo-one",
                rating=5,
                created_at="2026-09-14T10:00:00Z",
            )
        ]
        with (
            patch(
                "src.leads.routes.demo_feedback_service.summary",
                new=AsyncMock(return_value=summary),
            ),
            patch(
                "src.leads.routes.demo_feedback_service.recent",
                new=AsyncMock(return_value=recent),
            ),
        ):
            result = await list_demo_feedback(
                request=_make_request(),
                user_data=(uuid4(), _make_profile(is_platform_admin=True)),
            )

        assert result.summary[0].demo_slug == "demo-one"
        assert result.summary[0].average_rating == 4.5
        assert result.recent[0].rating == 5

    @pytest.mark.asyncio
    async def test_regular_user_is_denied(self):
        from src.leads.routes import list_demo_feedback

        with pytest.raises(HTTPException) as exc_info:
            await list_demo_feedback(
                request=_make_request(),
                user_data=(uuid4(), _make_profile(is_platform_admin=False)),
            )
        assert exc_info.value.status_code == 403
