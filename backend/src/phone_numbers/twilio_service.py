"""
Twilio service for phone number operations.

This module provides integration with Twilio's Phone Numbers API for searching
available phone numbers and purchasing them.
"""

import logging
from typing import Optional

import httpx
from twilio.base.page import Page
from twilio.rest import Client
from twilio.rest.api.v2010.account.incoming_phone_number import (
    IncomingPhoneNumberInstance,
)

from shared.config.settings import settings

logger = logging.getLogger(__name__)


class TwilioService:
    """Service for interacting with Twilio Phone Numbers API.

    Provides methods to search for available phone numbers and purchase them
    using the Twilio API.

    Attributes:
        client: Twilio REST client instance
        account_sid: Twilio Account SID
    """

    def __init__(self) -> None:
        """Initialize Twilio service with credentials from settings."""
        self.account_sid = settings.twilio_account_sid
        self.auth_token = settings.twilio_auth_token

        if not self.account_sid or not self.auth_token:
            logger.warning(
                "Twilio credentials not configured. "
                "Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN environment variables."
            )
            self.client: Optional[Client] = None
        else:
            self.client = Client(self.account_sid, self.auth_token)
            logger.info("Twilio service initialized")

    def is_configured(self) -> bool:
        """Check if Twilio credentials are configured.

        Returns:
            True if Twilio is properly configured, False otherwise.
        """
        return self.client is not None

    async def send_sms(self, to_number: str, message: str) -> bool:
        """Send a bounded, server-side SMS through the configured Twilio account."""
        from_number = settings.twilio_sms_from_number
        if not self.account_sid or not self.auth_token or not from_number:
            return False
        if not to_number.startswith("+") or not from_number.startswith("+"):
            return False

        url = (
            "https://api.twilio.com/2010-04-01/Accounts/"
            f"{self.account_sid}/Messages.json"
        )
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
                response = await client.post(
                    url,
                    data={"To": to_number, "From": from_number, "Body": message},
                    auth=(self.account_sid, self.auth_token),
                )
            if response.status_code != 201:
                logger.warning(
                    "Twilio SMS request failed with status %s", response.status_code
                )
                return False
            return True
        except httpx.HTTPError as exc:
            logger.warning("Twilio SMS request failed (%s)", type(exc).__name__)
            return False

    def search_available_numbers(
        self,
        country_code: str = "US",
        number_type: str = "local",
        area_code: Optional[str] = None,
        contains: Optional[str] = None,
        limit: int = 50,
    ) -> Page:
        """Search for available phone numbers.

        Args:
            country_code: ISO 3166-1 alpha-2 country code (default: US)
            number_type: Type of numbers to search (local, toll_free, mobile)
            area_code: Optional area code to filter by
            contains: Optional pattern to search for in number
            limit: Maximum number of results (max 50)

        Returns:
            Page of available phone numbers from Twilio

        Raises:
            ValueError: If Twilio is not configured
            Exception: If the API call fails

        Example:
            >>> service = TwilioService()
            >>> results = service.search_available_numbers(
            ...     country_code="US", number_type="local"
            ... )
            >>> for num in results:
            ...     print(num.phone_number)
        """
        if not self.client:
            raise ValueError("Twilio is not configured")

        logger.info(
            f"Searching for {number_type} numbers in {country_code}, " f"limit={limit}"
        )

        try:
            if number_type == "toll_free":
                resource = self.client.available_phone_numbers(country_code).toll_free
            elif number_type == "mobile":
                resource = self.client.available_phone_numbers(country_code).mobile
            else:
                resource = self.client.available_phone_numbers(country_code).local

            params = {"limit": min(limit, 50)}

            if area_code:
                params["area_code"] = area_code
            if contains:
                params["contains"] = contains

            results = resource.list(**params)
            logger.info(f"Found {len(results)} available numbers")

            return results

        except Exception as e:
            logger.error(
                "Twilio number search failed (error_type=%s)", type(e).__name__
            )
            raise

    def purchase_phone_number(
        self,
        phone_number: str,
        voice_application_sid: Optional[str] = None,
        sms_application_sid: Optional[str] = None,
        voice_url: Optional[str] = None,
        voice_method: str = "POST",
        status_callback: Optional[str] = None,
        status_callback_method: str = "POST",
    ) -> IncomingPhoneNumberInstance:
        """Purchase a phone number.

        Args:
            phone_number: Number to purchase in E.164 format, for example
                ``+15551234567``.
            voice_application_sid: Optional Voice Application SID for handling calls
            sms_application_sid: Optional SMS Application SID for handling SMS
            voice_url: Optional public URL Twilio calls for inbound voice
            voice_method: HTTP method used for ``voice_url``
            status_callback: Optional public URL for call status callbacks
            status_callback_method: HTTP method used for ``status_callback``

        Returns:
            The purchased phone number instance

        Raises:
            ValueError: If Twilio is not configured
            Exception: If the purchase fails
        """
        if not self.client:
            raise ValueError("Twilio is not configured")

        logger.info("Starting Twilio phone number purchase")

        try:
            purchased = self.client.incoming_phone_numbers.create(
                phone_number=phone_number,
                voice_url=voice_url,
                voice_method=voice_method,
                status_callback=status_callback,
                status_callback_method=status_callback_method,
                voice_application_sid=voice_application_sid,
                sms_application_sid=sms_application_sid,
            )

            logger.info("Twilio phone number purchase completed")

            return purchased

        except Exception as e:
            logger.error(
                "Twilio phone number purchase failed (error_type=%s)",
                type(e).__name__,
            )
            raise

    def release_phone_number(self, phone_number_sid: str) -> bool:
        """Release (cancel) a phone number.

        Args:
            phone_number_sid: The SID of the phone number to release

        Returns:
            True if successful

        Raises:
            ValueError: If Twilio is not configured
            Exception: If the release fails
        """
        if not self.client:
            raise ValueError("Twilio is not configured")

        logger.info("Releasing Twilio phone number")

        try:
            self.client.incoming_phone_numbers(phone_number_sid).delete()
            logger.info("Twilio phone number release completed")
            return True

        except Exception as e:
            logger.error(
                "Twilio phone number release failed (error_type=%s)",
                type(e).__name__,
            )
            raise

    def get_phone_number(
        self, phone_number_sid: str
    ) -> Optional[IncomingPhoneNumberInstance]:
        """Get details of a purchased phone number.

        Args:
            phone_number_sid: The SID of the phone number

        Returns:
            Phone number instance or None if not found

        Raises:
            ValueError: If Twilio is not configured
            Exception: If the API call fails
        """
        if not self.client:
            raise ValueError("Twilio is not configured")

        try:
            return self.client.incoming_phone_numbers(phone_number_sid).fetch()
        except Exception as e:
            logger.error(
                "Twilio phone number lookup failed (error_type=%s)",
                type(e).__name__,
            )
            return None


twilio_service = TwilioService()
