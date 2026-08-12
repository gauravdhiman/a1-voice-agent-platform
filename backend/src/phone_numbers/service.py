"""
Phone number management service.

This module provides the business logic for managing phone numbers,
including purchasing, assigning, and canceling phone numbers.
"""

import calendar
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from src.billing.models import (
    CreditConsumptionRequest,
    TransactionSource,
    TransactionType,
)
from src.billing.service import BillingService
from src.billing.system_pricing import (
    get_phone_number_pricing_event_name,
    get_system_pricing_definition,
)

from shared.config import supabase_config
from shared.organization.phone_number_models import (
    AvailablePhoneNumber,
    PhoneNumber,
    PhoneNumberAssignRequest,
    PhoneNumberBillingStatus,
    PhoneNumberCreate,
    PhoneNumberListResponse,
    PhoneNumberPurchaseRequest,
    PhoneNumberPurchaseResponse,
    PhoneNumberSearchRequest,
    PhoneNumberSearchResponse,
    PhoneNumberStatus,
    PhoneNumberType,
    PhoneNumberUpdate,
    PhoneNumberWithAgent,
)

from .twilio_service import twilio_service

logger = logging.getLogger(__name__)

PHONE_NUMBER_BILLING_GRACE_DAYS = 7


@dataclass
class PhoneNumberRentalRunResult:
    """Counters returned by one monthly phone-rental billing pass."""

    processed: int = 0
    charged: int = 0
    past_due: int = 0
    released: int = 0
    errors: int = 0


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
        self.twilio_service = twilio_service

    async def search_available(
        self, search_request: PhoneNumberSearchRequest
    ) -> tuple[PhoneNumberSearchResponse, Optional[str]]:
        """Search for available phone numbers from Twilio.

        Args:
            search_request: Search parameters

        Returns:
            Tuple of (search results, error message)
        """
        try:
            if not self.twilio_service.is_configured():
                return (
                    PhoneNumberSearchResponse(
                        items=[],
                        total_count=0,
                        page=search_request.page,
                        page_size=search_request.page_size,
                        total_pages=0,
                    ),
                    None,
                )

            twilio_type = search_request.phone_number_type.value

            results = self.twilio_service.search_available_numbers(
                country_code=search_request.country_code,
                number_type=twilio_type,
                area_code=search_request.area_code,
                contains=search_request.contains,
                limit=search_request.page_size,
            )

            available_numbers = []
            for num in results:
                cost = await self._get_credits_for_type(
                    search_request.phone_number_type
                )

                capabilities = {}
                if hasattr(num, "capabilities"):
                    capabilities = {
                        "voice": getattr(num.capabilities, "voice", False),
                        "sms": getattr(num.capabilities, "sms", False),
                        "mms": getattr(num.capabilities, "mms", False),
                    }

                area_code = None
                if hasattr(num, "area_code"):
                    area_code = num.area_code
                elif hasattr(num, "postal_code"):
                    area_code = num.postal_code

                locality = getattr(num, "locality", None)

                available_numbers.append(
                    AvailablePhoneNumber(
                        phone_number=num.phone_number,
                        phone_number_type=search_request.phone_number_type,
                        country_code=search_request.country_code,
                        area_code=area_code,
                        monthly_cost_credits=cost,
                        capabilities=capabilities,
                        locality=locality,
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
            logger.error(f"Error searching available numbers: {e}")
            return (
                PhoneNumberSearchResponse(
                    items=[],
                    total_count=0,
                    page=search_request.page,
                    page_size=search_request.page_size,
                    total_pages=0,
                ),
                f"Failed to search available numbers: {str(e)}",
            )

    async def purchase_number(
        self,
        organization_id: UUID,
        purchase_request: PhoneNumberPurchaseRequest,
    ) -> tuple[Optional[PhoneNumberPurchaseResponse], Optional[str]]:
        """Purchase a phone number using credits.

        Args:
            organization_id: Organization purchasing the number
            purchase_request: Purchase request details

        Returns:
            Tuple of (purchase result, error message)
        """
        try:
            if not self.twilio_service.is_configured():
                return None, "Phone number provider not configured"

            cost = await self._get_credits_for_type(purchase_request.phone_number_type)

            balance = await self.billing_service.get_credit_balance(organization_id)
            if balance.total_credits < cost:
                return (
                    None,
                    f"Insufficient credits. Need {cost} credits, have {balance.total_credits}",
                )

            purchased = self.twilio_service.purchase_phone_number(
                phone_number=purchase_request.phone_number
            )

            purchased_at = datetime.now(timezone.utc)
            next_billing_at = _add_month(purchased_at)

            record = PhoneNumberCreate(
                organization_id=organization_id,
                phone_number=purchase_request.phone_number,
                provider="twilio",
                provider_sid=purchased.sid,
                phone_number_type=purchase_request.phone_number_type,
                country_code=purchase_request.country_code,
                monthly_cost_credits=cost,
                status=PhoneNumberStatus.PURCHASED,
                billing_status=PhoneNumberBillingStatus.ACTIVE,
                next_billing_at=next_billing_at,
            )

            result = (
                self.supabase.table("phone_numbers")
                .insert(record.model_dump(mode="json"))
                .execute()
            )

            if not result.data:
                if purchased.sid and self.twilio_service.is_configured():
                    self.twilio_service.release_phone_number(purchased.sid)
                return None, "Failed to save phone number record"

            consumption = await self.billing_service.consume_credits(
                CreditConsumptionRequest(
                    organization_id=organization_id,
                    event_name=get_phone_number_pricing_event_name(
                        purchase_request.phone_number_type
                    ),
                    quantity=1,
                    metadata={
                        "phone_number": purchase_request.phone_number,
                        "provider_sid": purchased.sid,
                        "cost": cost,
                    },
                )
            )

            if not consumption.success:
                if purchased.sid and self.twilio_service.is_configured():
                    self.twilio_service.release_phone_number(purchased.sid)
                self.supabase.table("phone_numbers").update(
                    {
                        "status": PhoneNumberStatus.CANCELLED.value,
                        "cancelled_at": datetime.now(timezone.utc).isoformat(),
                    }
                ).eq("id", result.data[0]["id"]).execute()
                return None, "Insufficient credits to keep the phone number"

            phone_number = PhoneNumber(**result.data[0])

            return (
                PhoneNumberPurchaseResponse(
                    success=True,
                    phone_number=phone_number,
                    message=f"Successfully purchased {purchase_request.phone_number}",
                    credit_balance_after=consumption.balance_after,
                ),
                None,
            )

        except Exception as e:
            logger.error(f"Error purchasing phone number: {e}")
            return None, f"Failed to purchase phone number: {str(e)}"

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
                .select("*")
                .eq("organization_id", str(organization_id))
                .eq("status", PhoneNumberStatus.PURCHASED.value)
                .execute()
            )

            phone_numbers = [PhoneNumber(**item) for item in result.data]

            numbers_with_agent = []
            unused_count = 0

            for pn in phone_numbers:
                agent_name = None
                if pn.assigned_agent_id:
                    agent_result = (
                        self.supabase.table("voice_agents")
                        .select("name")
                        .eq("id", str(pn.assigned_agent_id))
                        .execute()
                    )
                    if agent_result.data:
                        agent_name = agent_result.data[0]["name"]
                else:
                    unused_count += 1

                numbers_with_agent.append(
                    PhoneNumberWithAgent(
                        **pn.model_dump(),
                        agent_name=agent_name,
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

    async def assign_to_agent(
        self,
        phone_number_id: UUID,
        assign_request: PhoneNumberAssignRequest,
    ) -> tuple[Optional[PhoneNumber], Optional[str]]:
        """Assign a phone number to an agent.

        Args:
            phone_number_id: Phone number to assign
            assign_request: Assignment details

        Returns:
            Tuple of (updated phone number, error message)
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

            phone_number = PhoneNumber(**result.data[0])

            if phone_number.status != PhoneNumberStatus.PURCHASED:
                return None, f"Cannot assign number with status {phone_number.status}"

            if phone_number.assigned_agent_id:
                return None, "Phone number is already assigned to an agent"

            agent_result = (
                self.supabase.table("voice_agents")
                .select("id")
                .eq("id", str(assign_request.agent_id))
                .execute()
            )

            if not agent_result.data:
                return None, "Agent not found"

            update_data = {
                "assigned_agent_id": str(assign_request.agent_id),
                "status": PhoneNumberStatus.ACTIVE.value,
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

    async def cancel_number(
        self,
        phone_number_id: UUID,
    ) -> tuple[bool, Optional[str]]:
        """Cancel (release) a phone number.

        Args:
            phone_number_id: Phone number to cancel

        Returns:
            Tuple of (success, error message)
        """
        try:
            result = (
                self.supabase.table("phone_numbers")
                .select("*")
                .eq("id", str(phone_number_id))
                .execute()
            )

            if not result.data:
                return False, "Phone number not found"

            phone_number = PhoneNumber(**result.data[0])

            if phone_number.status == PhoneNumberStatus.CANCELLED:
                return False, "Phone number is already cancelled"

            if phone_number.provider_sid and self.twilio_service.is_configured():
                self.twilio_service.release_phone_number(phone_number.provider_sid)

            update_data = {
                "status": PhoneNumberStatus.CANCELLED.value,
                "cancelled_at": datetime.now(timezone.utc).isoformat(),
                "assigned_agent_id": None,
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

    async def _get_credits_for_type(self, phone_type: PhoneNumberType) -> int:
        """Get the current system credit cost for a phone number type.

        Args:
            phone_type: Type of phone number

        Returns:
            Monthly cost in credits
        """
        event_name = get_phone_number_pricing_event_name(phone_type)
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

    async def process_due_rentals(
        self, now: Optional[datetime] = None
    ) -> PhoneNumberRentalRunResult:
        """Charge active phone rentals and release numbers after grace expiry.

        Existing numbers retain their Twilio ownership while a failed monthly
        debit is within the seven-day grace period. A successful retry restores
        the active billing state; an expired grace period releases the provider
        number and marks the local row cancelled.
        """
        # TODO: [Billing] Add a Postgres-backed rental claim/lease before the
        # backend is deployed with multiple scheduler instances. The current
        # single-process scheduler is safe for the present deployment shape.
        now = now or datetime.now(timezone.utc)
        result = (
            self.supabase.table("phone_numbers")
            .select("*")
            .in_(
                "status",
                [PhoneNumberStatus.PURCHASED.value, PhoneNumberStatus.ACTIVE.value],
            )
            .execute()
        )
        summary = PhoneNumberRentalRunResult()

        for row in result.data or []:
            try:
                phone_number = PhoneNumber(**row)
                due_at = phone_number.next_billing_at or _add_month(
                    phone_number.purchased_at
                )
                if due_at > now:
                    continue

                grace_ends_at = phone_number.billing_grace_ends_at
                if (
                    phone_number.billing_status == PhoneNumberBillingStatus.PAST_DUE
                    and grace_ends_at
                    and grace_ends_at <= now
                ):
                    released, error = await self.cancel_number(phone_number.id)
                    if released:
                        summary.released += 1
                        summary.processed += 1
                    else:
                        summary.errors += 1
                        logger.error(
                            "Failed to release past-due phone number %s: %s",
                            phone_number.id,
                            error,
                        )
                    continue

                cost = await self._get_credits_for_type(phone_number.phone_number_type)
                event_name = get_phone_number_pricing_event_name(
                    phone_number.phone_number_type
                )
                consumption = await self.billing_service.consume_credits(
                    CreditConsumptionRequest(
                        organization_id=phone_number.organization_id,
                        event_name=event_name,
                        quantity=1,
                        metadata={
                            "phone_number_id": str(phone_number.id),
                            "billing_period": due_at.isoformat(),
                            "cost": cost,
                        },
                    )
                )
                if consumption.success:
                    self.supabase.table("phone_numbers").update(
                        {
                            "monthly_cost_credits": cost,
                            "billing_status": PhoneNumberBillingStatus.ACTIVE.value,
                            "next_billing_at": _add_month(due_at).isoformat(),
                            "billing_grace_ends_at": None,
                            "updated_at": now.isoformat(),
                        }
                    ).eq("id", str(phone_number.id)).execute()
                    summary.charged += 1
                    summary.processed += 1
                else:
                    grace_end = grace_ends_at or (
                        now + timedelta(days=PHONE_NUMBER_BILLING_GRACE_DAYS)
                    )
                    self.supabase.table("phone_numbers").update(
                        {
                            "billing_status": PhoneNumberBillingStatus.PAST_DUE.value,
                            "billing_grace_ends_at": grace_end.isoformat(),
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
