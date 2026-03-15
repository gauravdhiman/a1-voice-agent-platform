"""
Phone number management service.

This module provides the business logic for managing phone numbers,
including purchasing, assigning, and canceling phone numbers.
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from shared.config import supabase_config
from shared.organization.phone_number_models import (
    AvailablePhoneNumber,
    PhoneNumber,
    PhoneNumberAssignRequest,
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
from src.billing.models import (
    CreditConsumptionRequest,
    TransactionSource,
    TransactionType,
)
from src.billing.service import BillingService

from .twilio_service import twilio_service

logger = logging.getLogger(__name__)

CREDITS_PER_LOCAL_NUMBER = 200
CREDITS_PER_TOLL_FREE_NUMBER = 500
CREDITS_PER_MOBILE_NUMBER = 200


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
                return PhoneNumberSearchResponse(
                    items=[],
                    total_count=0,
                    page=search_request.page,
                    page_size=search_request.page_size,
                    total_pages=0,
                ), None

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
                cost = self._get_credits_for_type(search_request.phone_number_type)

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
            return PhoneNumberSearchResponse(
                items=[],
                total_count=0,
                page=search_request.page,
                page_size=search_request.page_size,
                total_pages=0,
            ), f"Failed to search available numbers: {str(e)}"

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

            cost = self._get_credits_for_type(purchase_request.phone_number_type)

            balance = await self.billing_service.get_credit_balance(organization_id)
            if balance.total_credits < cost:
                return (
                    None,
                    f"Insufficient credits. Need {cost} credits, have {balance.total_credits}",
                )

            purchased = self.twilio_service.purchase_phone_number(
                phone_number=purchase_request.phone_number
            )

            new_balance = balance.total_credits - cost

            record = PhoneNumberCreate(
                organization_id=organization_id,
                phone_number=purchase_request.phone_number,
                provider="twilio",
                provider_sid=purchased.sid,
                phone_number_type=purchase_request.phone_number_type,
                country_code=purchase_request.country_code,
                monthly_cost_credits=cost,
                status=PhoneNumberStatus.PURCHASED,
            )

            result = (
                self.supabase.table("phone_numbers")
                .insert(record.model_dump())
                .execute()
            )

            if not result.data:
                return None, "Failed to save phone number record"

            await self.billing_service.consume_credits(
                CreditConsumptionRequest(
                    organization_id=organization_id,
                    event_name="phone_number_purchase",
                    quantity=1,
                    metadata={
                        "phone_number": purchase_request.phone_number,
                        "provider_sid": purchased.sid,
                        "cost": cost,
                    },
                )
            )

            phone_number = PhoneNumber(**result.data[0])

            return (
                PhoneNumberPurchaseResponse(
                    success=True,
                    phone_number=phone_number,
                    message=f"Successfully purchased {purchase_request.phone_number}",
                    credit_balance_after=new_balance,
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
            return PhoneNumberListResponse(
                items=[], total_count=0, unused_count=0
            ), f"Failed to fetch phone numbers: {str(e)}"

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

    def _get_credits_for_type(self, phone_type: PhoneNumberType) -> int:
        """Get the credit cost for a phone number type.

        Args:
            phone_type: Type of phone number

        Returns:
            Monthly cost in credits
        """
        mapping = {
            PhoneNumberType.LOCAL: CREDITS_PER_LOCAL_NUMBER,
            PhoneNumberType.TOLL_FREE: CREDITS_PER_TOLL_FREE_NUMBER,
            PhoneNumberType.MOBILE: CREDITS_PER_MOBILE_NUMBER,
        }
        return mapping.get(phone_type, CREDITS_PER_LOCAL_NUMBER)


phone_number_service = PhoneNumberService()
