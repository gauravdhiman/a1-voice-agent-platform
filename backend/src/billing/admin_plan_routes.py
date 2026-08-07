"""
Platform admin API routes for plan product versioning.

Routes require ``platform_admin`` role. Phase 2 exposes publish workflow;
full CRUD editor UI lands in Phase 4.

See ``docs/03_implementation/plan_entitlements_and_limits.md`` §10.3.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from src.auth.dependencies import assert_platform_role
from src.auth.middleware import get_authenticated_user
from src.auth.models import UserProfile
from src.billing.plan_version_models import (
    PlanVersionPublishRequest,
    PlanVersionPublishResult,
)
from src.billing.plan_version_service import plan_version_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin-plans"])


@router.post(
    "/plan-versions/{plan_version_id}/publish",
    response_model=PlanVersionPublishResult,
)
async def publish_plan_version(
    plan_version_id: UUID,
    request: PlanVersionPublishRequest,
    user_auth: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Publish a draft plan version and apply migration policy.

    Marks the version as current for new signups, deprecates the prior signup
    version, records a publish event, and optionally queues subscriber migrations.
    Existing subscribers keep their bound ``plan_version_id`` unless migration
    mode is ``immediate_required``.

    Args:
        plan_version_id: Draft plan version UUID to publish.
        request: Migration policy configuration.
        user_auth: Authenticated platform admin.

    Returns:
        PlanVersionPublishResult with publish event and migration counts.
    """
    user_id, user_profile = user_auth

    assert_platform_role(
        user_profile,
        "platform_admin",
        error_message="User does not have permission to publish plan versions",
    )

    try:
        return await plan_version_service.publish_plan_version(
            plan_version_id,
            request,
            published_by=user_id,
        )
    except ValueError as exc:
        logger.warning("Plan version publish rejected: %s", exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        logger.error("Error publishing plan version %s: %s", plan_version_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to publish plan version",
        )
