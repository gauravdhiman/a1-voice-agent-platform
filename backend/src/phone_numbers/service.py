"""
Phone number management service.

This module provides the business logic for managing phone numbers,
including purchasing, assigning, and canceling phone numbers.
"""

import asyncio
import calendar
import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import HTTPException
from src.billing.entitlement_models import EntitlementDenied
from src.billing.entitlement_service import EntitlementService
from src.billing.models import CreditConsumptionRequest
from src.billing.service import BillingService
from src.billing.system_pricing import (
    get_phone_number_pricing_event_name,
    get_system_pricing_definition,
)

from shared.common.security import decrypt_data, encrypt_data
from shared.config import supabase_config
from shared.config.settings import settings
from shared.organization.phone_number_models import (
    AvailablePhoneNumber,
    PhoneNumber,
    PhoneNumberAssignRequest,
    PhoneNumberBillingMode,
    PhoneNumberBillingStatus,
    PhoneNumberConfigurationStatus,
    PhoneNumberCreate,
    PhoneNumberImportRequest,
    PhoneNumberImportResponse,
    PhoneNumberListResponse,
    PhoneNumberManagementMode,
    PhoneNumberProvisioningSource,
    PhoneNumberPurchaseRequest,
    PhoneNumberPurchaseResponse,
    PhoneNumberSearchRequest,
    PhoneNumberSearchResponse,
    PhoneNumberStatus,
    PhoneNumberType,
    PhoneNumberWebhookDetailsResponse,
    PhoneNumberWithAgent,
)

from .maintenance_guard import phone_mutation_guard
from .platform_settings_service import platform_phone_number_settings_service
from .twilio_service import twilio_service
from .utils import (
    build_phone_number_webhook_urls,
    hash_connection_token,
    normalize_phone_number,
    normalize_search_contains,
)

logger = logging.getLogger(__name__)

PHONE_NUMBER_SEARCH_UNAVAILABLE = (
    "Phone number search is temporarily unavailable. Please try again later."
)
PHONE_NUMBER_PURCHASE_UNAVAILABLE = (
    "Phone number purchase could not be confirmed. Check your phone numbers and "
    "credit balance before retrying."
)

PHONE_NUMBER_BILLING_GRACE_DAYS = 7

ACTIVE_PHONE_NUMBER_STATUSES = (
    PhoneNumberStatus.PURCHASED.value,
    PhoneNumberStatus.ACTIVE.value,
    PhoneNumberStatus.VERIFICATION_REQUIRED.value,
    PhoneNumberStatus.RELEASE_PENDING.value,
)

PHONE_NUMBER_LIST_COLUMNS = (
    "id, organization_id, phone_number, provider, provider_sid, phone_number_type, "
    "country_code, area_code, monthly_cost_credits, is_included_in_plan, status, assigned_agent_id, "
    "is_incoming_enabled, is_outgoing_enabled, billing_status, next_billing_at, "
    "billing_grace_ends_at, provisioning_source, management_mode, "
    "configuration_status, billing_mode, configuration_error, last_verified_at, "
    "purchased_at, cancelled_at, created_at, updated_at"
)


@dataclass
class PhoneNumberRentalRunResult:
    """Counters returned by one monthly phone-rental billing pass."""

    processed: int = 0
    charged: int = 0
    past_due: int = 0
    released: int = 0
    errors: int = 0
    deferred: int = 0


