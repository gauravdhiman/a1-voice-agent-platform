"""Tests for the unauthenticated legal document read route."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from fastapi import HTTPException
from src.legal.models import LegalDocumentPublic
from src.legal.public_routes import get_published_legal_document

TEST_VERSION_ID = UUID("00000000-0000-0000-0000-000000000071")


def _public_doc(document_key: str = "terms") -> LegalDocumentPublic:
    return LegalDocumentPublic(
        document_key=document_key,
        title="Terms & Conditions" if document_key == "terms" else "Privacy Policy",
        version_number=2,
        content_markdown="# current",
        published_at=datetime.now(timezone.utc),
    )


class TestPublicLegalRoute:
    @pytest.mark.asyncio
    async def test_returns_current_published_document_with_title(self):
        with patch("src.legal.public_routes.legal_service") as mock_svc:
            expected = _public_doc()
            mock_svc.get_published_document = AsyncMock(return_value=expected)
            result = await get_published_legal_document("terms")

        assert result is expected
        assert result.title == "Terms & Conditions"
        mock_svc.get_published_document.assert_awaited_once_with("terms")

    @pytest.mark.asyncio
    async def test_missing_published_version_maps_to_404(self):
        with patch("src.legal.public_routes.legal_service") as mock_svc:
            mock_svc.get_published_document = AsyncMock(
                side_effect=ValueError("No published terms document")
            )
            with pytest.raises(HTTPException) as exc_info:
                await get_published_legal_document("terms")

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "No published version of 'terms' is available"

    @pytest.mark.asyncio
    async def test_unexpected_error_maps_to_500(self):
        with patch("src.legal.public_routes.legal_service") as mock_svc:
            mock_svc.get_published_document = AsyncMock(side_effect=RuntimeError("db"))
            with pytest.raises(HTTPException) as exc_info:
                await get_published_legal_document("privacy")

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Failed to load legal document"
