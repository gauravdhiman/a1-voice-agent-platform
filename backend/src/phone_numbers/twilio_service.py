"""
Twilio service for phone number operations.

This module provides integration with Twilio's Phone Numbers API for searching
available phone numbers and purchasing them.
"""

import logging
from typing import Optional

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
            logger.info(
                f"Twilio service initialized with account SID: {self.account_sid}"
            )

    def is_configured(self) -> bool:
        """Check if Twilio credentials are configured.

        Returns:
            True if Twilio is properly configured, False otherwise.
        """
        return self.client is not None

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
            >>> results = service.search_available_numbers(country_code="US", number_type="local")
            >>> for num in results:
            ...     print(num.phone_number)
        """
        if not self.client:
            raise ValueError("Twilio is not configured")

        logger.info(
            f"Searching for {number_type} numbers in {country_code}, "
            f"area_code={area_code}, contains={contains}, limit={limit}"
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
            logger.error(f"Error searching for available numbers: {e}")
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
            phone_number: The phone number to purchase (E.164 format, e.g., +15551234567)
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

        logger.info(f"Purchasing phone number: {phone_number}")

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

            logger.info(
                f"Successfully purchased phone number: {purchased.phone_number}, "
                f"SID: {purchased.sid}"
            )

            return purchased

        except Exception as e:
            logger.error(f"Error purchasing phone number {phone_number}: {e}")
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

        logger.info(f"Releasing phone number with SID: {phone_number_sid}")

        try:
            self.client.incoming_phone_numbers(phone_number_sid).delete()
            logger.info(f"Successfully released phone number: {phone_number_sid}")
            return True

        except Exception as e:
            logger.error(f"Error releasing phone number {phone_number_sid}: {e}")
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
            logger.error(f"Error fetching phone number {phone_number_sid}: {e}")
            return None


twilio_service = TwilioService()
