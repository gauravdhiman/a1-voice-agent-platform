"""
Platform admin API routes for plan product versioning and catalog management.

Routes require ``platform_admin`` role. Publish workflow delegates to
``PlanVersionService``; draft CRUD uses ``AdminPlanCatalogService``.

See ``docs/03_implementation/plan_entitlements_and_limits.md`` §10.3.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from src.auth.dependencies import assert_platform_role
from src.auth.middleware import get_authenticated_user
from src.auth.models import UserProfile
from src.billing.admin_plan_catalog_service import admin_plan_catalog_service
from src.billing.admin_plan_models import (
    EntitlementDefinitionUpdate,
    PlanProduct,
    PlanProductCreate,
    PlanProductWithVersions,
    PlanVersionCloneRequest,
    PlanVersionDetail,
    PlanVersionDraftCreate,
    PlanVersionDraftUpdate,
)
from src.billing.entitlement_models import EntitlementDefinition
from src.billing.plan_version_models import (
    PlanVersionPublishRequest,
    PlanVersionPublishResult,
)
from src.billing.plan_version_service import plan_version_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin-plans"])


def _require_platform_admin(user_profile: UserProfile) -> None:
    """Raise 403 unless the caller is a platform admin."""
    assert_platform_role(
        user_profile,
        "platform_admin",
        error_message="User does not have permission to manage plan catalog",
    )


@router.get(
    "/entitlement-definitions",
    response_model=list[EntitlementDefinition],
)
async def list_entitlement_definitions(
    active_only: bool = Query(default=False),
    user_auth: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """List entitlement catalog entries for the admin editor."""
    _, user_profile = user_auth
    _require_platform_admin(user_profile)
    try:
        return await admin_plan_catalog_service.list_entitlement_definitions(
            active_only=active_only
        )
    except Exception as exc:
        logger.error("Error listing entitlement definitions: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list entitlement definitions",
        )


@router.patch(
    "/entitlement-definitions/{key}",
    response_model=EntitlementDefinition,
)
async def update_entitlement_definition(
    key: str,
    body: EntitlementDefinitionUpdate,
    user_auth: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Update display metadata on a catalog definition."""
    _, user_profile = user_auth
    _require_platform_admin(user_profile)
    try:
        return await admin_plan_catalog_service.update_entitlement_definition(
            key, body
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        logger.error("Error updating entitlement definition %s: %s", key, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update entitlement definition",
        )


@router.get("/plan-products", response_model=list[PlanProductWithVersions])
async def list_plan_products(
    user_auth: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """List plan products with nested versions."""
    _, user_profile = user_auth
    _require_platform_admin(user_profile)
    try:
        return await admin_plan_catalog_service.list_plan_products()
    except Exception as exc:
        logger.error("Error listing plan products: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list plan products",
        )


@router.post(
    "/plan-products",
    response_model=PlanProduct,
    status_code=status.HTTP_201_CREATED,
)
async def create_plan_product(
    body: PlanProductCreate,
    user_auth: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Create a new plan product family."""
    _, user_profile = user_auth
    _require_platform_admin(user_profile)
    try:
        return await admin_plan_catalog_service.create_plan_product(body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        logger.error("Error creating plan product: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create plan product",
        )


@router.post(
    "/plan-products/{product_id}/versions",
    response_model=PlanVersionDetail,
    status_code=status.HTTP_201_CREATED,
)
async def create_draft_plan_version(
    product_id: UUID,
    body: PlanVersionDraftCreate,
    user_auth: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Create a draft plan version for a product."""
    _, user_profile = user_auth
    _require_platform_admin(user_profile)
    try:
        return await admin_plan_catalog_service.create_draft_version(product_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        logger.error(
            "Error creating draft version for product %s: %s", product_id, exc
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create draft plan version",
        )


@router.get("/plan-versions/{plan_version_id}", response_model=PlanVersionDetail)
async def get_plan_version(
    plan_version_id: UUID,
    user_auth: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Fetch a plan version with entitlements."""
    _, user_profile = user_auth
    _require_platform_admin(user_profile)
    try:
        return await admin_plan_catalog_service.get_plan_version(plan_version_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        logger.error("Error fetching plan version %s: %s", plan_version_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch plan version",
        )


@router.put("/plan-versions/{plan_version_id}", response_model=PlanVersionDetail)
async def update_draft_plan_version(
    plan_version_id: UUID,
    body: PlanVersionDraftUpdate,
    user_auth: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Update a draft plan version (immutable once published)."""
    _, user_profile = user_auth
    _require_platform_admin(user_profile)
    try:
        return await admin_plan_catalog_service.update_draft_version(
            plan_version_id, body
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        logger.error("Error updating plan version %s: %s", plan_version_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update plan version",
        )


@router.post(
    "/plan-versions/{plan_version_id}/clone",
    response_model=PlanVersionDetail,
    status_code=status.HTTP_201_CREATED,
)
async def clone_plan_version(
    plan_version_id: UUID,
    body: PlanVersionCloneRequest,
    user_auth: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Clone any version into a new draft with incremented version number."""
    _, user_profile = user_auth
    _require_platform_admin(user_profile)
    try:
        return await admin_plan_catalog_service.clone_plan_version(
            plan_version_id,
            display_label=body.display_label,
            price_amount_cents=body.price_amount_cents,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        logger.error("Error cloning plan version %s: %s", plan_version_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clone plan version",
        )


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

    _require_platform_admin(user_profile)

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
