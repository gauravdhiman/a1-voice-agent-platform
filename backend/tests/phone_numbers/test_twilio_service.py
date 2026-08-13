"""Unit tests for the production Twilio phone-number provider adapter."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.phone_numbers.twilio_service import TwilioService


def _mock_client() -> MagicMock:
    """Create a Twilio client double with the resource tree used by production."""
    client = MagicMock()
    client.available_phone_numbers.return_value.local = MagicMock()
    client.available_phone_numbers.return_value.toll_free = MagicMock()
    client.available_phone_numbers.return_value.mobile = MagicMock()
    client.incoming_phone_numbers.create.return_value = SimpleNamespace(
        sid="PN1234567890",
        phone_number="+15551234567",
    )
    return client


@pytest.fixture
def twilio_service() -> TwilioService:
    """Build the real adapter with a mocked Twilio REST client."""
    service = TwilioService.__new__(TwilioService)
    service.account_sid = "AC_test_account_sid"
    service.auth_token = "test_auth_token"
    service.client = _mock_client()
    return service


@pytest.fixture
def twilio_service_not_configured() -> TwilioService:
    """Build the real adapter without provider credentials."""
    service = TwilioService.__new__(TwilioService)
    service.account_sid = None
    service.auth_token = None
    service.client = None
    return service


class TestTwilioServiceInitialization:
    """Initialization and provider-configuration behavior."""

    def test_initializes_client_when_credentials_exist(self):
        """Credentials create a Twilio client with the configured values."""
        configured_settings = SimpleNamespace(
            twilio_account_sid="AC_test",
            twilio_auth_token="secret",
        )
        with patch(
            "src.phone_numbers.twilio_service.settings",
            configured_settings,
        ), patch("src.phone_numbers.twilio_service.Client") as client_cls:
            service = TwilioService()

        client_cls.assert_called_once_with("AC_test", "secret")
        assert service.is_configured() is True

    def test_stays_unconfigured_without_credentials(self):
        """Missing credentials leave the provider adapter disabled."""
        missing_settings = SimpleNamespace(
            twilio_account_sid=None,
            twilio_auth_token=None,
        )
        with patch("src.phone_numbers.twilio_service.settings", missing_settings):
            service = TwilioService()

        assert service.is_configured() is False


class TestTwilioServiceSearch:
    """Available-number search behavior against the real adapter."""

    @pytest.mark.parametrize(
        ("number_type", "resource_name"),
        [
            ("local", "local"),
            ("toll_free", "toll_free"),
            ("mobile", "mobile"),
            ("unsupported", "local"),
        ],
    )
    def test_selects_provider_resource_and_forwards_filters(
        self,
        twilio_service: TwilioService,
        number_type: str,
        resource_name: str,
    ):
        """Search forwards the country, filters, and capped result limit."""
        resource = getattr(
            twilio_service.client.available_phone_numbers.return_value,
            resource_name,
        )
        resource.list.return_value = []

        result = twilio_service.search_available_numbers(
            country_code="US",
            number_type=number_type,
            area_code="480",
            contains="+1480",
            limit=100,
        )

        assert result == []
        twilio_service.client.available_phone_numbers.assert_called_once_with("US")
        resource.list.assert_called_once_with(
            limit=50,
            area_code="480",
            contains="+1480",
        )

    def test_search_omits_empty_optional_filters(self, twilio_service: TwilioService):
        """Empty area and pattern inputs are not sent to Twilio."""
        resource = twilio_service.client.available_phone_numbers.return_value.local
        resource.list.return_value = []

        twilio_service.search_available_numbers(
            country_code="CA",
            number_type="local",
            area_code="",
            contains=None,
            limit=5,
        )

        resource.list.assert_called_once_with(limit=5)

    def test_search_requires_configuration(
        self, twilio_service_not_configured: TwilioService
    ):
        """Unconfigured deployments fail before any provider call."""
        with pytest.raises(ValueError, match="Twilio is not configured"):
            twilio_service_not_configured.search_available_numbers()

    def test_search_propagates_provider_errors(self, twilio_service: TwilioService):
        """Provider failures remain visible to the service-layer compensator."""
        resource = twilio_service.client.available_phone_numbers.return_value.local
        resource.list.side_effect = RuntimeError("provider unavailable")

        with pytest.raises(RuntimeError, match="provider unavailable"):
            twilio_service.search_available_numbers()


class TestTwilioServicePurchase:
    """Purchase and automatic webhook configuration behavior."""

    def test_purchase_forwards_webhook_configuration(
        self, twilio_service: TwilioService
    ):
        """A purchase sends both platform callback URLs in one provider request."""
        result = twilio_service.purchase_phone_number(
            phone_number="+15551234567",
            voice_url="https://api.example.com/voice",
            status_callback="https://api.example.com/status",
        )

        assert result.sid == "PN1234567890"
        twilio_service.client.incoming_phone_numbers.create.assert_called_once_with(
            phone_number="+15551234567",
            voice_url="https://api.example.com/voice",
            voice_method="POST",
            status_callback="https://api.example.com/status",
            status_callback_method="POST",
            voice_application_sid=None,
            sms_application_sid=None,
        )

    def test_purchase_forwards_application_sids(self, twilio_service: TwilioService):
        """Optional TwiML application identifiers remain supported."""
        twilio_service.purchase_phone_number(
            phone_number="+15551234567",
            voice_application_sid="AP123",
            sms_application_sid="AP456",
        )

        kwargs = twilio_service.client.incoming_phone_numbers.create.call_args.kwargs
        assert kwargs["voice_application_sid"] == "AP123"
        assert kwargs["sms_application_sid"] == "AP456"

    def test_purchase_requires_configuration(
        self, twilio_service_not_configured: TwilioService
    ):
        """Purchasing is rejected when the provider is not configured."""
        with pytest.raises(ValueError, match="Twilio is not configured"):
            twilio_service_not_configured.purchase_phone_number("+15551234567")

    def test_purchase_propagates_provider_errors(self, twilio_service: TwilioService):
        """Provider purchase failures are returned to lifecycle compensation."""
        twilio_service.client.incoming_phone_numbers.create.side_effect = RuntimeError(
            "purchase failed"
        )

        with pytest.raises(RuntimeError, match="purchase failed"):
            twilio_service.purchase_phone_number("+15551234567")


class TestTwilioServiceRelease:
    """Provider release behavior."""

    def test_release_deletes_provider_number(self, twilio_service: TwilioService):
        """Release calls Twilio delete and returns success."""
        assert twilio_service.release_phone_number("PN1234567890") is True
        twilio_service.client.incoming_phone_numbers.assert_called_once_with(
            "PN1234567890"
        )
        twilio_service.client.incoming_phone_numbers.return_value.delete.assert_called_once()

    def test_release_requires_configuration(
        self, twilio_service_not_configured: TwilioService
    ):
        """Release is rejected when no provider credentials are configured."""
        with pytest.raises(ValueError, match="Twilio is not configured"):
            twilio_service_not_configured.release_phone_number("PN1234567890")

    def test_release_propagates_provider_errors(self, twilio_service: TwilioService):
        """Release errors are left to the caller to mark release_pending."""
        twilio_service.client.incoming_phone_numbers.return_value.delete.side_effect = (
            RuntimeError("release failed")
        )

        with pytest.raises(RuntimeError, match="release failed"):
            twilio_service.release_phone_number("PN1234567890")


class TestTwilioServiceGet:
    """Provider lookup behavior."""

    def test_get_returns_provider_number(self, twilio_service: TwilioService):
        """A successful fetch returns the provider instance."""
        expected = SimpleNamespace(sid="PN1234567890")
        twilio_service.client.incoming_phone_numbers.return_value.fetch.return_value = (
            expected
        )

        assert twilio_service.get_phone_number("PN1234567890") is expected

    def test_get_returns_none_when_provider_fetch_fails(
        self, twilio_service: TwilioService
    ):
        """A missing provider number is represented as None."""
        twilio_service.client.incoming_phone_numbers.return_value.fetch.side_effect = (
            RuntimeError("not found")
        )

        assert twilio_service.get_phone_number("PN1234567890") is None

    def test_get_requires_configuration(
        self, twilio_service_not_configured: TwilioService
    ):
        """Lookup is rejected when the provider is not configured."""
        with pytest.raises(ValueError, match="Twilio is not configured"):
            twilio_service_not_configured.get_phone_number("PN1234567890")
