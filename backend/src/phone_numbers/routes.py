"""
API routes for phone number management.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from src.auth.middleware import check_billing_permissions, get_authenticated_user
from src.auth.models import UserProfile
from src.security.rate_limiter import limiter

from shared.organization.phone_number_models import (
    PhoneNumberAssignRequest,
    PhoneNumberListResponse,
    PhoneNumberPurchaseRequest,
    PhoneNumberPurchaseResponse,
    PhoneNumberSearchRequest,
    PhoneNumberSearchResponse,
)

from .service import phone_number_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/phone-numbers", tags=["phone-numbers"])


@router.get("/available", response_model=PhoneNumberSearchResponse)
async def search_available_numbers(
    country_code: str = "US",
    phone_number_type: str = "local",
    area_code: str | None = None,
    contains: str | None = None,
    page: int = 1,
    page_size: int = 50,
    user_auth: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Search for available phone numbers.

    Returns a list of phone numbers available for purchase from the provider.
    Maximum 50 results per page.
    """
    try:
        search_request = PhoneNumberSearchRequest(
            country_code=country_code,
            phone_number_type=phone_number_type,
            area_code=area_code,
            contains=contains,
            page=page,
            page_size=min(page_size, 50),
        )

        result, error = await phone_number_service.search_available(search_request)

        if error:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error,
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching available numbers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search available numbers",
        )


@router.post("/purchase", response_model=PhoneNumberPurchaseResponse)
@limiter.limit("3/hour")
async def purchase_phone_number(
    http_request: Request,
    purchase_request: PhoneNumberPurchaseRequest,
    organization_id: UUID,
    user_auth: tuple[UUID, UserProfile] = Depends(check_billing_permissions),
):
    """Purchase a phone number using credits.

    The organization must have sufficient credits to purchase the number.
    Credits are deducted immediately upon purchase.
    """
    try:
        user_id, user_profile = user_auth

        result, error = await phone_number_service.purchase_number(
            organization_id=organization_id,
            purchase_request=purchase_request,
        )

        if error:
            if "Insufficient credits" in error:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
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
        logger.error(f"Error purchasing phone number: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to purchase phone number",
        )


@router.get("", response_model=PhoneNumberListResponse)
async def list_organization_numbers(
    organization_id: UUID,
    user_auth: tuple[UUID, UserProfile] = Depends(check_billing_permissions),
):
    """Get all phone numbers owned by an organization.

    Returns both assigned and unassigned phone numbers.
    """
    try:
        user_id, user_profile = user_auth

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


@router.post("/{phone_number_id}/assign")
async def assign_phone_number_to_agent(
    phone_number_id: UUID,
    assign_request: PhoneNumberAssignRequest,
    organization_id: UUID,
    user_auth: tuple[UUID, UserProfile] = Depends(check_billing_permissions),
):
    """Assign a phone number to an agent.

    The phone number must be owned by the organization and not already assigned.
    """
    try:
        user_id, user_profile = user_auth

        result, error = await phone_number_service.assign_to_agent(
            phone_number_id=phone_number_id,
            assign_request=assign_request,
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


@router.delete("/{phone_number_id}")
async def cancel_phone_number(
    phone_number_id: UUID,
    organization_id: UUID,
    user_auth: tuple[UUID, UserProfile] = Depends(check_billing_permissions),
):
    """Cancel (release) a phone number.

    Warning: This will release the number immediately and calls will stop working.
    No refund is provided for the current billing period.
    """
    try:
        user_id, user_profile = user_auth

        success, error = await phone_number_service.cancel_number(
            phone_number_id=phone_number_id,
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

        return {
            "success": True,
            "message": "Phone number cancelled. It is now released and calls will not work.",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling phone number: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel phone number",
        )