class PhoneNumberService:
    """Service for managing phone numbers.

    Handles phone number search, purchase, assignment to agents,
    and cancellation with proper credit management.

    Attributes:
        supabase: Supabase client for database operations
        billing_service: Service for credit operations
    """

    def __init__(self) -> None:
        """Initialize phone number service."""
        self.supabase = supabase_config.client
        self.billing_service = BillingService()
        self.entitlement_service = EntitlementService()
        self.twilio_service = twilio_service

    async def search_available(
        self,
        search_request: PhoneNumberSearchRequest,
        organization_id: Optional[UUID] = None,
    ) -> tuple[PhoneNumberSearchResponse, Optional[str]]:
        """Search for available phone numbers from Twilio.

        Args:
            search_request: Search parameters

        Returns:
            Tuple of (search results, error message)
        """
        try:
            if search_request.country_code.strip().upper() != "US":
                return (
                    PhoneNumberSearchResponse(
                        items=[],
                        total_count=0,
                        page=search_request.page,
                        page_size=search_request.page_size,
                        total_pages=0,
                    ),
                    "Only US platform-provided phone numbers are available in v1.",
                )
            if search_request.phone_number_type == PhoneNumberType.MOBILE:
                return (
                    PhoneNumberSearchResponse(
                        items=[],
                        total_count=0,
                        page=search_request.page,
                        page_size=search_request.page_size,
                        total_pages=0,
                    ),
                    "Mobile phone numbers are not available for new platform purchases in v1.",
                )

            if not self.twilio_service.is_configured():
                return (
                    PhoneNumberSearchResponse(
                        items=[],
                        total_count=0,
                        page=search_request.page,
                        page_size=search_request.page_size,
                        total_pages=0,
                    ),
                    PHONE_NUMBER_SEARCH_UNAVAILABLE,
                )

            twilio_type = search_request.phone_number_type.value

            results = self.twilio_service.search_available_numbers(
                country_code=search_request.country_code.upper(),
                number_type=twilio_type,
                area_code=search_request.area_code,
                contains=normalize_search_contains(
                    search_request.contains,
                    search_request.search_mode,
                    search_request.country_code,
                ),
                limit=search_request.page_size,
            )

            qualifies_for_included_local = (
                await self._qualifies_for_included_us_local_number(
                    organization_id,
                    search_request.phone_number_type,
                    search_request.country_code,
                )
                if organization_id
                else False
            )
            cost = (
                0
                if qualifies_for_included_local
                else await self._get_credits_for_type(
                    search_request.phone_number_type, search_request.country_code
                )
            )

            available_numbers = []
            for num in results:
                capabilities = {}
                if hasattr(num, "capabilities"):
                    capabilities = {
                        "voice": getattr(num.capabilities, "voice", False),
                        "sms": getattr(num.capabilities, "sms", False),
                        "mms": getattr(num.capabilities, "mms", False),
                    }

                area_code = getattr(num, "area_code", None)
                postal_code = getattr(num, "postal_code", None)

                locality = getattr(num, "locality", None)

                available_numbers.append(
                    AvailablePhoneNumber(
                        phone_number=num.phone_number,
                        phone_number_type=search_request.phone_number_type,
                        country_code=search_request.country_code.upper(),
                        area_code=area_code,
                        monthly_cost_credits=cost,
                        is_included_in_plan=qualifies_for_included_local,
                        capabilities=capabilities,
                        locality=locality,
                        postal_code=postal_code,
                    )
                )

            return (
                PhoneNumberSearchResponse(
                    items=available_numbers,
                    total_count=len(available_numbers),
                    page=search_request.page,
                    page_size=search_request.page_size,
                    total_pages=1,
                ),
                None,
            )

        except Exception as e:
            # Provider exceptions can contain account identifiers and raw
            # upstream response bodies. Keep those out of both logs and the
            # customer-facing error contract.
            logger.error(
                "Phone number availability lookup failed (error_type=%s)",
                type(e).__name__,
            )
            return (
                PhoneNumberSearchResponse(
                    items=[],
                    total_count=0,
                    page=search_request.page,
                    page_size=search_request.page_size,
                    total_pages=0,
                ),
                PHONE_NUMBER_SEARCH_UNAVAILABLE,
            )

    async def purchase_number(
        self,
        organization_id: UUID,
        purchase_request: PhoneNumberPurchaseRequest,
        idempotency_key: Optional[str] = None,
    ) -> tuple[Optional[PhoneNumberPurchaseResponse], Optional[str]]:
        """Purchase a phone number using credits.

        Args:
            organization_id: Organization purchasing the number
            purchase_request: Purchase request details

        Returns:
            Tuple of (purchase result, error message)
        """
        normalized_number = normalize_phone_number(
            purchase_request.phone_number, purchase_request.country_code
        )
        caller_idempotency_key = idempotency_key
        request_idempotency_key = caller_idempotency_key
        credit_idempotency_key: Optional[str] = None
        attempt_id: Optional[str] = None
        charged = False
        charged_cost = 0
        provider_sid: Optional[str] = None
        is_included = False
        balance_after = 0

        try:
            # Always route purchases through the atomic phone-credit debit
            # path, even for callers that do not provide an HTTP retry key.
            # The generated key identifies this provisioning attempt; callers
            # that need retry-safe replay should still send Idempotency-Key.
            request_idempotency_key = request_idempotency_key or (
                f"phone-number:{organization_id}:{secrets.token_urlsafe(24)}"
            )

            if caller_idempotency_key:
                existing_result = (
                    self.supabase.table("phone_numbers")
                    .select("*")
                    .eq("organization_id", str(organization_id))
                    .eq("provisioning_idempotency_key", request_idempotency_key)
                    .limit(1)
                    .execute()
                )
                if existing_result.data:
                    existing = PhoneNumber(**existing_result.data[0])
                    if (
                        existing.phone_number != normalized_number
                        or existing.phone_number_type
                        != purchase_request.phone_number_type
                    ):
                        return (
                            None,
                            "This idempotency key was already used for another number",
                        )
                    if existing.status == PhoneNumberStatus.PROVISIONING:
                        return (
                            None,
                            "This phone number purchase is already provisioning",
                        )
                    if existing.status == PhoneNumberStatus.RELEASE_PENDING:
                        return (
                            None,
                            "This phone number purchase is awaiting provider release",
                        )
                    if existing.status in {
                        PhoneNumberStatus.PURCHASED,
                        PhoneNumberStatus.ACTIVE,
                    }:
                        try:
                            balance = await self.billing_service.get_credit_balance(
                                organization_id
                            )
                            balance_after = int(balance.total_credits)
                        except Exception:
                            balance_after = 0
                        return (
                            PhoneNumberPurchaseResponse(
                                success=True,
                                phone_number=existing,
                                message="Phone number purchase already completed",
                                credit_balance_after=balance_after,
                            ),
                            None,
                        )
                    if existing.status in {
                        PhoneNumberStatus.CANCELLED,
                        PhoneNumberStatus.DISCONNECTED,
                    }:
                        return (
                            None,
                            "This purchase attempt has ended. Start a new purchase with a fresh idempotency key.",
                        )

            if purchase_request.country_code.strip().upper() != "US":
                return (
                    None,
                    "Only US platform-provided phone numbers are available in v1.",
                )
            if purchase_request.phone_number_type == PhoneNumberType.MOBILE:
                return (
                    None,
                    "Mobile phone numbers are not available for new platform purchases in v1.",
                )

            if not self.twilio_service.is_configured():
                return None, PHONE_NUMBER_PURCHASE_UNAVAILABLE

            # Keep the public retry key on the provisioning row, but use a
            # unique key for this ledger attempt. Reusing a refunded ledger key
            # would otherwise look like a successful debit without charging.
            credit_idempotency_key = (
                f"phone-number-debit:{organization_id}:{secrets.token_urlsafe(24)}"
            )

            limit_error = await self._phone_number_limit_error(organization_id)
            if limit_error:
                return None, limit_error

            is_included = await self._qualifies_for_included_us_local_number(
                organization_id,
                purchase_request.phone_number_type,
                purchase_request.country_code,
            )
            if purchase_request.expected_included_in_plan and not is_included:
                return (
                    None,
                    "The included US local number was just claimed. Search again to review current pricing.",
                )
            cost = (
                0
                if is_included
                else await self._get_credits_for_type(
                    purchase_request.phone_number_type, purchase_request.country_code
                )
            )
            if cost:
                event_name = get_phone_number_pricing_event_name(
                    purchase_request.phone_number_type, purchase_request.country_code
                )
                consumption = await self.billing_service.consume_credits(
                    CreditConsumptionRequest(
                        organization_id=organization_id,
                        event_name=event_name,
                        quantity=1,
                        metadata={
                            "phone_number": normalized_number,
                            "purpose": "phone_number_purchase",
                            "cost": cost,
                        },
                        idempotency_key=credit_idempotency_key,
                    )
                )
                if not consumption.success:
                    return None, "Insufficient credits to purchase the phone number"
                charged = True
                charged_cost = cost
                balance_after = int(consumption.balance_after)
            else:
                balance = await self.billing_service.get_credit_balance(organization_id)
                balance_after = int(balance.total_credits)

            purchased_at = datetime.now(timezone.utc)
            next_billing_at = _add_month(purchased_at)
            pending = PhoneNumberCreate(
                organization_id=organization_id,
                phone_number=normalized_number,
                provider="twilio",
                provider_sid=None,
                phone_number_type=purchase_request.phone_number_type,
                country_code=purchase_request.country_code.upper(),
                monthly_cost_credits=cost,
                is_included_in_plan=is_included,
                status=PhoneNumberStatus.PROVISIONING,
                billing_status=PhoneNumberBillingStatus.ACTIVE,
                billing_mode=PhoneNumberBillingMode.PLATFORM_RENTAL,
                provisioning_source=PhoneNumberProvisioningSource.PLATFORM,
                management_mode=PhoneNumberManagementMode.PLATFORM,
                configuration_status=PhoneNumberConfigurationStatus.PENDING,
                next_billing_at=next_billing_at,
                provisioning_idempotency_key=request_idempotency_key,
            )
            pending_result = (
                self.supabase.table("phone_numbers")
                .insert(pending.model_dump(mode="json", exclude_none=True))
                .execute()
            )
            if not pending_result.data:
                await self._refund_failed_purchase(
                    organization_id,
                    cost,
                    normalized_number,
                    credit_idempotency_key,
                )
                return None, "Failed to save phone number provisioning record"
            attempt_id = pending_result.data[0]["id"]

            urls = build_phone_number_webhook_urls(settings.api_base_url)
            purchased = self.twilio_service.purchase_phone_number(
                phone_number=normalized_number,
                voice_url=urls.voice_url,
                status_callback=urls.status_callback,
            )
            provider_sid = purchased.sid

            update_result = (
                self.supabase.table("phone_numbers")
                .update(
                    {
                        "provider_sid": provider_sid,
                        "status": PhoneNumberStatus.PURCHASED.value,
                        "configuration_status": PhoneNumberConfigurationStatus.CONFIGURED.value,
                        "last_verified_at": datetime.now(timezone.utc).isoformat(),
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
                .eq("id", attempt_id)
                .execute()
            )
            if not update_result.data:
                raise RuntimeError("Failed to finalize phone number record")

            phone_number = PhoneNumber(**update_result.data[0])
            return (
                PhoneNumberPurchaseResponse(
                    success=True,
                    phone_number=phone_number,
                    message=f"Successfully purchased {normalized_number}",
                    credit_balance_after=balance_after,
                ),
                None,
            )

        except Exception as e:
            # Provider and persistence errors can contain phone numbers,
            # account identifiers, or upstream response bodies. Keep them out
            # of logs and the customer-facing error contract.
            logger.error(
                "Phone number purchase failed (error_type=%s)", type(e).__name__
            )
            if provider_sid:
                try:
                    if self.twilio_service.is_configured():
                        self.twilio_service.release_phone_number(provider_sid)
                        if attempt_id:
                            self._mark_cancelled(attempt_id)
                    elif attempt_id:
                        self._set_release_pending(attempt_id, provider_sid)
                except Exception as compensation_error:
                    logger.error(
                        "Provider compensation failed for phone-number purchase "
                        "(error_type=%s)",
                        type(compensation_error).__name__,
                    )
                    if attempt_id:
                        try:
                            self._set_release_pending(attempt_id, provider_sid)
                        except Exception as state_error:
                            logger.error(
                                "Could not persist phone-number release retry "
                                "(error_type=%s)",
                                type(state_error).__name__,
                            )
            elif attempt_id:
                try:
                    self._mark_cancelled(attempt_id)
                except Exception as state_error:
                    logger.error(
                        "Could not persist cancelled phone-number purchase "
                        "(error_type=%s)",
                        type(state_error).__name__,
                    )
            if charged:
                await self._refund_failed_purchase(
                    organization_id,
                    charged_cost,
                    normalized_number,
                    credit_idempotency_key,
                )
            return None, PHONE_NUMBER_PURCHASE_UNAVAILABLE

    async def import_number(
        self,
        organization_id: UUID,
        import_request: PhoneNumberImportRequest,
    ) -> tuple[Optional[PhoneNumberImportResponse], Optional[str]]:
        """Connect a customer-owned Twilio number without provider billing.

        The method creates a verification-required row and returns tokenized
        webhook URLs once. The raw token is not recoverable and the method
        never calls Twilio's purchase or delete API. Customer-managed numbers
        are not subject to the organization's platform-purchased number limit.
        """
        try:
            normalized_number = normalize_phone_number(
                import_request.phone_number, import_request.country_code
            )
            assigned_agent_id = None
            if import_request.agent_id:
                agent_result = (
                    self.supabase.table("voice_agents")
                    .select("id")
                    .eq("id", str(import_request.agent_id))
                    .eq("organization_id", str(organization_id))
                    .eq("is_active", True)
                    .execute()
                )
                if not agent_result.data:
                    return None, "Agent not found in this organization"
                assigned_agent_id = import_request.agent_id

            token = secrets.token_urlsafe(32)
            urls = build_phone_number_webhook_urls(settings.api_base_url, token)
            now = datetime.now(timezone.utc)
            record = PhoneNumberCreate(
                organization_id=organization_id,
                phone_number=normalized_number,
                provider="twilio",
                provider_sid=None,
                phone_number_type=import_request.phone_number_type,
                country_code=import_request.country_code.upper(),
                monthly_cost_credits=0,
                status=PhoneNumberStatus.VERIFICATION_REQUIRED,
                assigned_agent_id=assigned_agent_id,
                is_incoming_enabled=False,
                billing_status=PhoneNumberBillingStatus.ACTIVE,
                billing_mode=PhoneNumberBillingMode.NONE,
                provisioning_source=PhoneNumberProvisioningSource.CUSTOMER,
                management_mode=PhoneNumberManagementMode.CUSTOMER,
                configuration_status=PhoneNumberConfigurationStatus.VERIFICATION_REQUIRED,
                connection_token_hash=hash_connection_token(token),
                connection_token_encrypted=encrypt_data({"token": token}),
                purchased_at=now,
            )
            result = (
                self.supabase.table("phone_numbers")
                .insert(record.model_dump(mode="json", exclude_none=True))
                .execute()
            )
            if not result.data:
                return None, "Failed to save customer phone number"

            phone_number = PhoneNumber(**result.data[0])
            return (
                PhoneNumberImportResponse(
                    success=True,
                    phone_number=phone_number,
                    voice_url=urls.voice_url,
                    status_callback=urls.status_callback,
                    message=(
                        "Configure both URLs in Twilio, then place a test call "
                        "to verify this number."
                    ),
                ),
                None,
            )
        except HTTPException as exc:
            return None, str(exc.detail)
        except Exception as e:
            if "uq_phone_numbers_active_number" in str(e):
                return (
                    None,
                    "This phone number is already connected. "
                    "Select it from the phone-number list instead.",
                )
            logger.error("Error importing customer phone number: %s", e)
            return None, f"Failed to import phone number: {str(e)}"

    async def get_verification_details(
        self, organization_id: UUID, phone_number_id: UUID
    ) -> tuple[Optional[PhoneNumberWebhookDetailsResponse], Optional[str]]:
        """Return pending customer webhook URLs for an organization-owned number.

        Args:
            organization_id: Organization requesting the setup details.
            phone_number_id: Phone-number record whose setup URLs are needed.

        Returns:
            A tuple containing the tokenized webhook details, or an error when
            the number is not pending customer verification or its encrypted
            setup token is unavailable.

        Notes:
            The raw token is encrypted at rest and is removed when the first
            valid customer webhook verifies the number. Platform-managed and
            already-verified numbers never expose setup details.
        """
        try:
            result = (
                self.supabase.table("phone_numbers")
                .select(
                    "id, phone_number, status, provisioning_source, "
                    "management_mode, connection_token_encrypted"
                )
                .eq("id", str(phone_number_id))
                .eq("organization_id", str(organization_id))
                .execute()
            )
            if not result.data:
                return None, "Phone number not found"

            row = result.data[0]
            if (
                row.get("status") != PhoneNumberStatus.VERIFICATION_REQUIRED.value
                or row.get("provisioning_source")
                != PhoneNumberProvisioningSource.CUSTOMER.value
                or row.get("management_mode")
                != PhoneNumberManagementMode.CUSTOMER.value
            ):
                return (
                    None,
                    "Verification details are only available while setup is pending",
                )

            encrypted_token = row.get("connection_token_encrypted")
            token = decrypt_data(encrypted_token or "").get("token")
            if not token:
                token = secrets.token_urlsafe(32)
                update_result = (
                    self.supabase.table("phone_numbers")
                    .update(
                        {
                            "connection_token_hash": hash_connection_token(token),
                            "connection_token_encrypted": encrypt_data(
                                {"token": token}
                            ),
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                        }
                    )
                    .eq("id", str(phone_number_id))
                    .eq("organization_id", str(organization_id))
                    .execute()
                )
                if not update_result.data:
                    return None, "Verification details are no longer available"

            urls = build_phone_number_webhook_urls(settings.api_base_url, token)
            return (
                PhoneNumberWebhookDetailsResponse(
                    phone_number_id=UUID(str(row["id"])),
                    phone_number=row["phone_number"],
                    voice_url=urls.voice_url,
                    status_callback=urls.status_callback,
                    message=(
                        "Set both URLs in Twilio, then place a test call to "
                        "complete verification."
                    ),
                ),
                None,
            )
        except Exception as e:
            logger.error(
                "Error loading verification details for phone number %s: %s",
                phone_number_id,
                e,
            )
            return None, "Failed to load phone-number verification details"

    async def verify_customer_number(
        self, phone_number: str, connection_token: str
    ) -> bool:
        """Verify a customer-owned number using its connection token."""
        normalized = normalize_phone_number(phone_number)
        result = (
            self.supabase.table("phone_numbers")
            .select("id")
            .eq("phone_number", normalized)
            .eq("connection_token_hash", hash_connection_token(connection_token))
            .eq("management_mode", PhoneNumberManagementMode.CUSTOMER.value)
            .in_(
                "status",
                [
                    PhoneNumberStatus.VERIFICATION_REQUIRED.value,
                    PhoneNumberStatus.ACTIVE.value,
                ],
            )
            .eq("billing_status", PhoneNumberBillingStatus.ACTIVE.value)
            .execute()
        )
        if not result.data:
            return False
        self.supabase.table("phone_numbers").update(
            {
                "status": PhoneNumberStatus.ACTIVE.value,
                "is_incoming_enabled": True,
                "configuration_status": PhoneNumberConfigurationStatus.CONFIGURED.value,
                "last_verified_at": datetime.now(timezone.utc).isoformat(),
                "configuration_error": None,
                "connection_token_encrypted": None,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", result.data[0]["id"]).execute()
        return True

    async def get_routable_agent_id(
        self, phone_number: str
    ) -> tuple[Optional[UUID], Optional[str]]:
        """Resolve an enabled, assigned phone number to its active agent."""
        normalized = normalize_phone_number(phone_number)
        result = (
            self.supabase.table("phone_numbers")
            .select("assigned_agent_id, voice_agents!inner(id, is_active)")
            .eq("phone_number", normalized)
            .in_(
                "status",
                [PhoneNumberStatus.PURCHASED.value, PhoneNumberStatus.ACTIVE.value],
            )
            .eq("is_incoming_enabled", True)
            .eq("billing_status", PhoneNumberBillingStatus.ACTIVE.value)
            .eq("configuration_status", PhoneNumberConfigurationStatus.CONFIGURED.value)
            .eq("voice_agents.is_active", True)
            .limit(1)
            .execute()
        )
        if not result.data or not result.data[0].get("assigned_agent_id"):
            return None, "Phone number is not assigned or enabled"
        return UUID(str(result.data[0]["assigned_agent_id"])), None

    async def _phone_number_limit_error(self, organization_id: UUID) -> Optional[str]:
        """Return a plan-limit error before any paid provider operation."""
        try:
            await self.entitlement_service.assert_limit(
                organization_id, "max_phone_numbers", increment=1
            )
        except EntitlementDenied as exc:
            return str(exc)
        return None

    async def _has_active_included_us_local_number(self, organization_id: UUID) -> bool:
        """Check whether the organization already holds its included US line."""
        result = (
            self.supabase.table("phone_numbers")
            .select("id")
            .eq("organization_id", str(organization_id))
            .eq("is_included_in_plan", True)
            .eq("management_mode", PhoneNumberManagementMode.PLATFORM.value)
            .eq("billing_mode", PhoneNumberBillingMode.PLATFORM_RENTAL.value)
            .eq("phone_number_type", PhoneNumberType.LOCAL.value)
            .eq("country_code", "US")
            # Count an included line while provider provisioning is pending so
            # a stale search is rejected before another provider purchase.
            .in_(
                "status",
                [
                    PhoneNumberStatus.PROVISIONING.value,
                    *ACTIVE_PHONE_NUMBER_STATUSES,
                ],
            )
            .limit(1)
            .execute()
        )
        return bool(result.data)

    async def _qualifies_for_included_us_local_number(
        self,
        organization_id: UUID,
        phone_number_type: PhoneNumberType,
        country_code: str,
    ) -> bool:
        """Check the active paid-plan benefit and whether its US line is unused."""
        if phone_number_type != PhoneNumberType.LOCAL or country_code.upper() != "US":
            return False
        if await self._has_active_included_us_local_number(organization_id):
            return False
        return await self._has_active_paid_plan_allowance(
            organization_id, datetime.now(timezone.utc)
        )

    async def _promote_included_us_local_number(
        self,
        organization_id: UUID,
        *,
        paid_plan_active: Optional[bool] = None,
    ) -> Optional[UUID]:
        """Apply the included allowance to the oldest remaining platform line."""
        try:
            if paid_plan_active is None:
                paid_plan_active = await self._has_active_paid_plan_allowance(
                    organization_id, datetime.now(timezone.utc)
                )
            if not paid_plan_active:
                return None

            existing = (
                self.supabase.table("phone_numbers")
                .select("id")
                .eq("organization_id", str(organization_id))
                .eq("is_included_in_plan", True)
                .eq("management_mode", PhoneNumberManagementMode.PLATFORM.value)
                .eq("billing_mode", PhoneNumberBillingMode.PLATFORM_RENTAL.value)
                .eq("phone_number_type", PhoneNumberType.LOCAL.value)
                .eq("country_code", "US")
                .in_("status", list(ACTIVE_PHONE_NUMBER_STATUSES))
                .limit(1)
                .execute()
            )
            if existing.data:
                return None

            candidates = (
                self.supabase.table("phone_numbers")
                .select("id, assigned_agent_id, configuration_status")
                .eq("organization_id", str(organization_id))
                .eq("is_included_in_plan", False)
                .eq("management_mode", PhoneNumberManagementMode.PLATFORM.value)
                .eq("billing_mode", PhoneNumberBillingMode.PLATFORM_RENTAL.value)
                .eq("phone_number_type", PhoneNumberType.LOCAL.value)
                .eq("country_code", "US")
                .in_(
                    "status",
                    [
                        PhoneNumberStatus.PURCHASED.value,
                        PhoneNumberStatus.ACTIVE.value,
                    ],
                )
                .order("purchased_at")
                .limit(1)
                .execute()
            )
            if not candidates.data:
                return None

            candidate = candidates.data[0]
            can_route = bool(
                candidate.get("assigned_agent_id")
                and candidate.get("configuration_status")
                == PhoneNumberConfigurationStatus.CONFIGURED.value
            )
            promoted = (
                self.supabase.table("phone_numbers")
                .update(
                    {
                        "is_included_in_plan": True,
                        "monthly_cost_credits": 0,
                        "billing_status": PhoneNumberBillingStatus.ACTIVE.value,
                        "billing_grace_ends_at": None,
                        "is_incoming_enabled": can_route,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
                .eq("id", candidate["id"])
                .eq("organization_id", str(organization_id))
                .eq("is_included_in_plan", False)
                .eq("management_mode", PhoneNumberManagementMode.PLATFORM.value)
                .eq("billing_mode", PhoneNumberBillingMode.PLATFORM_RENTAL.value)
                .eq("phone_number_type", PhoneNumberType.LOCAL.value)
                .eq("country_code", "US")
                .in_(
                    "status",
                    [
                        PhoneNumberStatus.PURCHASED.value,
                        PhoneNumberStatus.ACTIVE.value,
                    ],
                )
                .select("id")
                .execute()
            )
            if promoted.data:
                return UUID(str(candidate["id"]))
            return None
        except Exception:
            # Cancellation and provider release must still complete if allowance
            # reassignment encounters a transient database or uniqueness race.
            logger.exception(
                "Failed to promote an included US local number for %s",
                organization_id,
            )
            return None

    async def _refund_failed_purchase(
        self,
        organization_id: UUID,
        credits: int,
        phone_number: str,
        idempotency_key: Optional[str] = None,
    ) -> None:
        """Refund a failed platform purchase without hiding refund failures."""
        try:
            await self.billing_service.refund_credits(
                organization_id=organization_id,
                credits=credits,
                reason="Phone-number purchase failed",
                metadata={"phone_number": phone_number},
                idempotency_key=(
                    f"phone-number-refund:{idempotency_key}"
                    if idempotency_key
                    else None
                ),
            )
        except Exception as e:
            logger.error(
                "Failed to refund phone-number purchase (error_type=%s)",
                type(e).__name__,
            )

    def _mark_cancelled(self, phone_number_id: str) -> None:
        """Mark a failed provisioning attempt as cancelled."""
        self.supabase.table("phone_numbers").update(
            {
                "status": PhoneNumberStatus.CANCELLED.value,
                "cancelled_at": datetime.now(timezone.utc).isoformat(),
                "is_incoming_enabled": False,
            }
        ).eq("id", phone_number_id).execute()

    def _set_release_pending(self, phone_number_id: str, provider_sid: str) -> None:
        """Persist an orphaned provider number for the daily release retry."""
        self.supabase.table("phone_numbers").update(
            {
                "provider_sid": provider_sid,
                "status": PhoneNumberStatus.RELEASE_PENDING.value,
                "is_incoming_enabled": False,
                "configuration_error": "Provider release is pending retry",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", phone_number_id).execute()

    async def get_organization_numbers(
        self, organization_id: UUID
    ) -> tuple[PhoneNumberListResponse, Optional[str]]:
        """Get all phone numbers owned by an organization.

        Args:
            organization_id: Organization ID

        Returns:
            Tuple of (list of phone numbers, error message)
        """
        try:
            result = (
                self.supabase.table("phone_numbers")
                .select(PHONE_NUMBER_LIST_COLUMNS)
                .eq("organization_id", str(organization_id))
                .in_("status", list(ACTIVE_PHONE_NUMBER_STATUSES))
                .execute()
            )

            phone_numbers = [PhoneNumber(**item) for item in result.data]

            assigned_agent_ids = sorted(
                {
                    str(phone_number.assigned_agent_id)
                    for phone_number in phone_numbers
                    if phone_number.assigned_agent_id
                }
            )
            agent_names: dict[str, str] = {}
            if assigned_agent_ids:
                agent_result = (
                    self.supabase.table("voice_agents")
                    .select("id, name")
                    .in_("id", assigned_agent_ids)
                    .execute()
                )
                agent_names = {
                    str(item["id"]): item["name"]
                    for item in (agent_result.data or [])
                    if item.get("id") and item.get("name")
                }

            numbers_with_agent = []
            unused_count = 0

            for pn in phone_numbers:
                if not pn.assigned_agent_id:
                    unused_count += 1

                numbers_with_agent.append(
                    PhoneNumberWithAgent(
                        **pn.model_dump(),
                        agent_name=(
                            agent_names.get(str(pn.assigned_agent_id))
                            if pn.assigned_agent_id
                            else None
                        ),
                    )
                )

            return (
                PhoneNumberListResponse(
                    items=numbers_with_agent,
                    total_count=len(phone_numbers),
                    unused_count=unused_count,
                ),
                None,
            )

        except Exception as e:
            logger.error(f"Error fetching organization phone numbers: {e}")
            return (
                PhoneNumberListResponse(items=[], total_count=0, unused_count=0),
                f"Failed to fetch phone numbers: {str(e)}",
            )

    async def get_agent_number(
        self, organization_id: UUID, agent_id: UUID
    ) -> tuple[Optional[PhoneNumberWithAgent], Optional[str]]:
        """Load the current number assigned to one agent.

        This endpoint is intentionally narrower than the organization list used
        by the assignment dropdown. The agent detail page can render its
        current value with one indexed lookup and defer loading every available
        organization number until the user opens the dropdown.

        Args:
            organization_id: Organization that owns the agent and number.
            agent_id: Agent whose active assignment should be returned.

        Returns:
            The assigned phone number, or ``None`` when the agent has no active
            assignment, together with an optional error message.
        """
        try:
            result = (
                self.supabase.table("phone_numbers")
                .select(PHONE_NUMBER_LIST_COLUMNS)
                .eq("organization_id", str(organization_id))
                .eq("assigned_agent_id", str(agent_id))
                .in_("status", list(ACTIVE_PHONE_NUMBER_STATUSES))
                .limit(1)
                .execute()
            )
            if not result.data:
                return None, None
            return PhoneNumberWithAgent(**result.data[0]), None
        except Exception as e:
            logger.error(
                "Error fetching phone number for agent %s in organization %s: %s",
                agent_id,
                organization_id,
                e,
            )
            return None, f"Failed to fetch phone number for agent: {str(e)}"

    async def assign_to_agent(
        self,
        phone_number_id: UUID,
        assign_request: PhoneNumberAssignRequest,
        organization_id: Optional[UUID] = None,
    ) -> tuple[Optional[PhoneNumber], Optional[str]]:
        """Assign a phone number to an agent.

        Args:
            phone_number_id: Phone number to assign
            assign_request: Assignment details

        Returns:
            Tuple of (updated phone number, error message)
        """
        try:
            query = (
                self.supabase.table("phone_numbers")
                .select("*")
                .eq("id", str(phone_number_id))
            )
            if organization_id:
                query = query.eq("organization_id", str(organization_id))
            result = query.execute()

            if not result.data:
                return None, "Phone number not found"

            phone_number = PhoneNumber(**result.data[0])

            if phone_number.status not in {
                PhoneNumberStatus.PURCHASED,
                PhoneNumberStatus.ACTIVE,
            }:
                return None, f"Cannot assign number with status {phone_number.status}"

            if phone_number.assigned_agent_id == assign_request.agent_id:
                return phone_number, None

            if phone_number.assigned_agent_id:
                return None, "Phone number is already assigned to an agent"

            agent_query = (
                self.supabase.table("voice_agents")
                .select("id")
                .eq("id", str(assign_request.agent_id))
            )
            agent_query = agent_query.eq("is_active", True)
            if organization_id:
                agent_query = agent_query.eq("organization_id", str(organization_id))
            agent_result = agent_query.execute()

            if not agent_result.data:
                return None, "Agent not found"

            update_data = {
                "assigned_agent_id": str(assign_request.agent_id),
                "status": PhoneNumberStatus.ACTIVE.value,
                "is_incoming_enabled": True,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            update_result = (
                self.supabase.table("phone_numbers")
                .update(update_data)
                .eq("id", str(phone_number_id))
                .execute()
            )

            if not update_result.data:
                return None, "Failed to update phone number"

            return PhoneNumber(**update_result.data[0]), None

        except Exception as e:
            logger.error(f"Error assigning phone number to agent: {e}")
            return None, f"Failed to assign phone number: {str(e)}"

    async def unassign_from_agent(
        self,
        phone_number_id: UUID,
        organization_id: Optional[UUID] = None,
    ) -> tuple[Optional[PhoneNumber], Optional[str]]:
        """Remove an agent mapping without releasing the underlying number.

        Args:
            phone_number_id: Phone number mapping to clear.
            organization_id: Optional organization scope used by the API.

        Returns:
            Tuple of the updated phone number and an optional error message.

        Notes:
            Platform-managed numbers return to ``purchased`` while
            customer-managed numbers remain ``active`` but stop receiving
            calls until they are assigned again.
        """
        try:
            query = (
                self.supabase.table("phone_numbers")
                .select("*")
                .eq("id", str(phone_number_id))
            )
            if organization_id:
                query = query.eq("organization_id", str(organization_id))
            result = query.execute()
            if not result.data:
                return None, "Phone number not found"

            phone_number = PhoneNumber(**result.data[0])
            if phone_number.status in {
                PhoneNumberStatus.CANCELLED,
                PhoneNumberStatus.DISCONNECTED,
            }:
                return None, f"Cannot unassign number with status {phone_number.status}"

            next_status = (
                PhoneNumberStatus.PURCHASED.value
                if phone_number.management_mode == PhoneNumberManagementMode.PLATFORM
                else PhoneNumberStatus.ACTIVE.value
            )
            update_result = (
                self.supabase.table("phone_numbers")
                .update(
                    {
                        "assigned_agent_id": None,
                        "status": next_status,
                        "is_incoming_enabled": False,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
                .eq("id", str(phone_number_id))
                .execute()
            )
            if not update_result.data:
                return None, "Failed to update phone number"
            return PhoneNumber(**update_result.data[0]), None
        except Exception as e:
            logger.error(f"Error unassigning phone number from agent: {e}")
            return None, f"Failed to unassign phone number: {str(e)}"

    async def cancel_number(
        self,
        phone_number_id: UUID,
        organization_id: Optional[UUID] = None,
    ) -> tuple[bool, Optional[str]]:
        """Cancel (release) a phone number.

        Args:
            phone_number_id: Phone number to cancel

        Returns:
            Tuple of (success, error message)
        """
        try:
            query = (
                self.supabase.table("phone_numbers")
                .select("*")
                .eq("id", str(phone_number_id))
            )
            if organization_id:
                query = query.eq("organization_id", str(organization_id))
            result = query.execute()

            if not result.data:
                return False, "Phone number not found"

            phone_number = PhoneNumber(**result.data[0])

            if phone_number.status == PhoneNumberStatus.CANCELLED:
                return False, "Phone number is already cancelled"

            if phone_number.management_mode == PhoneNumberManagementMode.CUSTOMER:
                update_data = {
                    "status": PhoneNumberStatus.DISCONNECTED.value,
                    "is_incoming_enabled": False,
                    "assigned_agent_id": None,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            else:
                if phone_number.provider_sid and self.twilio_service.is_configured():
                    try:
                        await asyncio.to_thread(
                            self.twilio_service.release_phone_number,
                            phone_number.provider_sid,
                        )
                    except Exception as exc:
                        self._set_release_pending(
                            str(phone_number_id), phone_number.provider_sid
                        )
                        logger.warning(
                            "Phone number %s release queued after provider failure: %s",
                            phone_number_id,
                            exc,
                        )
                        return True, "release_pending"

                update_data = {
                    "status": PhoneNumberStatus.CANCELLED.value,
                    "cancelled_at": datetime.now(timezone.utc).isoformat(),
                    "assigned_agent_id": None,
                    "is_incoming_enabled": False,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }

            update_result = (
                self.supabase.table("phone_numbers")
                .update(update_data)
                .eq("id", str(phone_number_id))
                .execute()
            )

            if not update_result.data:
                return False, "Failed to update phone number status"

            if phone_number.is_included_in_plan:
                await self._promote_included_us_local_number(
                    phone_number.organization_id
                )

            return True, None

        except Exception as e:
            logger.error(f"Error cancelling phone number: {e}")
            return False, f"Failed to cancel phone number: {str(e)}"

    async def get_by_id(
        self, phone_number_id: UUID
    ) -> tuple[Optional[PhoneNumber], Optional[str]]:
        """Get a phone number by ID.

        Args:
            phone_number_id: Phone number ID

        Returns:
            Tuple of (phone number, error message)
        """
        try:
            result = (
                self.supabase.table("phone_numbers")
                .select("*")
                .eq("id", str(phone_number_id))
                .execute()
            )

            if not result.data:
                return None, "Phone number not found"

            return PhoneNumber(**result.data[0]), None

        except Exception as e:
            logger.error(f"Error fetching phone number: {e}")
            return None, f"Failed to fetch phone number: {str(e)}"

    async def _get_credits_for_type(
        self, phone_type: PhoneNumberType, country_code: str = "US"
    ) -> int:
        """Get the current system credit cost for a phone type and country.

        Args:
            phone_type: Type of phone number.
            country_code: ISO country code; local rates vary by country.

        Returns:
            Monthly cost in credits
        """
        event_name = get_phone_number_pricing_event_name(phone_type, country_code)
        result = (
            self.supabase.table("credit_events")
            .select("credit_cost")
            .eq("name", event_name)
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
        if result.data and isinstance(result.data, list):
            return max(0, int(result.data[0].get("credit_cost") or 0))
        return get_system_pricing_definition(event_name).default_credit_cost

    async def _has_active_paid_plan_allowance(
        self, organization_id: UUID, now: datetime
    ) -> bool:
        """Return whether the organization's included-number benefit is active."""
        entitlements = await self.entitlement_service.get_org_entitlements(
            organization_id
        )
        if (
            not entitlements.is_entitled
            or entitlements.plan_product_slug.lower() == "free"
        ):
            return False

        if entitlements.cancel_at_period_end:
            if not entitlements.access_until:
                logger.error(
                    "Scheduled-cancel subscription for organization %s is missing "
                    "access_until; included phone allowance is disabled until the "
                    "subscription end date is repaired",
                    organization_id,
                )
                return False

            access_until = datetime.fromisoformat(
                entitlements.access_until.replace("Z", "+00:00")
            )
            if access_until.tzinfo is None:
                access_until = access_until.replace(tzinfo=timezone.utc)
            return access_until > now

        return True

    async def process_due_rentals(
        self, now: Optional[datetime] = None, *, guarded: bool = False
    ) -> PhoneNumberRentalRunResult:
        """Charge active phone rentals and release numbers after grace expiry.

        Existing numbers retain their Twilio ownership while a failed monthly
        debit is within the seven-day grace period. A successful retry restores
        the active billing state; an expired grace period releases the provider
        number and marks the local row cancelled.
        """
        now = now or datetime.now(timezone.utc)
        if guarded:
            rental_rows = await self._load_guarded_rental_rows()
        else:
            result = await asyncio.to_thread(
                lambda: self.supabase.table("phone_numbers")
                .select("*")
                .in_("status", list(ACTIVE_PHONE_NUMBER_STATUSES))
                .execute()
            )
            rental_rows = result.data or []
        lifecycle_settings = await platform_phone_number_settings_service.get_settings()
        if not guarded:
            return await self._process_rental_rows(rental_rows, now, lifecycle_settings)

        # Re-read each organization after acquiring its claim: the initial scan
        # is only an inventory, not an authoritative mutation snapshot.
        summary = PhoneNumberRentalRunResult()
        organization_ids = sorted(
            {str(row.get("organization_id")) for row in rental_rows}
        )
        for organization_id in organization_ids:
            try:
                async with phone_mutation_guard(UUID(organization_id), force=True):
                    current = await self._load_guarded_rental_rows(organization_id)
                    result = await self._process_rental_rows(
                        current, now, lifecycle_settings
                    )
                    for field in (
                        "processed",
                        "charged",
                        "past_due",
                        "released",
                        "errors",
                    ):
                        setattr(
                            summary,
                            field,
                            getattr(summary, field) + getattr(result, field),
                        )
                    if result.errors:
                        # A provider mutation may have completed even when its
                        # outcome could not be recorded. Retain this org claim.
                        raise RuntimeError(
                            "Phone rental provider outcome requires review"
                        )
            except HTTPException as exc:
                if exc.status_code == 409:
                    summary.deferred += 1
                else:
                    summary.errors += 1
            except Exception:
                summary.errors += 1
                logger.exception("Phone rental organization pass failed")
        return summary

    async def _load_guarded_rental_rows(
        self, organization_id: Optional[str] = None
    ) -> list[dict]:
        """Read all active rental rows using stable keyset pagination."""
        rows = []
        last_id = None
        page_size = 200
        while True:

            def load_page():
                query = (
                    self.supabase.table("phone_numbers")
                    .select("*")
                    .in_("status", list(ACTIVE_PHONE_NUMBER_STATUSES))
                )
                if organization_id:
                    query = query.eq("organization_id", organization_id)
                if last_id:
                    query = query.gt("id", last_id)
                return query.order("id").limit(page_size).execute()

            response = await asyncio.to_thread(load_page)
            page = response.data
            if not isinstance(page, list):
                raise RuntimeError("Invalid phone rental page")
            rows.extend(page)
            if len(page) < page_size:
                return rows
            next_id = str(page[-1].get("id") or "")
            if not next_id or next_id == last_id:
                raise RuntimeError("Phone rental pagination did not advance")
            last_id = next_id

    async def _process_rental_rows(
        self, rental_rows: list[dict], now: datetime, lifecycle_settings
    ) -> PhoneNumberRentalRunResult:
        """Process a freshly read set of rental rows under the caller's guard."""
        summary = PhoneNumberRentalRunResult()
        included_organizations = {
            str(row.get("organization_id"))
            for row in rental_rows
            if row.get("is_included_in_plan")
            and row.get("management_mode") == PhoneNumberManagementMode.PLATFORM.value
            and row.get("billing_mode") == PhoneNumberBillingMode.PLATFORM_RENTAL.value
            and row.get("phone_number_type") == PhoneNumberType.LOCAL.value
            and str(row.get("country_code", "")).upper() == "US"
        }
        reconciled_organizations: set[str] = set()
        promoted_number_ids: set[UUID] = set()
        for row in rental_rows:
            organization_key = str(row.get("organization_id"))
            if (
                row.get("management_mode") != PhoneNumberManagementMode.PLATFORM.value
                or row.get("billing_mode")
                != PhoneNumberBillingMode.PLATFORM_RENTAL.value
                or row.get("phone_number_type") != PhoneNumberType.LOCAL.value
                or str(row.get("country_code", "")).upper() != "US"
                or organization_key in included_organizations
                or organization_key in reconciled_organizations
            ):
                continue

            reconciled_organizations.add(organization_key)
            try:
                organization_id = UUID(organization_key)
                if await self._has_active_paid_plan_allowance(organization_id, now):
                    promoted_id = await self._promote_included_us_local_number(
                        organization_id, paid_plan_active=True
                    )
                    if promoted_id:
                        promoted_number_ids.add(promoted_id)
                        included_organizations.add(organization_key)
            except Exception:
                summary.errors += 1
                logger.exception(
                    "Failed to reconcile included phone allowance for %s",
                    organization_key,
                )

        for row in rental_rows:
            try:
                phone_number = PhoneNumber(**row)
                if phone_number.billing_mode != PhoneNumberBillingMode.PLATFORM_RENTAL:
                    continue

                if phone_number.status == PhoneNumberStatus.RELEASE_PENDING:
                    released, error = await self._retry_release_pending(phone_number)
                    if released:
                        summary.released += 1
                        summary.processed += 1
                    else:
                        summary.errors += 1
                        logger.error(
                            "Pending phone release still failed for %s: %s",
                            phone_number.id,
                            error,
                        )
                    continue

                if phone_number.id in promoted_number_ids:
                    summary.processed += 1
                    continue

                due_at = phone_number.next_billing_at or _add_month(
                    phone_number.purchased_at
                )
                if due_at > now:
                    continue

                if (
                    phone_number.is_included_in_plan
                    and await self._has_active_paid_plan_allowance(
                        phone_number.organization_id, now
                    )
                ):
                    can_route = bool(
                        phone_number.assigned_agent_id
                        and phone_number.configuration_status
                        == PhoneNumberConfigurationStatus.CONFIGURED
                        and phone_number.status
                        in {
                            PhoneNumberStatus.PURCHASED,
                            PhoneNumberStatus.ACTIVE,
                        }
                    )
                    self.supabase.table("phone_numbers").update(
                        {
                            "monthly_cost_credits": 0,
                            "billing_status": PhoneNumberBillingStatus.ACTIVE.value,
                            "billing_grace_ends_at": None,
                            "is_incoming_enabled": can_route,
                            "next_billing_at": _add_month(due_at).isoformat(),
                            "updated_at": now.isoformat(),
                        }
                    ).eq("id", str(phone_number.id)).execute()
                    summary.processed += 1
                    continue

                grace_ends_at = phone_number.billing_grace_ends_at
                if (
                    phone_number.billing_status == PhoneNumberBillingStatus.PAST_DUE
                    and grace_ends_at
                    and grace_ends_at <= now
                ):
                    released, error = await self.cancel_number(phone_number.id)
                    if released and error != "release_pending":
                        summary.released += 1
                        summary.processed += 1
                    elif error == "release_pending":
                        summary.processed += 1
                        summary.errors += 1
                        logger.error(
                            "Past-due phone release is pending retry for %s",
                            phone_number.id,
                        )
                    else:
                        summary.errors += 1
                        logger.error(
                            "Failed to release past-due phone number %s: %s",
                            phone_number.id,
                            error,
                        )
                    continue

                cost = await self._get_credits_for_type(
                    phone_number.phone_number_type, phone_number.country_code
                )
                event_name = get_phone_number_pricing_event_name(
                    phone_number.phone_number_type, phone_number.country_code
                )
                consumption = await self.billing_service.consume_credits(
                    CreditConsumptionRequest(
                        organization_id=phone_number.organization_id,
                        event_name=event_name,
                        quantity=1,
                        metadata={
                            "phone_number_id": str(phone_number.id),
                            "phone_number": phone_number.phone_number,
                            "purpose": "phone_number_rental",
                            "billing_period": due_at.isoformat(),
                            "cost": cost,
                        },
                        idempotency_key=(
                            f"phone-rental:{phone_number.id}:{due_at.isoformat()}"
                        ),
                    )
                )
                if consumption.success:
                    self.supabase.table("phone_numbers").update(
                        {
                            "is_included_in_plan": False,
                            "monthly_cost_credits": cost,
                            "billing_status": PhoneNumberBillingStatus.ACTIVE.value,
                            "is_incoming_enabled": True,
                            "next_billing_at": _add_month(due_at).isoformat(),
                            "billing_grace_ends_at": None,
                            "updated_at": now.isoformat(),
                        }
                    ).eq("id", str(phone_number.id)).execute()
                    summary.charged += 1
                    summary.processed += 1
                else:
                    grace_end = grace_ends_at or (
                        now
                        + timedelta(days=lifecycle_settings.billing_grace_period_days)
                    )
                    self.supabase.table("phone_numbers").update(
                        {
                            "is_included_in_plan": False,
                            "monthly_cost_credits": cost,
                            "billing_status": PhoneNumberBillingStatus.PAST_DUE.value,
                            "billing_grace_ends_at": grace_end.isoformat(),
                            "is_incoming_enabled": False,
                            "updated_at": now.isoformat(),
                        }
                    ).eq("id", str(phone_number.id)).execute()
                    summary.past_due += 1
                    summary.processed += 1
            except Exception:
                summary.errors += 1
                logger.exception(
                    "Phone rental billing failed for row %s", row.get("id")
                )

        return summary

    async def _retry_release_pending(
        self, phone_number: PhoneNumber
    ) -> tuple[bool, Optional[str]]:
        """Retry releasing a provider-owned orphan left by a failed operation."""
        if not phone_number.provider_sid:
            self._mark_cancelled(str(phone_number.id))
            if phone_number.is_included_in_plan:
                await self._promote_included_us_local_number(
                    phone_number.organization_id
                )
            return True, None
        try:
            await asyncio.to_thread(
                self.twilio_service.release_phone_number, phone_number.provider_sid
            )
            self._mark_cancelled(str(phone_number.id))
            if phone_number.is_included_in_plan:
                await self._promote_included_us_local_number(
                    phone_number.organization_id
                )
            return True, None
        except Exception as exc:
            return False, str(exc)


def _add_month(value: datetime) -> datetime:
    """Advance a timestamp by one calendar month without overflowing dates."""
    next_month = value.month + 1
    next_year = value.year
    if next_month == 13:
        next_month = 1
        next_year += 1
    next_day = min(value.day, calendar.monthrange(next_year, next_month)[1])
    return value.replace(year=next_year, month=next_month, day=next_day)


phone_number_service = PhoneNumberService()
