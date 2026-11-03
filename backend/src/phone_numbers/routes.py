"""
API routes for phone number management.

Permission contract (see permission-matrix.md / N1 Epic C):

  - List organization numbers → ``phone_number:read``
  - Search available numbers  → ``phone_number:create`` (pricing is org-scoped)
  - Purchase                  → ``phone_number:create``
  - Assign to agent           → ``phone_number:update``
  - Cancel / release          → ``phone_number:delete``

These routes previously used ``check_billing_permissions``, which
allowed ``billing:subscribe`` holders to mutate phone inventory —
a consistency gap with the frontend ``canManagePhoneNumbers`` gate.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from src.auth.dependencies import assert_has_permission
from src.auth.middleware import get_authenticated_user
from src.auth.models import UserProfile
from src.security.rate_limiter import limiter

from shared.organization.phone_number_models import (
    PhoneNumberAssignRequest,
    PhoneNumberImportRequest,
    PhoneNumberImportResponse,
    PhoneNumberListResponse,
    PhoneNumberPurchaseRequest,
    PhoneNumberPurchaseResponse,
    PhoneNumberSearchMode,
    PhoneNumberSearchRequest,
    PhoneNumberSearchResponse,
    PhoneNumberWebhookDetailsResponse,
    PhoneNumberWithAgent,
)

from .maintenance_guard import phone_mutation_guard
from .platform_settings_models import (
    PlatformPhoneNumberSettings,
    PlatformPhoneNumberSettingsUpdate,
)
from .platform_settings_service import platform_phone_number_settings_service
from .service import (
    PHONE_NUMBER_PURCHASE_UNAVAILABLE,
    PHONE_NUMBER_SEARCH_UNAVAILABLE,
    phone_number_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/phone-numbers", tags=["phone-numbers"])


def _is_plan_limit_error(error: str) -> bool:
    """Recognize the entitlement service's stable plan-limit messages.

    Provider errors are also returned as strings by the service layer, so a
    broad substring check for ``"limit"`` can incorrectly turn a provider
    rate-limit failure into a customer billing error.
    """
    normalized = error.strip().lower()
    return normalized.startswith(("your plan allows ", "plan allows ", "plan limit '"))


def _assert_platform_admin(user_profile: UserProfile) -> None:
    """Require a platform administrator for global phone settings."""
    if not user_profile.has_role("platform_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only platform administrators can manage phone-number settings",
        )


@router.get("/admin/settings", response_model=PlatformPhoneNumberSettings)
async def get_platform_phone_number_settings(
    user_auth: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Return platform-admin phone-number billing and retry settings."""
    _user_id, user_profile = user_auth
    _assert_platform_admin(user_profile)
    return await platform_phone_number_settings_service.get_settings(
        allow_fallback=False
    )


@router.put("/admin/settings", response_model=PlatformPhoneNumberSettings)
async def update_platform_phone_number_settings(
    payload: PlatformPhoneNumberSettingsUpdate,
    user_auth: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Update platform-admin phone-number billing and retry settings."""
    user_id, user_profile = user_auth
    _assert_platform_admin(user_profile)
    return await platform_phone_number_settings_service.update_settings(
        payload, user_id
    )


@router.get("/available", response_model=PhoneNumberSearchResponse)
async def search_available_numbers(
    organization_id: UUID,
    country_code: str = "US",
    phone_number_type: str = "local",
    area_code: str | None = None,
    contains: str | None = None,
    search_mode: str = PhoneNumberSearchMode.CONTAINS.value,
    page: int = 1,
    page_size: int = 50,
    user_auth: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Search for available phone numbers.

    Returns a list of phone numbers available for purchase from the provider.
    Maximum 50 results per page. The caller needs ``phone_number:create`` so
    the response can accurately price the organization's included number.
    """
    try:
        _user_id, user_profile = user_auth
        assert_has_permission(
            user_profile,
            "phone_number",
            "create",
            organization_id,
            error_message="Insufficient permissions to search phone numbers",
        )
        if country_code.strip().upper() != "US":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only US platform-provided phone numbers are available in v1.",
            )
        search_request = PhoneNumberSearchRequest(
            country_code=country_code,
            phone_number_type=phone_number_type,
            area_code=area_code,
            contains=contains,
            search_mode=search_mode,
            page=page,
            page_size=min(page_size, 50),
        )

        result, error = await phone_number_service.search_available(
            search_request, organization_id
        )

        if error:
            if error.startswith(
                (
                    "Only US platform-provided",
                    "Mobile phone numbers are not available",
                )
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error,
                )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=PHONE_NUMBER_SEARCH_UNAVAILABLE,
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Unexpected phone number search failure (error_type=%s)",
            type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=PHONE_NUMBER_SEARCH_UNAVAILABLE,
        )


