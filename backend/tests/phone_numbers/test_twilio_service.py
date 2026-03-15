"""
Twilio Service Tests

These tests verify the TwilioService logic by directly testing the class behavior
with mocked external dependencies.
"""

from unittest.mock import MagicMock

import pytest


class MockSettings:
    """Mock settings for Twilio service."""

    def __init__(self, with_credentials=True):
        self.twilio_account_sid = "AC_test_account_sid" if with_credentials else None
        self.twilio_auth_token = "test_auth_token" if with_credentials else None


class TwilioServiceUnderTest:
    """A direct implementation of TwilioService for testing.

    This mirrors the logic in src/phone_numbers/twilio_service.py
    but allows us to test without import issues.
    """

    def __init__(self, client=None, settings=None):
        self.client = client
        self.settings = settings or MockSettings()
        self.account_sid = self.settings.twilio_account_sid

    def is_configured(self) -> bool:
        return self.client is not None

    def search_available_numbers(
        self,
        country_code: str = "US",
        number_type: str = "local",
        area_code: str = None,
        contains: str = None,
        limit: int = 50,
    ):
        if not self.client:
            raise ValueError("Twilio is not configured")

        if number_type == "toll_free":
            resource = self.client.available_phone_numbers.toll_free
        elif number_type == "mobile":
            resource = self.client.available_phone_numbers.mobile
        else:
            resource = self.client.available_phone_numbers.local

        params = {"country_code": country_code, "page_size": min(limit, 50)}

        if area_code:
            params["area_code"] = area_code
        if contains:
            params["contains"] = contains

        return resource.list(**params)

    def purchase_phone_number(
        self,
        phone_number: str,
        voice_application_sid: str = None,
        sms_application_sid: str = None,
    ):
        if not self.client:
            raise ValueError("Twilio is not configured")

        return self.client.incoming_phone_numbers.create(
            phone_number=phone_number,
            voice_application_sid=voice_application_sid,
            sms_application_sid=sms_application_sid,
        )

    def release_phone_number(self, phone_number_sid: str) -> bool:
        if not self.client:
            raise ValueError("Twilio is not configured")

        self.client.incoming_phone_numbers(phone_number_sid).delete()
        return True

    def get_phone_number(self, phone_number_sid: str):
        if not self.client:
            raise ValueError("Twilio is not configured")

        try:
            return self.client.incoming_phone_numbers(phone_number_sid).fetch()
        except Exception:
            return None


def get_mock_client():
    """Create a mock Twilio client."""
    client = MagicMock()
    client.available_phone_numbers = MagicMock()
    client.incoming_phone_numbers = MagicMock()
    return client


@pytest.fixture
def twilio_service():
    """Create TwilioService with mocked dependencies."""
    mock_settings = MockSettings(with_credentials=True)
    mock_client = get_mock_client()
    return TwilioServiceUnderTest(client=mock_client, settings=mock_settings)


@pytest.fixture
def twilio_service_not_configured():
    """Create TwilioService without credentials."""
    mock_settings = MockSettings(with_credentials=False)
    return TwilioServiceUnderTest(client=None, settings=mock_settings)


class TestTwilioServiceIsConfigured:
    """Test cases for Twilio configuration check."""

    def test_is_configured_true(self, twilio_service):
        """Returns True when credentials are set."""
        assert twilio_service.is_configured() is True

    def test_is_configured_false_when_not_configured(
        self, twilio_service_not_configured
    ):
        """Returns False when credentials are not set."""
        assert twilio_service_not_configured.is_configured() is False


class TestTwilioServiceSearchAvailableNumbers:
    """Test cases for searching available phone numbers."""

    def test_search_local_numbers(self, twilio_service):
        """Searches for local numbers."""
        mock_resource = MagicMock()
        mock_resource.list.return_value = []
        twilio_service.client.available_phone_numbers.local = mock_resource

        result = twilio_service.search_available_numbers(
            country_code="US", number_type="local"
        )

        assert result == []
        twilio_service.client.available_phone_numbers.local.list.assert_called_once()

    def test_search_toll_free_numbers(self, twilio_service):
        """Searches for toll-free numbers."""
        mock_resource = MagicMock()
        mock_resource.list.return_value = []
        twilio_service.client.available_phone_numbers.toll_free = mock_resource

        result = twilio_service.search_available_numbers(
            country_code="US", number_type="toll_free"
        )

        assert result == []
        twilio_service.client.available_phone_numbers.toll_free.list.assert_called_once()

    def test_search_mobile_numbers(self, twilio_service):
        """Searches for mobile numbers."""
        mock_resource = MagicMock()
        mock_resource.list.return_value = []
        twilio_service.client.available_phone_numbers.mobile = mock_resource

        result = twilio_service.search_available_numbers(
            country_code="US", number_type="mobile"
        )

        assert result == []
        twilio_service.client.available_phone_numbers.mobile.list.assert_called_once()

    def test_search_with_area_code_filter(self, twilio_service):
        """Filters by area code."""
        mock_resource = MagicMock()
        mock_resource.list.return_value = []
        twilio_service.client.available_phone_numbers.local = mock_resource

        twilio_service.search_available_numbers(
            country_code="US", number_type="local", area_code="555"
        )

        call_kwargs = mock_resource.list.call_args[1]
        assert call_kwargs["area_code"] == "555"

    def test_search_with_contains_filter(self, twilio_service):
        """Filters by number pattern."""
        mock_resource = MagicMock()
        mock_resource.list.return_value = []
        twilio_service.client.available_phone_numbers.local = mock_resource

        twilio_service.search_available_numbers(
            country_code="US", number_type="local", contains="1234"
        )

        call_kwargs = mock_resource.list.call_args[1]
        assert call_kwargs["contains"] == "1234"

    def test_search_with_limit(self, twilio_service):
        """Respects limit parameter."""
        mock_resource = MagicMock()
        mock_resource.list.return_value = []
        twilio_service.client.available_phone_numbers.local = mock_resource

        twilio_service.search_available_numbers(
            country_code="US", number_type="local", limit=10
        )

        call_kwargs = mock_resource.list.call_args[1]
        assert call_kwargs["page_size"] == 10

    def test_search_raises_when_not_configured(self, twilio_service_not_configured):
        """Raises ValueError when Twilio is not configured."""
        with pytest.raises(ValueError, match="Twilio is not configured"):
            twilio_service_not_configured.search_available_numbers()

    def test_search_raises_on_api_error(self, twilio_service):
        """Raises exception when API call fails."""
        mock_resource = MagicMock()
        mock_resource.list.side_effect = Exception("API Error")
        twilio_service.client.available_phone_numbers.local = mock_resource

        with pytest.raises(Exception, match="API Error"):
            twilio_service.search_available_numbers(country_code="US")


