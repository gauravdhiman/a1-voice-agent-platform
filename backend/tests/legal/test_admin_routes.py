"""Tests for the platform-admin legal document routes.

Authorization is exercised per route through the ``platform_admin`` role gate;
error mapping pins the precedence contract: a ``ValueError`` whose message
contains ``not found`` maps to 404, every other ``ValueError`` maps to 409.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID

import pytest
from fastapi import HTTPException
from src.auth.middleware import get_authenticated_user
from src.legal.models import (
    LegalDocumentVersionDetail,
    LegalDocumentVersionSummary,
    LegalDraftCreate,
    LegalDraftUpdate,
    LegalPublishRequest,
    LegalPublishResult,
    LegalVersionStatus,
)

TEST_USER_ID = UUID("00000000-0000-0000-0000-000000000004")
TEST_VERSION_ID = UUID("00000000-0000-0000-0000-000000000061")
TEST_EVENT_ID = UUID("00000000-0000-0000-0000-000000000062")


def _profile(is_admin: bool) -> Mock:
    p = Mock()
    p.has_role = Mock(return_value=is_admin)
    return p


ADMIN_AUTH = (TEST_USER_ID, _profile(True))
DENIED_AUTH = (TEST_USER_ID, _profile(False))


def _detail() -> LegalDocumentVersionDetail:
    now = datetime.now(timezone.utc)
    return LegalDocumentVersionDetail(
        id=TEST_VERSION_ID,
        document_key="terms",
        version_number=2,
        status=LegalVersionStatus.DRAFT,
        is_current=False,
        summary_of_changes=None,
        published_at=None,
        published_by=None,
        created_by=TEST_USER_ID,
        created_at=now,
        updated_at=now,
        content_markdown="# draft",
    )


def _publish_result() -> LegalPublishResult:
    return LegalPublishResult(
        version=_detail().model_copy(
            update={"status": LegalVersionStatus.PUBLISHED, "is_current": True}
        ),
        publish_event_id=TEST_EVENT_ID,
        notified_count=3,
        dispatch_id=UUID("00000000-0000-0000-0000-000000000063"),
    )


class TestAdminLegalRoutesAuthz:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("handler", "kwargs"),
        [
            ("list_legal_document_versions", {"document_key": "terms"}),
            ("get_legal_document_version", {"version_id": TEST_VERSION_ID}),
            (
                "create_legal_document_draft",
                {"document_key": "terms", "body": LegalDraftCreate()},
            ),
            (
                "update_legal_document_draft",
                {
                    "version_id": TEST_VERSION_ID,
                    "body": LegalDraftUpdate(content_markdown="# x"),
                },
            ),
            ("delete_legal_document_draft", {"version_id": TEST_VERSION_ID}),
            (
                "publish_legal_document_version",
                {"version_id": TEST_VERSION_ID, "body": LegalPublishRequest()},
            ),
        ],
    )
    async def test_non_platform_admin_gets_403(self, handler, kwargs):
        from src.legal import admin_routes

        with pytest.raises(HTTPException) as exc_info:
            await getattr(admin_routes, handler)(**kwargs, user_auth=DENIED_AUTH)
        assert exc_info.value.status_code == 403
        assert (
            exc_info.value.detail
            == "User does not have permission to manage legal documents"
        )

    @pytest.mark.asyncio
    async def test_missing_authorization_header_is_rejected(self):
        with pytest.raises(HTTPException) as exc_info:
            await get_authenticated_user(authorization=None)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_non_admin_denial_precedes_service_calls(self):
        from src.legal import admin_routes

        with patch("src.legal.admin_routes.legal_service") as mock_svc:
            mock_svc.delete_draft = AsyncMock()
            with pytest.raises(HTTPException) as exc_info:
                await admin_routes.delete_legal_document_draft(
                    TEST_VERSION_ID, user_auth=DENIED_AUTH
                )
            assert exc_info.value.status_code == 403
            mock_svc.delete_draft.assert_not_called()


class TestAdminLegalRoutesDrafts:
    @pytest.mark.asyncio
    async def test_create_draft_passes_admin_identity(self):
        from src.legal.admin_routes import create_legal_document_draft

        with patch("src.legal.admin_routes.legal_service") as mock_svc:
            expected = _detail()
            mock_svc.create_draft = AsyncMock(return_value=expected)
            result = await create_legal_document_draft(
                "terms",
                LegalDraftCreate(content_markdown="# draft", summary_of_changes="init"),
                user_auth=ADMIN_AUTH,
            )
        assert result is expected
        mock_svc.create_draft.assert_awaited_once_with(
            "terms",
            content_markdown="# draft",
            summary_of_changes="init",
            created_by=TEST_USER_ID,
        )

    @pytest.mark.asyncio
    async def test_create_draft_conflict_maps_to_409(self):
        from src.legal.admin_routes import create_legal_document_draft

        with patch("src.legal.admin_routes.legal_service") as mock_svc:
            mock_svc.create_draft = AsyncMock(
                side_effect=ValueError("A draft version of 'terms' already exists.")
            )
            with pytest.raises(HTTPException) as exc_info:
                await create_legal_document_draft(
                    "terms", LegalDraftCreate(), user_auth=ADMIN_AUTH
                )
        assert exc_info.value.status_code == 409
        assert "already exists" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_update_missing_version_maps_to_404(self):
        from src.legal.admin_routes import update_legal_document_draft

        with patch("src.legal.admin_routes.legal_service") as mock_svc:
            mock_svc.update_draft = AsyncMock(
                side_effect=ValueError(
                    f"Legal document version {TEST_VERSION_ID} not found"
                )
            )
            with pytest.raises(HTTPException) as exc_info:
                await update_legal_document_draft(
                    TEST_VERSION_ID,
                    LegalDraftUpdate(content_markdown="# x"),
                    user_auth=ADMIN_AUTH,
                )
        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_update_non_draft_maps_to_409(self):
        from src.legal.admin_routes import update_legal_document_draft

        with patch("src.legal.admin_routes.legal_service") as mock_svc:
            mock_svc.update_draft = AsyncMock(
                side_effect=ValueError(
                    f"Version {TEST_VERSION_ID} is not a draft (status=published)"
                )
            )
            with pytest.raises(HTTPException) as exc_info:
                await update_legal_document_draft(
                    TEST_VERSION_ID,
                    LegalDraftUpdate(content_markdown="# x"),
                    user_auth=ADMIN_AUTH,
                )
        assert exc_info.value.status_code == 409
        assert "is not a draft" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_delete_non_draft_maps_to_409(self):
        from src.legal.admin_routes import delete_legal_document_draft

        with patch("src.legal.admin_routes.legal_service") as mock_svc:
            mock_svc.delete_draft = AsyncMock(
                side_effect=ValueError(f"Version {TEST_VERSION_ID} is not a draft")
            )
            with pytest.raises(HTTPException) as exc_info:
                await delete_legal_document_draft(TEST_VERSION_ID, user_auth=ADMIN_AUTH)
        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_delete_missing_version_maps_to_404(self):
        from src.legal.admin_routes import delete_legal_document_draft

        with patch("src.legal.admin_routes.legal_service") as mock_svc:
            mock_svc.delete_draft = AsyncMock(
                side_effect=ValueError("Legal document version missing not found")
            )
            with pytest.raises(HTTPException) as exc_info:
                await delete_legal_document_draft(TEST_VERSION_ID, user_auth=ADMIN_AUTH)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_draft_success_returns_none(self):
        from src.legal.admin_routes import delete_legal_document_draft

        with patch("src.legal.admin_routes.legal_service") as mock_svc:
            mock_svc.delete_draft = AsyncMock(return_value=None)
            result = await delete_legal_document_draft(
                TEST_VERSION_ID, user_auth=ADMIN_AUTH
            )
        assert result is None
        mock_svc.delete_draft.assert_awaited_once_with(TEST_VERSION_ID)


class TestAdminLegalRoutesReads:
    @pytest.mark.asyncio
    async def test_list_versions_delegates_document_key(self):
        from src.legal.admin_routes import list_legal_document_versions

        now = datetime.now(timezone.utc)
        summary = LegalDocumentVersionSummary(
            id=TEST_VERSION_ID,
            document_key="privacy",
            version_number=1,
            status=LegalVersionStatus.PUBLISHED,
            is_current=True,
            created_at=now,
            updated_at=now,
        )
        with patch("src.legal.admin_routes.legal_service") as mock_svc:
            mock_svc.list_versions = AsyncMock(return_value=[summary])
            result = await list_legal_document_versions("privacy", user_auth=ADMIN_AUTH)
        assert result == [summary]
        mock_svc.list_versions.assert_awaited_once_with("privacy")

    @pytest.mark.asyncio
    async def test_get_version_missing_maps_to_404(self):
        from src.legal.admin_routes import get_legal_document_version

        with patch("src.legal.admin_routes.legal_service") as mock_svc:
            mock_svc.get_version = AsyncMock(side_effect=ValueError("gone not found"))
            with pytest.raises(HTTPException) as exc_info:
                await get_legal_document_version(TEST_VERSION_ID, user_auth=ADMIN_AUTH)
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "gone not found"


class TestAdminLegalRoutesPublish:
    @pytest.mark.asyncio
    async def test_publish_result_is_passed_through(self):
        from src.legal.admin_routes import publish_legal_document_version

        expected = _publish_result()
        with patch("src.legal.admin_routes.legal_service") as mock_svc:
            mock_svc.publish_version = AsyncMock(return_value=expected)
            result = await publish_legal_document_version(
                TEST_VERSION_ID,
                LegalPublishRequest(notify_users=True),
                user_auth=ADMIN_AUTH,
            )
        assert result is expected
        assert isinstance(result, LegalPublishResult)
        assert result.publish_event_id == TEST_EVENT_ID
        assert result.notified_count == 3
        assert result.dispatch_id is not None
        mock_svc.publish_version.assert_awaited_once_with(
            TEST_VERSION_ID,
            LegalPublishRequest(notify_users=True),
            published_by=TEST_USER_ID,
        )

    @pytest.mark.asyncio
    async def test_publish_non_draft_maps_to_409(self):
        from src.legal.admin_routes import publish_legal_document_version

        with patch("src.legal.admin_routes.legal_service") as mock_svc:
            mock_svc.publish_version = AsyncMock(
                side_effect=ValueError(f"Version {TEST_VERSION_ID} is not a draft")
            )
            with pytest.raises(HTTPException) as exc_info:
                await publish_legal_document_version(
                    TEST_VERSION_ID, LegalPublishRequest(), user_auth=ADMIN_AUTH
                )
        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_publish_missing_version_maps_to_404(self):
        from src.legal.admin_routes import publish_legal_document_version

        with patch("src.legal.admin_routes.legal_service") as mock_svc:
            mock_svc.publish_version = AsyncMock(
                side_effect=ValueError("Legal document version x not found")
            )
            with pytest.raises(HTTPException) as exc_info:
                await publish_legal_document_version(
                    TEST_VERSION_ID, LegalPublishRequest(), user_auth=ADMIN_AUTH
                )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_publish_unexpected_error_maps_to_500(self):
        from src.legal.admin_routes import publish_legal_document_version

        with patch("src.legal.admin_routes.legal_service") as mock_svc:
            mock_svc.publish_version = AsyncMock(side_effect=RuntimeError("db down"))
            with pytest.raises(HTTPException) as exc_info:
                await publish_legal_document_version(
                    TEST_VERSION_ID, LegalPublishRequest(), user_auth=ADMIN_AUTH
                )
        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Failed to publish legal document version"