@router.post("/purchase", response_model=PhoneNumberPurchaseResponse)
@limiter.limit("3/hour")
async def purchase_phone_number(
    request: Request,
    purchase_request: PhoneNumberPurchaseRequest,
    organization_id: UUID,
    user_auth: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Purchase a phone number using credits.

    The organization must have sufficient credits to purchase the number.
    Credits are deducted immediately upon purchase.
    """
    try:
        _user_id, user_profile = user_auth
        assert_has_permission(
            user_profile,
            "phone_number",
            "create",
            organization_id,
            error_message="Insufficient permissions to purchase phone numbers",
        )
        async with phone_mutation_guard(organization_id):
            result, error = await phone_number_service.purchase_number(
                organization_id=organization_id,
                purchase_request=purchase_request,
                idempotency_key=request.headers.get("Idempotency-Key"),
            )

        if error:
            if error == PHONE_NUMBER_PURCHASE_UNAVAILABLE:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=PHONE_NUMBER_PURCHASE_UNAVAILABLE,
                )
            if error.strip().lower().startswith(
                "insufficient credits to purchase the phone number"
            ) or _is_plan_limit_error(error):
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail=error,
                )
            if (
                "idempotency key" in error.lower()
                or "already provisioning" in error.lower()
                or "awaiting provider release" in error.lower()
                or "purchase attempt has ended" in error.lower()
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=error,
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error,
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Phone number purchase route failed (error_type=%s)", type(e).__name__
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to purchase phone number",
        )


@router.post("/import", response_model=PhoneNumberImportResponse)
async def import_phone_number(
    import_request: PhoneNumberImportRequest,
    organization_id: UUID,
    user_auth: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Connect an existing customer-owned Twilio number without buying it."""
    try:
        _user_id, user_profile = user_auth
        assert_has_permission(
            user_profile,
            "phone_number",
            "create",
            organization_id,
            error_message="Insufficient permissions to connect phone numbers",
        )
        async with phone_mutation_guard(organization_id):
            result, error = await phone_number_service.import_number(
                organization_id=organization_id,
                import_request=import_request,
            )
        if error:
            if _is_plan_limit_error(error):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing phone number: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to connect phone number",
        )


@router.get("", response_model=PhoneNumberListResponse)
async def list_organization_numbers(
    organization_id: UUID,
    user_auth: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Get all phone numbers owned by an organization.

    Returns both assigned and unassigned phone numbers.
    """
    try:
        _user_id, user_profile = user_auth
        assert_has_permission(
            user_profile,
            "phone_number",
            "read",
            organization_id,
            error_message="Insufficient permissions to view phone numbers",
        )

        result, error = await phone_number_service.get_organization_numbers(
            organization_id=organization_id
        )

        if error:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error,
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing organization phone numbers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list phone numbers",
        )


@router.get("/agent/{agent_id}", response_model=PhoneNumberWithAgent | None)
async def get_agent_phone_number(
    agent_id: UUID,
    organization_id: UUID,
    user_auth: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Return the active phone number assigned to one organization agent."""
    try:
        _user_id, user_profile = user_auth
        assert_has_permission(
            user_profile,
            "phone_number",
            "read",
            organization_id,
            error_message="Insufficient permissions to view phone numbers",
        )

        result, error = await phone_number_service.get_agent_number(
            organization_id=organization_id,
            agent_id=agent_id,
        )
        if error:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error,
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error loading phone number for agent %s: %s", agent_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load phone number for agent",
        )