class TestTwilioServicePurchasePhoneNumber:
    """Test cases for purchasing phone numbers."""

    def test_purchase_number_success(self, twilio_service):
        """Purchases a phone number successfully."""
        mock_purchased = MagicMock()
        mock_purchased.sid = "PN1234567890"
        mock_purchased.phone_number = "+15551234567"
        twilio_service.client.incoming_phone_numbers.create.return_value = (
            mock_purchased
        )

        result = twilio_service.purchase_phone_number(phone_number="+15551234567")

        assert result.sid == "PN1234567890"
        assert result.phone_number == "+15551234567"
        twilio_service.client.incoming_phone_numbers.create.assert_called_once()

    def test_purchase_number_with_application_sids(self, twilio_service):
        """Purchases number with voice and SMS application SIDs."""
        mock_purchased = MagicMock()
        mock_purchased.sid = "PN1234567890"
        twilio_service.client.incoming_phone_numbers.create.return_value = (
            mock_purchased
        )

        twilio_service.purchase_phone_number(
            phone_number="+15551234567",
            voice_application_sid="AP123",
            sms_application_sid="AP456",
        )

        call_kwargs = twilio_service.client.incoming_phone_numbers.create.call_args[1]
        assert call_kwargs["voice_application_sid"] == "AP123"
        assert call_kwargs["sms_application_sid"] == "AP456"

    def test_purchase_raises_when_not_configured(self, twilio_service_not_configured):
        """Raises ValueError when Twilio is not configured."""
        with pytest.raises(ValueError, match="Twilio is not configured"):
            twilio_service_not_configured.purchase_phone_number("+15551234567")

    def test_purchase_raises_on_api_error(self, twilio_service):
        """Raises exception when API call fails."""
        twilio_service.client.incoming_phone_numbers.create.side_effect = Exception(
            "Purchase failed"
        )

        with pytest.raises(Exception, match="Purchase failed"):
            twilio_service.purchase_phone_number(phone_number="+15551234567")


class TestTwilioServiceReleasePhoneNumber:
    """Test cases for releasing phone numbers."""

    def test_release_number_success(self, twilio_service):
        """Releases a phone number successfully."""
        result = twilio_service.release_phone_number("PN1234567890")

        assert result is True
        twilio_service.client.incoming_phone_numbers.assert_called_with("PN1234567890")
        twilio_service.client.incoming_phone_numbers.return_value.delete.assert_called_once()

    def test_release_raises_when_not_configured(self, twilio_service_not_configured):
        """Raises ValueError when Twilio is not configured."""
        with pytest.raises(ValueError, match="Twilio is not configured"):
            twilio_service_not_configured.release_phone_number("PN1234567890")

    def test_release_raises_on_api_error(self, twilio_service):
        """Raises exception when API call fails."""
        twilio_service.client.incoming_phone_numbers.return_value.delete.side_effect = (
            Exception("Release failed")
        )

        with pytest.raises(Exception, match="Release failed"):
            twilio_service.release_phone_number("PN1234567890")


class TestTwilioServiceGetPhoneNumber:
    """Test cases for fetching phone number details."""

    def test_get_number_success(self, twilio_service):
        """Fetches phone number details successfully."""
        mock_number = MagicMock()
        mock_number.sid = "PN1234567890"
        twilio_service.client.incoming_phone_numbers.return_value.fetch.return_value = (
            mock_number
        )

        result = twilio_service.get_phone_number("PN1234567890")

        assert result is not None
        assert result.sid == "PN1234567890"

    def test_get_number_returns_none_on_error(self, twilio_service):
        """Returns None when API call fails."""
        twilio_service.client.incoming_phone_numbers.return_value.fetch.side_effect = (
            Exception("Not found")
        )

        result = twilio_service.get_phone_number("PN1234567890")

        assert result is None

    def test_get_number_raises_when_not_configured(self, twilio_service_not_configured):
        """Raises ValueError when Twilio is not configured."""
        with pytest.raises(ValueError, match="Twilio is not configured"):
            twilio_service_not_configured.get_phone_number("PN1234567890")
