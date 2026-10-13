"""Public routes for reading the current published legal documents."""

import logging

from fastapi import APIRouter, HTTPException, status
from src.legal.models import LegalDocumentKey, LegalDocumentPublic
from src.legal.service import legal_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/legal", tags=["legal"])


@router.get(
    "/{document_key}",
    response_model=LegalDocumentPublic,
)
async def get_published_legal_document(document_key: LegalDocumentKey):
    """Return the latest published version of a legal document.

    Unauthenticated. The response always reflects the current published version
    so visitors see the same text that acceptance is recorded against.
    """
    try:
        return await legal_service.get_published_document(document_key)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No published version of '{document_key}' is available",
        )
    except Exception as exc:
        logger.error("Error reading published legal document %s: %s", document_key, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load legal document",
        )