@router.get(
    "/{phone_number_id}/verification-details",
    response_model=PhoneNumberWebhookDetailsResponse,
)
async def get_phone_number_verification_details(
    phone_number_id: UUID,
    organization_id: UUID,
    user_auth: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Return pending customer-owned webhook URLs for a phone number."""
    try:
        _user_id, user_profile = user_auth
        assert_has_permission(
            user_profile,
            "phone_number",
            "read",
            organization_id,
            error_message="Insufficient permissions to view phone numbers",
        )

        result, error = await phone_number_service.get_verification_details(
            organization_id=organization_id,
            phone_number_id=phone_number_id,
        )
        if error:
            raise HTTPException(
                status_code=(
                    status.HTTP_404_NOT_FOUND
                    if error == "Phone number not found"
                    else status.HTTP_400_BAD_REQUEST
                ),
                detail=error,
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error loading verification details for phone number %s: %s",
            phone_number_id,
            e,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load phone-number verification details",
        )


@router.post("/{phone_number_id}/assign")
async def assign_phone_number_to_agent(
    phone_number_id: UUID,
    assign_request: PhoneNumberAssignRequest,
    organization_id: UUID,
    user_auth: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Assign a phone number to an agent.

    The phone number must be owned by the organization and not already assigned.
    """
    try:
        _user_id, user_profile = user_auth
        assert_has_permission(
            user_profile,
            "phone_number",
            "update",
            organization_id,
            error_message="Insufficient permissions to assign phone numbers",
        )

        async with phone_mutation_guard(organization_id):
            result, error = await phone_number_service.assign_to_agent(
                phone_number_id=phone_number_id,
                assign_request=assign_request,
                organization_id=organization_id,
            )

        if error:
            if "not found" in error.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=error,
                )
            if "already assigned" in error.lower():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=error,
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error,
            )

        return {"success": True, "phone_number": result}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning phone number: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assign phone number",
        )


@router.delete("/{phone_number_id}/assignment")
async def unassign_phone_number(
    phone_number_id: UUID,
    organization_id: UUID,
    user_auth: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Clear an agent mapping while keeping the organization number connected."""
    try:
        _user_id, user_profile = user_auth
        assert_has_permission(
            user_profile,
            "phone_number",
            "update",
            organization_id,
            error_message="Insufficient permissions to unassign phone numbers",
        )

        async with phone_mutation_guard(organization_id):
            result, error = await phone_number_service.unassign_from_agent(
                phone_number_id=phone_number_id,
                organization_id=organization_id,
            )
        if error:
            if "not found" in error.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=error,
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error,
            )
        return {"success": True, "phone_number": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unassigning phone number: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unassign phone number",
        )


@router.delete("/{phone_number_id}")
async def cancel_phone_number(
    phone_number_id: UUID,
    organization_id: UUID,
    user_auth: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Cancel (release) a phone number.

    Warning: This will release the number immediately and calls will stop working.
    No refund is provided for the current billing period.
    """
    try:
        _user_id, user_profile = user_auth
        assert_has_permission(
            user_profile,
            "phone_number",
            "delete",
            organization_id,
            error_message="Insufficient permissions to cancel phone numbers",
        )

        async with phone_mutation_guard(organization_id):
            success, error = await phone_number_service.cancel_number(
                phone_number_id=phone_number_id,
                organization_id=organization_id,
            )

        if error and error != "release_pending":
            if "not found" in error.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=error,
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error,
            )

        if error == "release_pending":
            return {
                "success": True,
                "message": "Release queued. We will retry with the provider automatically.",
            }

        return {
            "success": True,
            "message": "Phone number disconnected or released. Calls will not work.",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling phone number: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel phone number",
        )
