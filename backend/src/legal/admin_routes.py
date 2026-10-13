"""Platform-admin API routes for legal document version management.

Routes require the ``platform_admin`` role. Draft CRUD delegates to
``LegalDocumentService``; publishing optionally queues a durable per-user
notification dispatch.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from src.auth.dependencies import assert_platform_role
from src.auth.middleware import get_authenticated_user
from src.auth.models import UserProfile
from src.legal.models import (
    LegalDocumentKey,
    LegalDocumentVersionDetail,
    LegalDocumentVersionSummary,
    LegalDraftCreate,
    LegalDraftUpdate,
    LegalPublishRequest,
    LegalPublishResult,
)
from src.legal.service import legal_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin/legal", tags=["admin-legal"])


def _require_platform_admin(user_profile: UserProfile) -> None:
    """Raise 403 unless the caller is a platform admin."""
    assert_platform_role(
        user_profile,
        "platform_admin",
        error_message="User does not have permission to manage legal documents",
    )


@router.get(
    "/{document_key}/versions",
    response_model=list[LegalDocumentVersionSummary],
)
async def list_legal_document_versions(
    document_key: LegalDocumentKey,
    user_auth: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """List version history for a legal document, newest first."""
    _, user_profile = user_auth
    _require_platform_admin(user_profile)
    try:
        return await legal_service.list_versions(document_key)
    except Exception as exc:
        logger.error(
            "Error listing legal document versions for %s: %s", document_key, exc
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list legal document versions",
        )


@router.get(
    "/versions/{version_id}",
    response_model=LegalDocumentVersionDetail,
)
async def get_legal_document_version(
    version_id: UUID,
    user_auth: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Fetch one legal document version including its content."""
    _, user_profile = user_auth
    _require_platform_admin(user_profile)
    try:
        return await legal_service.get_version(version_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        logger.error("Error reading legal document version %s: %s", version_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load legal document version",
        )


@router.post(
    "/{document_key}/draft",
    response_model=LegalDocumentVersionDetail,
    status_code=status.HTTP_201_CREATED,
)
async def create_legal_document_draft(
    document_key: LegalDocumentKey,
    body: LegalDraftCreate,
    user_auth: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Create the next draft version, optionally seeded with content."""
    user_id, user_profile = user_auth
    _require_platform_admin(user_profile)
    try:
        return await legal_service.create_draft(
            document_key,
            content_markdown=body.content_markdown,
            summary_of_changes=body.summary_of_changes,
            created_by=user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except Exception as exc:
        logger.error("Error creating legal draft for %s: %s", document_key, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create legal document draft",
        )


@router.put(
    "/versions/{version_id}",
    response_model=LegalDocumentVersionDetail,
)
async def update_legal_document_draft(
    version_id: UUID,
    body: LegalDraftUpdate,
    user_auth: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Update the content of an existing draft version."""
    _, user_profile = user_auth
    _require_platform_admin(user_profile)
    try:
        return await legal_service.update_draft(
            version_id,
            content_markdown=body.content_markdown,
            summary_of_changes=body.summary_of_changes,
        )
    except ValueError as exc:
        message = str(exc)
        code = (
            status.HTTP_404_NOT_FOUND
            if "not found" in message
            else status.HTTP_409_CONFLICT
        )
        raise HTTPException(status_code=code, detail=message)
    except Exception as exc:
        logger.error("Error updating legal draft %s: %s", version_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update legal document draft",
        )


@router.delete(
    "/versions/{version_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_legal_document_draft(
    version_id: UUID,
    user_auth: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Delete a draft version. Published history is never deleted."""
    _, user_profile = user_auth
    _require_platform_admin(user_profile)
    try:
        await legal_service.delete_draft(version_id)
    except ValueError as exc:
        message = str(exc)
        code = (
            status.HTTP_404_NOT_FOUND
            if "not found" in message
            else status.HTTP_409_CONFLICT
        )
        raise HTTPException(status_code=code, detail=message)
    except Exception as exc:
        logger.error("Error deleting legal draft %s: %s", version_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete legal document draft",
        )


@router.post(
    "/versions/{version_id}/publish",
    response_model=LegalPublishResult,
)
async def publish_legal_document_version(
    version_id: UUID,
    body: LegalPublishRequest,
    user_auth: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Publish a draft and optionally queue update emails for all signed-up users."""
    user_id, user_profile = user_auth
    _require_platform_admin(user_profile)
    try:
        return await legal_service.publish_version(
            version_id,
            body,
            published_by=user_id,
        )
    except ValueError as exc:
        message = str(exc)
        code = (
            status.HTTP_404_NOT_FOUND
            if "not found" in message
            else status.HTTP_409_CONFLICT
        )
        raise HTTPException(status_code=code, detail=message)
    except Exception as exc:
        logger.error("Error publishing legal document version %s: %s", version_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to publish legal document version",
        )
