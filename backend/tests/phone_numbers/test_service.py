"""
Phone Number Service Tests
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from shared.organization.phone_number_models import PhoneNumberStatus, PhoneNumberType


@pytest.fixture
def phone_number_service(mock_supabase_client):
    """Create PhoneNumberService instance with fresh mocks for each test."""
    from src.phone_numbers.service import PhoneNumberService

    with patch("src.phone_numbers.service.supabase_config") as mock_config:
        mock_config.client = mock_supabase_client

        service = PhoneNumberService()
        service.supabase = mock_supabase_client
        service.billing_service = MagicMock()
        service.entitlement_service = MagicMock()
        service.entitlement_service.assert_limit = AsyncMock()
        service.entitlement_service.get_org_entitlements = AsyncMock(
            return_value=MagicMock(
                is_entitled=True,
                plan_product_slug="starter",
                cancel_at_period_end=False,
                access_until=None,
            )
        )
        # Existing tests exercise paid rentals unless they explicitly model
        # an organization with its first included US local line available.
        service._has_active_included_us_local_number = AsyncMock(return_value=True)

        yield service


@pytest.fixture
def sample_org_id():
    """Sample organization ID."""
    return uuid4()


@pytest.fixture
def sample_agent_id():
    """Sample agent ID."""
    return uuid4()


@pytest.fixture
def sample_phone_number_id():
    """Sample phone number ID."""
    return uuid4()


@pytest.fixture
def sample_available_number():
    """Sample available phone number from Twilio."""
    mock_num = MagicMock()
    mock_num.phone_number = "+15551234567"
    mock_num.area_code = "555"
    mock_num.locality = "Los Angeles"
    mock_num.postal_code = "90001"
    mock_capabilities = MagicMock()
    mock_capabilities.voice = True
    mock_capabilities.sms = True
    mock_capabilities.mms = False
    mock_num.capabilities = mock_capabilities
    return mock_num


@pytest.fixture
def sample_purchased_phone_number(sample_org_id, sample_phone_number_id):
    """Sample purchased phone number data."""
    now = datetime.now(timezone.utc)
    return {
        "id": str(sample_phone_number_id),
        "organization_id": str(sample_org_id),
        "phone_number": "+15551234567",
        "provider": "twilio",
        "provider_sid": "PN1234567890",
        "phone_number_type": "local",
        "country_code": "US",
        "area_code": "555",
        "monthly_cost_credits": 200,
        "status": "purchased",
        "assigned_agent_id": None,
        "is_incoming_enabled": True,
        "is_outgoing_enabled": False,
        "purchased_at": now.isoformat(),
        "cancelled_at": None,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }


@pytest.fixture
def mock_twilio_service():
    """Create a mocked Twilio service."""
    with patch("src.phone_numbers.service.twilio_service") as mock:
        mock.is_configured.return_value = True
        mock.search_available_numbers.return_value = []
        mock.purchase_phone_number.return_value = MagicMock(
            sid="PN1234567890",
            phone_number="+15551234567",
        )
        mock.release_phone_number.return_value = True
        yield mock


class TestPhoneNumberServiceSearch:
    """Test cases for phone number search."""

    @pytest.mark.asyncio
    async def test_get_routable_agent_id_uses_joined_active_agent_lookup(
        self,
        phone_number_service,
        mock_supabase_client,
        sample_agent_id,
    ):
        """Inbound routing resolves the agent in the phone-number query."""
        mock_supabase_client.table.return_value.execute.return_value = MagicMock(
            data=[
                {
                    "assigned_agent_id": str(sample_agent_id),
                    "voice_agents": {
                        "id": str(sample_agent_id),
                        "is_active": True,
                    },
                }
            ]
        )

        result, error = await phone_number_service.get_routable_agent_id(
            "+1 (555) 123-4567"
        )

        assert error is None
        assert result == sample_agent_id
        mock_supabase_client.table.assert_called_once_with("phone_numbers")
        mock_supabase_client.table.return_value.select.assert_called_once_with(
            "assigned_agent_id, voice_agents!inner(id, is_active)"
        )

    @pytest.mark.asyncio
    async def test_search_available_numbers_success(
        self, phone_number_service, mock_supabase_client, sample_available_number
    ):
        """Returns available numbers from Twilio."""
        from shared.organization.phone_number_models import PhoneNumberSearchRequest

        with patch.object(phone_number_service, "twilio_service") as mock_twilio:
            mock_twilio.is_configured.return_value = True
            mock_twilio.search_available_numbers.return_value = [
                sample_available_number
            ]

            request = PhoneNumberSearchRequest(
                country_code="US",
                phone_number_type=PhoneNumberType.LOCAL,
                area_code="555",
            )

            result, error = await phone_number_service.search_available(request)

            assert error is None
            assert len(result.items) == 1
            assert result.items[0].phone_number == "+15551234567"
            assert result.items[0].monthly_cost_credits == 80

    @pytest.mark.asyncio
    async def test_search_prices_first_us_local_line_as_included(
        self,
        phone_number_service,
        sample_org_id,
        sample_available_number,
    ):
        """The first US local platform number is returned at zero credits."""
        from shared.organization.phone_number_models import PhoneNumberSearchRequest

        phone_number_service._has_active_included_us_local_number = AsyncMock(
            return_value=False
        )
        phone_number_service._has_active_paid_plan_allowance = AsyncMock(
            return_value=True
        )
        phone_number_service._get_credits_for_type = AsyncMock(return_value=80)
        with patch.object(phone_number_service, "twilio_service") as mock_twilio:
            mock_twilio.is_configured.return_value = True
            mock_twilio.search_available_numbers.return_value = [
                sample_available_number
            ]

            response, error = await phone_number_service.search_available(
                PhoneNumberSearchRequest(country_code="US"), sample_org_id
            )

        assert error is None
        assert response.items[0].is_included_in_plan is True
        assert response.items[0].monthly_cost_credits == 0

    @pytest.mark.asyncio
    async def test_free_plan_never_qualifies_for_the_included_us_local_line(
        self, phone_number_service, sample_org_id
    ):
        phone_number_service._has_active_included_us_local_number = AsyncMock(
            return_value=False
        )
        phone_number_service._has_active_paid_plan_allowance = AsyncMock(
            return_value=False
        )

        qualifies = await phone_number_service._qualifies_for_included_us_local_number(
            sample_org_id, PhoneNumberType.LOCAL, "US"
        )

        assert qualifies is False
        phone_number_service._has_active_paid_plan_allowance.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_free_plan_can_search_but_does_not_get_included_number(
        self,
        phone_number_service,
        sample_org_id,
        sample_available_number,
    ):
        """Catalog search is read-only; the free plan cannot claim a paid benefit."""
        from shared.organization.phone_number_models import PhoneNumberSearchRequest

        phone_number_service._has_active_included_us_local_number = AsyncMock(
            return_value=False
        )
        phone_number_service._has_active_paid_plan_allowance = AsyncMock(
            return_value=False
        )
        phone_number_service._get_credits_for_type = AsyncMock(return_value=80)
        with patch.object(phone_number_service, "twilio_service") as mock_twilio:
            mock_twilio.is_configured.return_value = True
            mock_twilio.search_available_numbers.return_value = [
                sample_available_number
            ]

            response, error = await phone_number_service.search_available(
                PhoneNumberSearchRequest(country_code="US"), sample_org_id
            )

        assert error is None
        assert len(response.items) == 1
        assert response.items[0].is_included_in_plan is False
        assert response.items[0].monthly_cost_credits == 80
        phone_number_service.entitlement_service.assert_limit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_search_prices_additional_us_local_line_at_system_rate(
        self,
        phone_number_service,
        sample_org_id,
        sample_available_number,
    ):
        """An active included line makes later US local lines paid rentals."""
        from shared.organization.phone_number_models import PhoneNumberSearchRequest

        phone_number_service._has_active_included_us_local_number = AsyncMock(
            return_value=True
        )
        phone_number_service._get_credits_for_type = AsyncMock(return_value=80)
        with patch.object(phone_number_service, "twilio_service") as mock_twilio:
            mock_twilio.is_configured.return_value = True
            mock_twilio.search_available_numbers.return_value = [
                sample_available_number
            ]

            response, error = await phone_number_service.search_available(
                PhoneNumberSearchRequest(country_code="US"), sample_org_id
            )

        assert error is None
        assert response.items[0].is_included_in_plan is False
        assert response.items[0].monthly_cost_credits == 80

    @pytest.mark.asyncio
    async def test_search_reports_unavailable_when_not_configured(
        self, phone_number_service
    ):
        """An unavailable provider is not misreported as empty inventory."""
        from shared.organization.phone_number_models import PhoneNumberSearchRequest
        from src.phone_numbers.service import PHONE_NUMBER_SEARCH_UNAVAILABLE

        with patch.object(phone_number_service, "twilio_service") as mock_twilio:
            mock_twilio.is_configured.return_value = False

            request = PhoneNumberSearchRequest()

            result, error = await phone_number_service.search_available(request)

            assert error == PHONE_NUMBER_SEARCH_UNAVAILABLE
            assert result.items == []
            assert result.total_count == 0

    @pytest.mark.asyncio
    async def test_search_handles_exception(
        self, phone_number_service, mock_supabase_client, caplog
    ):
        """Provider diagnostics stay out of public errors and logs."""
        from shared.organization.phone_number_models import PhoneNumberSearchRequest
        from src.phone_numbers.service import PHONE_NUMBER_SEARCH_UNAVAILABLE

        provider_diagnostic = (
            "HTTP 401 account AC1234567890 authentication failed; credentials inactive"
        )

        with patch.object(phone_number_service, "twilio_service") as mock_twilio:
            mock_twilio.is_configured.return_value = True
            mock_twilio.search_available_numbers.side_effect = Exception(
                provider_diagnostic
            )

            request = PhoneNumberSearchRequest()

            result, error = await phone_number_service.search_available(request)

            assert error == PHONE_NUMBER_SEARCH_UNAVAILABLE
            assert provider_diagnostic not in error
            assert "AC1234567890" not in caplog.text

    @pytest.mark.asyncio
    async def test_search_with_toll_free_type(self, phone_number_service):
        """Searches for toll-free numbers."""
        from shared.organization.phone_number_models import PhoneNumberSearchRequest

        with patch.object(phone_number_service, "twilio_service") as mock_twilio:
            mock_twilio.is_configured.return_value = True
            mock_twilio.search_available_numbers.return_value = []

            request = PhoneNumberSearchRequest(
                phone_number_type=PhoneNumberType.TOLL_FREE
            )

            result, error = await phone_number_service.search_available(request)

            assert error is None
            mock_twilio.search_available_numbers.assert_called_once()
            call_args = mock_twilio.search_available_numbers.call_args
            assert call_args[1]["number_type"] == "toll_free"


class TestPhoneNumberServicePurchase:
    """Test cases for phone number purchase."""

    @pytest.mark.asyncio
    async def test_free_plan_cannot_claim_an_included_us_line(
        self, phone_number_service, sample_org_id
    ):
        """A positive number limit does not create a Free-plan line benefit."""
        from shared.organization.phone_number_models import PhoneNumberPurchaseRequest

        phone_number_service._has_active_included_us_local_number = AsyncMock(
            return_value=False
        )
        phone_number_service._has_active_paid_plan_allowance = AsyncMock(
            return_value=False
        )
        phone_number_service._phone_number_limit_error = AsyncMock(return_value=None)

        with patch.object(phone_number_service, "twilio_service") as twilio:
            twilio.is_configured.return_value = True
            result, error = await phone_number_service.purchase_number(
                sample_org_id,
                PhoneNumberPurchaseRequest(
                    phone_number="+15551234567",
                    expected_included_in_plan=True,
                ),
            )

        assert result is None
        assert error and "Search again" in error
        phone_number_service.billing_service.consume_credits.assert_not_called()
        twilio.purchase_phone_number.assert_not_called()

    @pytest.mark.asyncio
    async def test_first_us_local_purchase_uses_plan_allowance(
        self,
        phone_number_service,
        mock_supabase_client,
        sample_org_id,
        sample_phone_number_id,
    ):
        """The first US local line is provisioned without a credit debit."""
        from shared.organization.phone_number_models import PhoneNumberPurchaseRequest

        now = datetime.now(timezone.utc)
        phone_number_service._has_active_included_us_local_number = AsyncMock(
            return_value=False
        )
        phone_number_service.billing_service.get_credit_balance = AsyncMock(
            return_value=MagicMock(total_credits=2500)
        )
        table = MagicMock()
        mock_supabase_client.table.return_value = table
        table.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": str(sample_phone_number_id)}]
        )
        purchased_row = {
            "id": str(sample_phone_number_id),
            "organization_id": str(sample_org_id),
            "phone_number": "+15551234567",
            "provider": "twilio",
            "provider_sid": "PN1234567890",
            "phone_number_type": "local",
            "country_code": "US",
            "area_code": "555",
            "monthly_cost_credits": 0,
            "is_included_in_plan": True,
            "status": "purchased",
            "assigned_agent_id": None,
            "is_incoming_enabled": True,
            "is_outgoing_enabled": False,
            "billing_status": "active",
            "billing_mode": "platform_rental",
            "provisioning_source": "platform",
            "management_mode": "platform_managed",
            "configuration_status": "configured",
            "next_billing_at": (now + timedelta(days=30)).isoformat(),
            "purchased_at": now.isoformat(),
            "last_verified_at": now.isoformat(),
            "cancelled_at": None,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        table.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[purchased_row]
        )

        with patch.object(phone_number_service, "twilio_service") as mock_twilio:
            mock_twilio.is_configured.return_value = True
            mock_twilio.purchase_phone_number.return_value = MagicMock(
                sid="PN1234567890", phone_number="+15551234567"
            )

            response, error = await phone_number_service.purchase_number(
                sample_org_id,
                PhoneNumberPurchaseRequest(
                    phone_number="+15551234567",
                    expected_included_in_plan=True,
                ),
            )

        assert error is None
        assert response is not None
        assert response.credit_balance_after == 2500
        assert response.phone_number.is_included_in_plan is True
        assert response.phone_number.monthly_cost_credits == 0
        phone_number_service.billing_service.consume_credits.assert_not_called()

    @pytest.mark.asyncio
    async def test_stale_included_selection_does_not_charge(
        self, phone_number_service, sample_org_id
    ):
        """A concurrent included-line claim asks the user to refresh pricing."""
        from shared.organization.phone_number_models import PhoneNumberPurchaseRequest

        phone_number_service._has_active_included_us_local_number = AsyncMock(
            return_value=True
        )
        with patch.object(phone_number_service, "twilio_service") as mock_twilio:
            mock_twilio.is_configured.return_value = True

            response, error = await phone_number_service.purchase_number(
                sample_org_id,
                PhoneNumberPurchaseRequest(
                    phone_number="+15551234567",
                    expected_included_in_plan=True,
                ),
            )

        assert response is None
        assert error is not None and "Search again" in error
        phone_number_service.billing_service.consume_credits.assert_not_called()
        mock_twilio.purchase_phone_number.assert_not_called()

    @pytest.mark.asyncio
    async def test_purchase_number_success(
        self,
        phone_number_service,
        mock_supabase_client,
        sample_org_id,
        sample_phone_number_id,
    ):
        """Purchases a phone number successfully."""
        from shared.organization.phone_number_models import PhoneNumberPurchaseRequest

        now = datetime.now(timezone.utc)

        mock_balance = MagicMock()
        mock_balance.total_credits = 1000

        phone_number_service.billing_service.get_credit_balance = AsyncMock(
            return_value=mock_balance
        )
        phone_number_service.billing_service.consume_credits = AsyncMock(
            return_value=MagicMock(success=True, balance_after=800)
        )
        phone_number_service._get_credits_for_type = AsyncMock(return_value=80)
        phone_number_service._has_active_included_us_local_number = AsyncMock(
            return_value=True
        )

        with patch.object(phone_number_service, "twilio_service") as mock_twilio:
            mock_twilio.is_configured.return_value = True
            mock_twilio.purchase_phone_number.return_value = MagicMock(
                sid="PN1234567890", phone_number="+15551234567"
            )

            mock_response = MagicMock()
            mock_response.data = [
                {
                    "id": str(sample_phone_number_id),
                    "organization_id": str(sample_org_id),
                    "phone_number": "+15551234567",
                    "provider": "twilio",
                    "provider_sid": "PN1234567890",
                    "phone_number_type": "local",
                    "country_code": "US",
                    "area_code": "555",
                    "monthly_cost_credits": 80,
                    "status": "purchased",
                    "assigned_agent_id": None,
                    "is_incoming_enabled": True,
                    "is_outgoing_enabled": False,
                    "purchased_at": now.isoformat(),
                    "cancelled_at": None,
                    "created_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                }
            ]
            table = mock_supabase_client.table.return_value
            table.execute.side_effect = [
                MagicMock(data=[]),
                mock_response,
                MagicMock(data=mock_response.data),
            ]

            request = PhoneNumberPurchaseRequest(
                phone_number="+15551234567",
                country_code="US",
                phone_number_type=PhoneNumberType.LOCAL,
            )

            request_key = "client-purchase-key"
            result, error = await phone_number_service.purchase_number(
                sample_org_id, request, idempotency_key=request_key
            )

            assert error is None
            assert result is not None
            assert result.success is True
            assert result.phone_number.phone_number == "+15551234567"
            assert result.credit_balance_after == 800
            consume_request = (
                phone_number_service.billing_service.consume_credits.call_args.args[0]
            )
            assert consume_request.event_name == "phone_number_us_local_month"
            assert consume_request.idempotency_key
            assert consume_request.idempotency_key != request_key
            inserted_row = table.insert.call_args.args[0]
            assert inserted_row["provisioning_idempotency_key"] == request_key

    @pytest.mark.asyncio
    async def test_purchase_uses_current_system_rate_and_balance(
        self,
        phone_number_service,
        mock_supabase_client,
        sample_org_id,
        sample_phone_number_id,
    ):
        """Purchase uses the configured system rate instead of a code constant."""
        from shared.organization.phone_number_models import PhoneNumberPurchaseRequest

        now = datetime.now(timezone.utc)
        phone_number_service._get_credits_for_type = AsyncMock(return_value=123)
        phone_number_service.billing_service.get_credit_balance = AsyncMock(
            return_value=MagicMock(total_credits=1000)
        )
        phone_number_service.billing_service.consume_credits = AsyncMock(
            return_value=MagicMock(success=True, balance_after=877)
        )

        with patch.object(phone_number_service, "twilio_service") as mock_twilio:
            mock_twilio.is_configured.return_value = True
            mock_twilio.purchase_phone_number.return_value = MagicMock(
                sid="PN1234567890", phone_number="+15551234567"
            )
            mock_response = MagicMock()
            mock_response.data = [
                {
                    "id": str(sample_phone_number_id),
                    "organization_id": str(sample_org_id),
                    "phone_number": "+15551234567",
                    "provider": "twilio",
                    "provider_sid": "PN1234567890",
                    "phone_number_type": "local",
                    "country_code": "US",
                    "monthly_cost_credits": 123,
                    "status": "purchased",
                    "assigned_agent_id": None,
                    "is_incoming_enabled": True,
                    "is_outgoing_enabled": False,
                    "purchased_at": now.isoformat(),
                    "cancelled_at": None,
                    "created_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                }
            ]
            mock_supabase_client.table.return_value.insert.return_value.execute.return_value = (
                mock_response
            )

            result, error = await phone_number_service.purchase_number(
                sample_org_id,
                PhoneNumberPurchaseRequest(phone_number="+15551234567"),
            )

        assert error is None
        assert result is not None
        assert result.credit_balance_after == 877
        consume_request = (
            phone_number_service.billing_service.consume_credits.call_args.args[0]
        )
        assert consume_request.event_name == "phone_number_us_local_month"
        assert consume_request.metadata["cost"] == 123

    @pytest.mark.asyncio
    async def test_purchase_number_insufficient_credits(
        self, phone_number_service, sample_org_id
    ):
        """Fails purchase when organization has insufficient credits."""
        from shared.organization.phone_number_models import PhoneNumberPurchaseRequest

        mock_balance = MagicMock()
        mock_balance.total_credits = 100

        phone_number_service.billing_service.get_credit_balance = AsyncMock(
            return_value=mock_balance
        )
        phone_number_service.billing_service.consume_credits = AsyncMock(
            return_value=MagicMock(success=False, balance_after=100)
        )

        with patch.object(phone_number_service, "twilio_service") as mock_twilio:
            mock_twilio.is_configured.return_value = True

            request = PhoneNumberPurchaseRequest(
                phone_number="+15551234567",
                phone_number_type=PhoneNumberType.LOCAL,
            )

            result, error = await phone_number_service.purchase_number(
                sample_org_id, request
            )

            assert result is None
            assert error is not None
            assert "Insufficient credits" in error

    @pytest.mark.asyncio
    async def test_purchase_number_not_configured(
        self, phone_number_service, sample_org_id
    ):
        """Fails purchase when Twilio is not configured."""
        from shared.organization.phone_number_models import PhoneNumberPurchaseRequest

        with patch.object(phone_number_service, "twilio_service") as mock_twilio:
            mock_twilio.is_configured.return_value = False

            request = PhoneNumberPurchaseRequest(phone_number="+15551234567")

            result, error = await phone_number_service.purchase_number(
                sample_org_id, request
            )

            assert result is None
            from src.phone_numbers.service import PHONE_NUMBER_PURCHASE_UNAVAILABLE

            assert error == PHONE_NUMBER_PURCHASE_UNAVAILABLE


class TestPhoneNumberServiceGetOrganizationNumbers:
    """Test cases for getting organization phone numbers."""

    @pytest.mark.asyncio
    async def test_get_organization_numbers_success(
        self,
        phone_number_service,
        mock_supabase_client,
        sample_org_id,
        sample_phone_number_id,
    ):
        """Returns all phone numbers for an organization."""
        now = datetime.now(timezone.utc)

        mock_phone_response = MagicMock()
        mock_phone_response.data = [
            {
                "id": str(sample_phone_number_id),
                "organization_id": str(sample_org_id),
                "phone_number": "+15551234567",
                "provider": "twilio",
                "provider_sid": "PN1234567890",
                "phone_number_type": "local",
                "country_code": "US",
                "area_code": "555",
                "monthly_cost_credits": 200,
                "status": "purchased",
                "assigned_agent_id": None,
                "is_incoming_enabled": True,
                "is_outgoing_enabled": False,
                "purchased_at": now.isoformat(),
                "cancelled_at": None,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }
        ]

        mock_agent_response = MagicMock()
        mock_agent_response.data = []

        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.side_effect = [
            mock_phone_response,
            mock_agent_response,
        ]

        result, error = await phone_number_service.get_organization_numbers(
            sample_org_id
        )

        assert error is None
        assert len(result.items) == 1
        assert result.items[0].phone_number == "+15551234567"
        assert result.unused_count == 1

    @pytest.mark.asyncio
    async def test_get_organization_numbers_with_agent(
        self,
        phone_number_service,
        mock_supabase_client,
        sample_org_id,
        sample_phone_number_id,
        sample_agent_id,
    ):
        """Returns phone numbers with assigned agent names."""
        now = datetime.now(timezone.utc)

        mock_phone_response = MagicMock()
        mock_phone_response.data = [
            {
                "id": str(sample_phone_number_id),
                "organization_id": str(sample_org_id),
                "phone_number": "+15551234567",
                "provider": "twilio",
                "provider_sid": "PN1234567890",
                "phone_number_type": "local",
                "country_code": "US",
                "area_code": "555",
                "monthly_cost_credits": 200,
                "status": "active",
                "assigned_agent_id": str(sample_agent_id),
                "is_incoming_enabled": True,
                "is_outgoing_enabled": False,
                "purchased_at": now.isoformat(),
                "cancelled_at": None,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }
        ]

        mock_agent_response = MagicMock()
        mock_agent_response.data = [{"id": str(sample_agent_id), "name": "Test Agent"}]

        mock_supabase_client.table.side_effect = [
            MagicMock(
                select=MagicMock(
                    return_value=MagicMock(
                        eq=MagicMock(
                            return_value=MagicMock(
                                in_=MagicMock(
                                    return_value=MagicMock(
                                        execute=MagicMock(
                                            return_value=mock_phone_response
                                        )
                                    )
                                )
                            )
                        )
                    )
                )
            ),
            MagicMock(
                select=MagicMock(
                    return_value=MagicMock(
                        in_=MagicMock(
                            return_value=MagicMock(
                                execute=MagicMock(return_value=mock_agent_response)
                            )
                        )
                    )
                )
            ),
        ]

        result, error = await phone_number_service.get_organization_numbers(
            sample_org_id
        )

        assert error is None
        assert len(result.items) == 1
        assert result.items[0].agent_name == "Test Agent"
        assert result.unused_count == 0

    @pytest.mark.asyncio
    async def test_get_organization_numbers_empty(
        self, phone_number_service, mock_supabase_client, sample_org_id
    ):
        """Returns empty list when organization has no numbers."""
        mock_response = MagicMock()
        mock_response.data = []

        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value = (
            mock_response
        )

        result, error = await phone_number_service.get_organization_numbers(
            sample_org_id
        )

        assert error is None
        assert result.items == []
        assert result.total_count == 0

    @pytest.mark.asyncio
    async def test_get_agent_number_returns_only_the_current_assignment(
        self,
        phone_number_service,
        mock_supabase_client,
        sample_org_id,
        sample_agent_id,
        sample_phone_number_id,
    ):
        """The agent editor can load its current number without listing the org."""
        now = datetime.now(timezone.utc).isoformat()
        mock_supabase_client.table.return_value.execute.return_value = MagicMock(
            data=[
                {
                    "id": str(sample_phone_number_id),
                    "organization_id": str(sample_org_id),
                    "phone_number": "+15551234567",
                    "provider": "twilio",
                    "provider_sid": "PN1234567890",
                    "phone_number_type": "local",
                    "country_code": "US",
                    "area_code": "555",
                    "monthly_cost_credits": 200,
                    "status": "active",
                    "assigned_agent_id": str(sample_agent_id),
                    "is_incoming_enabled": True,
                    "is_outgoing_enabled": False,
                    "billing_status": "active",
                    "billing_mode": "platform_rental",
                    "provisioning_source": "platform",
                    "management_mode": "platform_managed",
                    "configuration_status": "configured",
                    "configuration_error": None,
                    "last_verified_at": None,
                    "next_billing_at": None,
                    "billing_grace_ends_at": None,
                    "purchased_at": now,
                    "cancelled_at": None,
                    "created_at": now,
                    "updated_at": now,
                }
            ]
        )

        result, error = await phone_number_service.get_agent_number(
            sample_org_id, sample_agent_id
        )

        assert error is None
        assert result is not None
        assert result.id == sample_phone_number_id
        assert result.assigned_agent_id == sample_agent_id
        mock_supabase_client.table.assert_called_once_with("phone_numbers")

    @pytest.mark.asyncio
    async def test_get_agent_number_returns_error_when_database_fails(
        self,
        phone_number_service,
        mock_supabase_client,
        sample_org_id,
        sample_agent_id,
    ):
        """Agent assignment failures are returned without leaking exceptions."""
        mock_supabase_client.table.side_effect = RuntimeError("database unavailable")

        result, error = await phone_number_service.get_agent_number(
            sample_org_id, sample_agent_id
        )

        assert result is None
        assert error == "Failed to fetch phone number for agent: database unavailable"

    @pytest.mark.asyncio
    async def test_get_organization_numbers_batches_agent_name_lookup(
        self,
        phone_number_service,
        mock_supabase_client,
        sample_org_id,
        sample_phone_number_id,
        sample_agent_id,
    ):
        """Listing numbers uses one agent query instead of one query per number."""
        now = datetime.now(timezone.utc).isoformat()
        number_row = {
            "id": str(sample_phone_number_id),
            "organization_id": str(sample_org_id),
            "phone_number": "+15551234567",
            "provider": "twilio",
            "provider_sid": "PN1234567890",
            "phone_number_type": "local",
            "country_code": "US",
            "area_code": "555",
            "monthly_cost_credits": 200,
            "status": "active",
            "assigned_agent_id": str(sample_agent_id),
            "is_incoming_enabled": True,
            "is_outgoing_enabled": False,
            "billing_status": "active",
            "billing_mode": "platform_rental",
            "provisioning_source": "platform",
            "management_mode": "platform_managed",
            "configuration_status": "configured",
            "configuration_error": None,
            "last_verified_at": None,
            "next_billing_at": None,
            "billing_grace_ends_at": None,
            "purchased_at": now,
            "cancelled_at": None,
            "created_at": now,
            "updated_at": now,
        }
        table = mock_supabase_client.table.return_value
        table.execute.side_effect = [
            MagicMock(data=[number_row]),
            MagicMock(data=[{"id": str(sample_agent_id), "name": "Test Agent"}]),
        ]

        result, error = await phone_number_service.get_organization_numbers(
            sample_org_id
        )

        assert error is None
        assert result.items[0].agent_name == "Test Agent"
        assert mock_supabase_client.table.call_count == 2
        mock_supabase_client.table.assert_any_call("voice_agents")


class TestPhoneNumberServiceAssignToAgent:
    """Test cases for assigning phone numbers to agents."""

    @pytest.mark.asyncio
    async def test_assign_to_agent_success(
        self,
        phone_number_service,
        mock_supabase_client,
        sample_phone_number_id,
        sample_agent_id,
    ):
        """Assigns phone number to agent successfully."""
        from shared.organization.phone_number_models import PhoneNumberAssignRequest

        now = datetime.now(timezone.utc)

        mock_select_response = MagicMock()
        mock_select_response.data = [
            {
                "id": str(sample_phone_number_id),
                "organization_id": str(uuid4()),
                "phone_number": "+15551234567",
                "provider": "twilio",
                "provider_sid": "PN1234567890",
                "phone_number_type": "local",
                "country_code": "US",
                "area_code": "555",
                "monthly_cost_credits": 200,
                "status": "purchased",
                "assigned_agent_id": None,
                "is_incoming_enabled": True,
                "is_outgoing_enabled": False,
                "purchased_at": now.isoformat(),
                "cancelled_at": None,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }
        ]

        mock_agent_response = MagicMock()
        mock_agent_response.data = [{"id": str(sample_agent_id)}]

        mock_update_response = MagicMock()
        mock_update_response.data = [
            {
                "id": str(sample_phone_number_id),
                "organization_id": str(uuid4()),
                "phone_number": "+15551234567",
                "provider": "twilio",
                "provider_sid": "PN1234567890",
                "phone_number_type": "local",
                "country_code": "US",
                "area_code": "555",
                "monthly_cost_credits": 200,
                "status": "active",
                "assigned_agent_id": str(sample_agent_id),
                "is_incoming_enabled": True,
                "is_outgoing_enabled": False,
                "purchased_at": now.isoformat(),
                "cancelled_at": None,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }
        ]

        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.side_effect = [
            mock_select_response,
            mock_agent_response,
            mock_update_response,
        ]
        mock_supabase_client.table.return_value.update.return_value.eq.return_value.execute.return_value = (
            mock_update_response
        )

        request = PhoneNumberAssignRequest(agent_id=sample_agent_id)

        result, error = await phone_number_service.assign_to_agent(
            sample_phone_number_id, request
        )

        assert error is None
        assert result is not None
        assert result.assigned_agent_id == sample_agent_id
        assert result.status == PhoneNumberStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_assign_to_agent_not_found(
        self, phone_number_service, mock_supabase_client, sample_phone_number_id
    ):
        """Returns error when phone number not found."""
        from shared.organization.phone_number_models import PhoneNumberAssignRequest

        mock_response = MagicMock()
        mock_response.data = []

        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value = (
            mock_response
        )

        request = PhoneNumberAssignRequest(agent_id=uuid4())

        result, error = await phone_number_service.assign_to_agent(
            sample_phone_number_id, request
        )

        assert result is None
        assert error == "Phone number not found"

    @pytest.mark.asyncio
    async def test_assign_to_agent_already_assigned(
        self,
        phone_number_service,
        mock_supabase_client,
        sample_phone_number_id,
    ):
        """Returns error when phone number is already assigned."""
        from shared.organization.phone_number_models import PhoneNumberAssignRequest

        now = datetime.now(timezone.utc)

        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": str(sample_phone_number_id),
                "organization_id": str(uuid4()),
                "phone_number": "+15551234567",
                "provider": "twilio",
                "provider_sid": "PN1234567890",
                "phone_number_type": "local",
                "country_code": "US",
                "area_code": "555",
                "monthly_cost_credits": 200,
                "status": "purchased",
                "assigned_agent_id": str(uuid4()),
                "is_incoming_enabled": True,
                "is_outgoing_enabled": False,
                "purchased_at": now.isoformat(),
                "cancelled_at": None,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }
        ]

        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value = (
            mock_response
        )

        request = PhoneNumberAssignRequest(agent_id=uuid4())

        result, error = await phone_number_service.assign_to_agent(
            sample_phone_number_id, request
        )

        assert result is None
        assert "already assigned" in error

    @pytest.mark.asyncio
    async def test_assign_to_agent_agent_not_found(
        self,
        phone_number_service,
        mock_supabase_client,
        sample_phone_number_id,
    ):
        """Returns error when agent not found."""
        from shared.organization.phone_number_models import PhoneNumberAssignRequest

        now = datetime.now(timezone.utc)

        mock_select_response = MagicMock()
        mock_select_response.data = [
            {
                "id": str(sample_phone_number_id),
                "organization_id": str(uuid4()),
                "phone_number": "+15551234567",
                "provider": "twilio",
                "provider_sid": "PN1234567890",
                "phone_number_type": "local",
                "country_code": "US",
                "area_code": "555",
                "monthly_cost_credits": 200,
                "status": "purchased",
                "assigned_agent_id": None,
                "is_incoming_enabled": True,
                "is_outgoing_enabled": False,
                "purchased_at": now.isoformat(),
                "cancelled_at": None,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }
        ]

        mock_agent_response = MagicMock()
        mock_agent_response.data = []

        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.side_effect = [
            mock_select_response,
            mock_agent_response,
        ]

        request = PhoneNumberAssignRequest(agent_id=uuid4())

        result, error = await phone_number_service.assign_to_agent(
            sample_phone_number_id, request
        )

        assert result is None
        assert error == "Agent not found"


class TestPhoneNumberServiceUnassign:
    """Test cases for clearing agent mappings without provider release."""

    @pytest.mark.asyncio
    async def test_unassign_platform_number_returns_to_purchased(
        self,
        phone_number_service,
        mock_supabase_client,
        sample_phone_number_id,
        sample_org_id,
        sample_agent_id,
    ):
        """Platform-owned numbers remain available after unassignment."""
        now = datetime.now(timezone.utc).isoformat()
        row = {
            "id": str(sample_phone_number_id),
            "organization_id": str(sample_org_id),
            "phone_number": "+15551234567",
            "provider": "twilio",
            "provider_sid": "PN123",
            "phone_number_type": "local",
            "country_code": "US",
            "area_code": "555",
            "monthly_cost_credits": 200,
            "status": "active",
            "assigned_agent_id": str(sample_agent_id),
            "is_incoming_enabled": True,
            "is_outgoing_enabled": False,
            "purchased_at": now,
            "cancelled_at": None,
            "created_at": now,
            "updated_at": now,
        }
        selected = MagicMock(data=[row])
        updated = MagicMock(
            data=[{**row, "status": "purchased", "assigned_agent_id": None}]
        )
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value = (
            selected
        )
        mock_supabase_client.table.return_value.update.return_value.eq.return_value.execute.return_value = (
            updated
        )

        result, error = await phone_number_service.unassign_from_agent(
            sample_phone_number_id,
            sample_org_id,
        )

        assert error is None
        assert result is not None
        assert result.status == PhoneNumberStatus.PURCHASED
        assert result.assigned_agent_id is None

    @pytest.mark.asyncio
    async def test_unassign_customer_number_stays_active_without_incoming(
        self,
        phone_number_service,
        mock_supabase_client,
        sample_phone_number_id,
        sample_org_id,
        sample_agent_id,
    ):
        """Customer-owned numbers stay connected but stop routing calls."""
        now = datetime.now(timezone.utc).isoformat()
        row = {
            "id": str(sample_phone_number_id),
            "organization_id": str(sample_org_id),
            "phone_number": "+15551234567",
            "provider": "twilio",
            "provider_sid": None,
            "phone_number_type": "local",
            "country_code": "US",
            "area_code": "555",
            "monthly_cost_credits": 0,
            "status": "active",
            "assigned_agent_id": str(sample_agent_id),
            "is_incoming_enabled": True,
            "is_outgoing_enabled": False,
            "provisioning_source": "customer",
            "management_mode": "customer_managed",
            "billing_mode": "none",
            "configuration_status": "configured",
            "purchased_at": now,
            "cancelled_at": None,
            "created_at": now,
            "updated_at": now,
        }
        selected = MagicMock(data=[row])
        updated = MagicMock(
            data=[{**row, "assigned_agent_id": None, "is_incoming_enabled": False}]
        )
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value = (
            selected
        )
        mock_supabase_client.table.return_value.update.return_value.eq.return_value.execute.return_value = (
            updated
        )

        result, error = await phone_number_service.unassign_from_agent(
            sample_phone_number_id,
            sample_org_id,
        )

        assert error is None
        assert result is not None
        assert result.status == PhoneNumberStatus.ACTIVE
        assert result.is_incoming_enabled is False

    @pytest.mark.asyncio
    async def test_unassign_returns_not_found_when_row_is_missing(
        self, phone_number_service, mock_supabase_client, sample_phone_number_id
    ):
        """A missing number is reported without attempting an update."""
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )

        result, error = await phone_number_service.unassign_from_agent(
            sample_phone_number_id
        )

        assert result is None
        assert error == "Phone number not found"

    @pytest.mark.asyncio
    async def test_unassign_rejects_terminal_number(
        self, phone_number_service, mock_supabase_client, sample_phone_number_id
    ):
        """Released numbers cannot be remapped through the assignment API."""
        now = datetime.now(timezone.utc).isoformat()
        row = {
            "id": str(sample_phone_number_id),
            "organization_id": str(uuid4()),
            "phone_number": "+15551234567",
            "provider": "twilio",
            "provider_sid": "PN123",
            "phone_number_type": "local",
            "country_code": "US",
            "area_code": "555",
            "monthly_cost_credits": 200,
            "status": "cancelled",
            "assigned_agent_id": None,
            "is_incoming_enabled": False,
            "is_outgoing_enabled": False,
            "purchased_at": now,
            "cancelled_at": now,
            "created_at": now,
            "updated_at": now,
        }
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[row]
        )

        result, error = await phone_number_service.unassign_from_agent(
            sample_phone_number_id
        )

        assert result is None
        assert "CANCELLED" in error

    @pytest.mark.asyncio
    async def test_unassign_reports_update_failure(
        self, phone_number_service, mock_supabase_client, sample_phone_number_id
    ):
        """A failed persistence response is surfaced to the caller."""
        now = datetime.now(timezone.utc).isoformat()
        row = {
            "id": str(sample_phone_number_id),
            "organization_id": str(uuid4()),
            "phone_number": "+15551234567",
            "provider": "twilio",
            "provider_sid": "PN123",
            "phone_number_type": "local",
            "country_code": "US",
            "area_code": "555",
            "monthly_cost_credits": 200,
            "status": "active",
            "assigned_agent_id": str(uuid4()),
            "is_incoming_enabled": True,
            "is_outgoing_enabled": False,
            "purchased_at": now,
            "cancelled_at": None,
            "created_at": now,
            "updated_at": now,
        }
        mock_supabase_client.table.return_value.execute.side_effect = [
            MagicMock(data=[row]),
            MagicMock(data=[]),
        ]

        result, error = await phone_number_service.unassign_from_agent(
            sample_phone_number_id
        )

        assert result is None
        assert error == "Failed to update phone number"

    @pytest.mark.asyncio
    async def test_unassign_handles_database_exception(
        self, phone_number_service, mock_supabase_client, sample_phone_number_id
    ):
        """Unexpected persistence errors become a safe service error."""
        mock_supabase_client.table.side_effect = RuntimeError("database unavailable")

        result, error = await phone_number_service.unassign_from_agent(
            sample_phone_number_id
        )

        assert result is None
        assert "Failed to unassign phone number" in error


class TestPhoneNumberServiceCancel:
    """Test cases for canceling phone numbers."""

    @pytest.mark.asyncio
    async def test_cancel_number_success(
        self,
        phone_number_service,
        mock_supabase_client,
        sample_phone_number_id,
    ):
        """Cancels phone number successfully.

        Patches ``phone_number_service.twilio_service`` so the Twilio
        release call is deterministic — the service binds the Twilio
        client in ``__init__`` (``self.twilio_service = twilio_service``),
        so the module-level ``mock_twilio_service`` fixture does NOT reach
        the instance. Without this patch the test hits the real Twilio
        API and fails with HTTP 401 when no credentials are configured.
        """
        now = datetime.now(timezone.utc)

        # Create response data
        select_data = [
            {
                "id": str(sample_phone_number_id),
                "organization_id": str(uuid4()),
                "phone_number": "+15551234567",
                "provider": "twilio",
                "provider_sid": "PN1234567890",
                "phone_number_type": "local",
                "country_code": "US",
                "area_code": "555",
                "monthly_cost_credits": 200,
                "status": "purchased",
                "assigned_agent_id": None,
                "is_incoming_enabled": True,
                "is_outgoing_enabled": False,
                "purchased_at": now.isoformat(),
                "cancelled_at": None,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }
        ]

        update_data = [
            {
                "id": str(sample_phone_number_id),
                "organization_id": str(uuid4()),
                "phone_number": "+15551234567",
                "provider": "twilio",
                "provider_sid": "PN1234567890",
                "phone_number_type": "local",
                "country_code": "US",
                "area_code": "555",
                "monthly_cost_credits": 200,
                "status": "cancelled",
                "assigned_agent_id": None,
                "is_incoming_enabled": True,
                "is_outgoing_enabled": False,
                "purchased_at": now.isoformat(),
                "cancelled_at": now.isoformat(),
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }
        ]

        # Use side_effect to directly return data - this bypasses the mock chain issue
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.side_effect = [
            MagicMock(data=select_data),
            MagicMock(data=update_data),
        ]

        with patch.object(phone_number_service, "twilio_service") as mock_twilio:
            mock_twilio.is_configured.return_value = True
            mock_twilio.release_phone_number.return_value = True

            result, error = await phone_number_service.cancel_number(
                sample_phone_number_id
            )

            # The Twilio release was attempted for a purchased number with a sid.
            mock_twilio.release_phone_number.assert_called_once_with("PN1234567890")

        assert error is None
        assert result is True

    @pytest.mark.asyncio
    async def test_cancel_number_not_found(
        self, phone_number_service, mock_supabase_client, sample_phone_number_id
    ):
        """Returns error when phone number not found."""
        # Create a mock with empty data
        mock_response = MagicMock()
        mock_response.data = []

        # Set the return value on the execute mock
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value = (
            mock_response
        )

        result, error = await phone_number_service.cancel_number(sample_phone_number_id)

        assert result is False
        assert error == "Phone number not found"

    @pytest.mark.asyncio
    async def test_cancel_number_already_cancelled(
        self,
        phone_number_service,
        mock_supabase_client,
        sample_phone_number_id,
    ):
        """Returns error when phone number is already cancelled."""
        now = datetime.now(timezone.utc)

        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": str(sample_phone_number_id),
                "organization_id": str(uuid4()),
                "phone_number": "+15551234567",
                "provider": "twilio",
                "provider_sid": "PN1234567890",
                "phone_number_type": "local",
                "country_code": "US",
                "area_code": "555",
                "monthly_cost_credits": 200,
                "status": "cancelled",
                "assigned_agent_id": None,
                "is_incoming_enabled": True,
                "is_outgoing_enabled": False,
                "purchased_at": now.isoformat(),
                "cancelled_at": now.isoformat(),
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }
        ]

        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value = (
            mock_response
        )

        result, error = await phone_number_service.cancel_number(sample_phone_number_id)

        assert result is False
        assert "already cancelled" in error


class TestPhoneNumberServiceGetCreditsForType:
    """Test cases for credit cost calculation."""

    @pytest.mark.asyncio
    async def test_credits_for_local_number(self, phone_number_service):
        """Returns correct credits for local number."""
        result = await phone_number_service._get_credits_for_type(PhoneNumberType.LOCAL)
        assert result == 80

    @pytest.mark.asyncio
    async def test_legacy_non_us_local_rate_is_preserved(self, phone_number_service):
        """Existing non-US local rentals retain their 200-credit rate."""
        result = await phone_number_service._get_credits_for_type(
            PhoneNumberType.LOCAL, "CA"
        )
        assert result == 200

    @pytest.mark.asyncio
    async def test_platform_number_search_rejects_non_us_country(
        self, phone_number_service
    ):
        """The v1 platform inventory exposes US numbers only."""
        from shared.organization.phone_number_models import PhoneNumberSearchRequest

        with patch.object(phone_number_service, "twilio_service") as twilio:
            response, error = await phone_number_service.search_available(
                PhoneNumberSearchRequest(country_code="CA")
            )

        assert response.items == []
        assert "Only US platform-provided" in error
        twilio.search_available_numbers.assert_not_called()

    @pytest.mark.asyncio
    async def test_platform_number_search_rejects_mobile_in_v1(
        self, phone_number_service
    ):
        """Search does not expose an unpriced mobile rental type in v1."""
        from shared.organization.phone_number_models import PhoneNumberSearchRequest

        with patch.object(phone_number_service, "twilio_service") as twilio:
            response, error = await phone_number_service.search_available(
                PhoneNumberSearchRequest(phone_number_type=PhoneNumberType.MOBILE)
            )

        assert response.items == []
        assert "Mobile phone numbers are not available" in error
        twilio.search_available_numbers.assert_not_called()

    @pytest.mark.asyncio
    async def test_platform_number_purchase_rejects_non_us_country(
        self, phone_number_service, sample_org_id
    ):
        """The API cannot bypass the US-only number market with a direct call."""
        from shared.organization.phone_number_models import PhoneNumberPurchaseRequest

        phone_number_service.billing_service.consume_credits = AsyncMock()
        with patch.object(phone_number_service, "twilio_service") as twilio:
            result, error = await phone_number_service.purchase_number(
                sample_org_id,
                PhoneNumberPurchaseRequest(
                    phone_number="+14155551234", country_code="CA"
                ),
            )

        assert result is None
        assert "Only US platform-provided" in error
        twilio.is_configured.assert_not_called()
        phone_number_service.billing_service.consume_credits.assert_not_called()

    @pytest.mark.asyncio
    async def test_platform_number_purchase_rejects_mobile_in_v1(
        self, phone_number_service, sample_org_id
    ):
        """A direct request cannot bypass the mobile-number launch restriction."""
        from shared.organization.phone_number_models import PhoneNumberPurchaseRequest

        with patch.object(phone_number_service, "twilio_service") as twilio:
            result, error = await phone_number_service.purchase_number(
                sample_org_id,
                PhoneNumberPurchaseRequest(
                    phone_number="+15551234567",
                    phone_number_type=PhoneNumberType.MOBILE,
                ),
            )

        assert result is None
        assert "Mobile phone numbers are not available" in error
        twilio.is_configured.assert_not_called()
        phone_number_service.billing_service.consume_credits.assert_not_called()

    @pytest.mark.asyncio
    async def test_credits_for_toll_free_number(self, phone_number_service):
        """Returns correct credits for toll-free number."""
        result = await phone_number_service._get_credits_for_type(
            PhoneNumberType.TOLL_FREE
        )
        assert result == 120

    @pytest.mark.asyncio
    async def test_credits_for_mobile_number(self, phone_number_service):
        """Returns correct credits for mobile number."""
        result = await phone_number_service._get_credits_for_type(
            PhoneNumberType.MOBILE
        )
        assert result == 200

    @pytest.mark.asyncio
    async def test_credits_for_unknown_type(self, phone_number_service):
        """Rejects an unknown phone-number type instead of guessing a price."""
        with pytest.raises(KeyError):
            await phone_number_service._get_credits_for_type(None)


class TestPhoneNumberRentalBilling:
    """Tests for recurring monthly phone-number rental enforcement."""

    @pytest.mark.asyncio
    async def test_included_us_local_line_never_debits_and_recovers_past_due_state(
        self,
        phone_number_service,
        mock_supabase_client,
        sample_purchased_phone_number,
    ):
        """Included rentals stay active without credits, even after old arrears."""
        now = datetime.now(timezone.utc)
        row = {
            **sample_purchased_phone_number,
            "is_included_in_plan": True,
            "monthly_cost_credits": 0,
            "next_billing_at": (now - timedelta(days=1)).isoformat(),
            "billing_status": "past_due",
            "billing_grace_ends_at": (now - timedelta(days=1)).isoformat(),
        }
        table = MagicMock()
        mock_supabase_client.table.return_value = table
        table.select.return_value.in_.return_value.execute.return_value = MagicMock(
            data=[row]
        )
        phone_number_service.billing_service.consume_credits = AsyncMock()

        result = await phone_number_service.process_due_rentals(now=now)

        assert result.processed == 1
        assert result.charged == 0
        assert result.released == 0
        phone_number_service.billing_service.consume_credits.assert_not_called()
        update = table.update.call_args.args[0]
        assert update["monthly_cost_credits"] == 0
        assert update["billing_status"] == "active"
        assert update["billing_grace_ends_at"] is None

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("entitled", "plan_slug", "cancel_at_period_end", "access_days", "charged"),
        [
            (True, "starter", False, None, False),
            (True, "growth", True, 1, False),
            (True, "growth", True, -1, True),
            (True, "growth", True, None, True),
            (False, "free", False, None, True),
            (True, "free", False, None, True),
        ],
    )
    async def test_included_number_converts_to_paid_rental_after_plan_access_ends(
        self,
        phone_number_service,
        mock_supabase_client,
        sample_purchased_phone_number,
        entitled,
        plan_slug,
        cancel_at_period_end,
        access_days,
        charged,
        caplog,
    ):
        """The included line stays free only while its paid-plan access applies."""
        now = datetime.now(timezone.utc)
        access_until = (
            (now + timedelta(days=access_days)).isoformat()
            if access_days is not None
            else None
        )
        phone_number_service.entitlement_service.get_org_entitlements = AsyncMock(
            return_value=MagicMock(
                is_entitled=entitled,
                plan_product_slug=plan_slug,
                cancel_at_period_end=cancel_at_period_end,
                access_until=access_until,
            )
        )
        phone_number_service._get_credits_for_type = AsyncMock(return_value=80)
        phone_number_service.billing_service.consume_credits = AsyncMock(
            return_value=MagicMock(success=True, balance_after=920)
        )
        row = {
            **sample_purchased_phone_number,
            "is_included_in_plan": True,
            "monthly_cost_credits": 0,
            "billing_status": "active",
            "next_billing_at": (now - timedelta(days=1)).isoformat(),
        }
        table = mock_supabase_client.table.return_value
        table.select.return_value.in_.return_value.execute.return_value = MagicMock(
            data=[row]
        )

        result = await phone_number_service.process_due_rentals(now=now)

        assert result.charged == int(charged)
        if charged:
            phone_number_service.billing_service.consume_credits.assert_awaited_once()
            update = table.update.call_args.args[0]
            assert update["is_included_in_plan"] is False
            assert update["monthly_cost_credits"] == 80
        else:
            phone_number_service.billing_service.consume_credits.assert_not_awaited()
            update = table.update.call_args.args[0]
            assert update["monthly_cost_credits"] == 0
        if cancel_at_period_end and access_until is None:
            assert "missing access_until" in caplog.text

    @pytest.mark.asyncio
    async def test_paid_plan_reactivation_restores_allowance_to_oldest_local_line(
        self,
        phone_number_service,
        mock_supabase_client,
        sample_purchased_phone_number,
        sample_phone_number_id,
        sample_org_id,
    ):
        """A returning paid plan gets its included line without a rental debit."""
        now = datetime.now(timezone.utc)
        row = {
            **sample_purchased_phone_number,
            "id": str(sample_phone_number_id),
            "organization_id": str(sample_org_id),
            "phone_number_type": "local",
            "country_code": "US",
            "management_mode": "platform_managed",
            "billing_mode": "platform_rental",
            "is_included_in_plan": False,
            "status": "purchased",
            "next_billing_at": (now - timedelta(days=1)).isoformat(),
        }
        candidate = {
            "id": str(sample_phone_number_id),
            "assigned_agent_id": None,
            "configuration_status": "configured",
        }
        table = mock_supabase_client.table.return_value
        table.execute.side_effect = [
            MagicMock(data=[row]),
            MagicMock(data=[]),
            MagicMock(data=[candidate]),
            MagicMock(data=[candidate]),
        ]
        phone_number_service._has_active_paid_plan_allowance = AsyncMock(
            return_value=True
        )
        phone_number_service.billing_service.consume_credits = AsyncMock()

        with patch(
            "src.phone_numbers.service.platform_phone_number_settings_service"
        ) as settings_service:
            settings_service.get_settings = AsyncMock(
                return_value=MagicMock(billing_grace_period_days=7)
            )
            result = await phone_number_service.process_due_rentals(now=now)

        assert result.charged == 0
        assert result.processed == 1
        phone_number_service.billing_service.consume_credits.assert_not_awaited()
        update = table.update.call_args.args[0]
        assert update["is_included_in_plan"] is True
        assert update["monthly_cost_credits"] == 0

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("country_code", "expected_event"),
        [
            ("US", "phone_number_us_local_month"),
            ("CA", "phone_number_local_month"),
        ],
    )
    async def test_process_due_rentals_charges_current_system_rate(
        self,
        phone_number_service,
        mock_supabase_client,
        sample_purchased_phone_number,
        country_code,
        expected_event,
    ):
        """A due number is charged using the current configured monthly rate."""
        due_at = datetime.now(timezone.utc) - timedelta(days=1)
        row = {
            **sample_purchased_phone_number,
            "country_code": country_code,
            "next_billing_at": due_at.isoformat(),
            "billing_status": "active",
        }
        table = MagicMock()
        mock_supabase_client.table.return_value = table
        table.select.return_value.in_.return_value.execute.return_value = MagicMock(
            data=[row]
        )
        phone_number_service._get_credits_for_type = AsyncMock(return_value=321)
        phone_number_service.billing_service.consume_credits = AsyncMock(
            return_value=MagicMock(success=True, balance_after=679)
        )

        result = await phone_number_service.process_due_rentals()

        assert result.charged == 1
        consume_request = (
            phone_number_service.billing_service.consume_credits.call_args.args[0]
        )
        assert consume_request.event_name == expected_event
        assert consume_request.metadata["cost"] == 321
        assert consume_request.idempotency_key.startswith("phone-rental:")
        update_data = table.update.call_args.args[0]
        assert update_data["monthly_cost_credits"] == 321
        assert update_data["billing_status"] == "active"

    @pytest.mark.asyncio
    async def test_process_due_rentals_enters_grace_when_balance_is_insufficient(
        self,
        phone_number_service,
        mock_supabase_client,
        sample_purchased_phone_number,
    ):
        """A failed renewal keeps the Twilio number during the grace window."""
        due_at = datetime.now(timezone.utc) - timedelta(days=1)
        row = {
            **sample_purchased_phone_number,
            "next_billing_at": due_at.isoformat(),
            "billing_status": "active",
        }
        table = MagicMock()
        mock_supabase_client.table.return_value = table
        table.select.return_value.in_.return_value.execute.return_value = MagicMock(
            data=[row]
        )
        phone_number_service._get_credits_for_type = AsyncMock(return_value=321)
        phone_number_service.billing_service.consume_credits = AsyncMock(
            return_value=MagicMock(success=False, balance_after=0)
        )

        result = await phone_number_service.process_due_rentals()

        assert result.past_due == 1
        update_data = table.update.call_args.args[0]
        assert update_data["billing_status"] == "past_due"
        assert update_data["billing_grace_ends_at"] is not None
        assert update_data["is_incoming_enabled"] is False

    @pytest.mark.asyncio
    async def test_process_due_rentals_skips_customer_owned_numbers(
        self,
        phone_number_service,
        mock_supabase_client,
        sample_purchased_phone_number,
    ):
        """Customer-owned numbers are not charged or released by rental billing."""
        row = {
            **sample_purchased_phone_number,
            "billing_mode": "none",
            "management_mode": "customer_managed",
            "provisioning_source": "customer",
            "status": "active",
            "next_billing_at": (
                datetime.now(timezone.utc) - timedelta(days=2)
            ).isoformat(),
        }
        table = MagicMock()
        mock_supabase_client.table.return_value = table
        table.select.return_value.in_.return_value.execute.return_value = MagicMock(
            data=[row]
        )
        phone_number_service.billing_service.consume_credits = AsyncMock()

        result = await phone_number_service.process_due_rentals()

        assert result.processed == 0
        phone_number_service.billing_service.consume_credits.assert_not_called()
        table.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_due_rentals_retries_release_pending_rows(
        self,
        phone_number_service,
        mock_supabase_client,
        sample_purchased_phone_number,
    ):
        """A daily run retries an orphaned provider release."""
        row = {
            **sample_purchased_phone_number,
            "status": "release_pending",
            "billing_mode": "platform_rental",
        }
        table = MagicMock()
        mock_supabase_client.table.return_value = table
        table.select.return_value.in_.return_value.execute.return_value = MagicMock(
            data=[row]
        )
        phone_number_service.twilio_service.release_phone_number = MagicMock(
            return_value=True
        )
        table.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[row]
        )

        result = await phone_number_service.process_due_rentals()

        assert result.released == 1
        phone_number_service.twilio_service.release_phone_number.assert_called_once_with(
            "PN1234567890"
        )
        assert table.update.call_args.args[0]["status"] == "cancelled"


class TestPhoneNumberServiceEdgeCases:
    """Cover service error and no-op paths that protect lifecycle boundaries."""

    @pytest.mark.asyncio
    async def test_get_routable_agent_id_rejects_unassigned_number(
        self, phone_number_service, mock_supabase_client
    ):
        """An enabled number without an assignment must not route a call."""
        mock_supabase_client.table.return_value.execute.return_value = MagicMock(
            data=[]
        )

        agent_id, error = await phone_number_service.get_routable_agent_id(
            "+15551234567"
        )

        assert agent_id is None
        assert error == "Phone number is not assigned or enabled"

    @pytest.mark.asyncio
    async def test_get_by_id_returns_not_found(
        self, phone_number_service, mock_supabase_client, sample_phone_number_id
    ):
        """Missing records return a stable not-found error."""
        mock_supabase_client.table.return_value.execute.return_value = MagicMock(
            data=[]
        )

        number, error = await phone_number_service.get_by_id(sample_phone_number_id)

        assert number is None
        assert error == "Phone number not found"

    @pytest.mark.asyncio
    async def test_get_by_id_sanitizes_database_exception(
        self, phone_number_service, mock_supabase_client, sample_phone_number_id
    ):
        """Database failures are returned rather than escaping the service."""
        mock_supabase_client.table.return_value.execute.side_effect = RuntimeError(
            "database unavailable"
        )

        number, error = await phone_number_service.get_by_id(sample_phone_number_id)

        assert number is None
        assert "Failed to fetch phone number" in error

    @pytest.mark.asyncio
    async def test_get_agent_number_returns_none_when_unassigned(
        self, phone_number_service, mock_supabase_client, sample_org_id, sample_agent_id
    ):
        """Agent detail loading treats an absent assignment as an empty value."""
        mock_supabase_client.table.return_value.execute.return_value = MagicMock(
            data=[]
        )

        number, error = await phone_number_service.get_agent_number(
            sample_org_id, sample_agent_id
        )

        assert number is None
        assert error is None

    @pytest.mark.asyncio
    async def test_get_organization_numbers_returns_error_on_database_failure(
        self, phone_number_service, mock_supabase_client, sample_org_id
    ):
        """Organization listing failures produce an empty safe response."""
        mock_supabase_client.table.return_value.execute.side_effect = RuntimeError(
            "database unavailable"
        )

        response, error = await phone_number_service.get_organization_numbers(
            sample_org_id
        )

        assert response.items == []
        assert response.total_count == 0
        assert "Failed to fetch phone numbers" in error

    @pytest.mark.asyncio
    async def test_phone_number_limit_error_returns_entitlement_message(
        self, phone_number_service, sample_org_id
    ):
        """Provider purchases stop when the plan entitlement is exhausted."""
        from src.billing.entitlement_models import EntitlementDenied

        phone_number_service.entitlement_service.assert_limit.side_effect = (
            EntitlementDenied("max_phone_numbers", "Phone-number limit reached")
        )

        error = await phone_number_service._phone_number_limit_error(sample_org_id)

        assert error == "Phone-number limit reached"

    @pytest.mark.asyncio
    async def test_refund_failed_purchase_swallows_refund_exception(
        self, phone_number_service, sample_org_id
    ):
        """A refund failure is logged without masking the original purchase error."""
        phone_number_service.billing_service.refund_credits = AsyncMock(
            side_effect=RuntimeError("billing unavailable")
        )

        await phone_number_service._refund_failed_purchase(
            sample_org_id, 200, "+15551234567", "purchase-idempotency-key"
        )

        phone_number_service.billing_service.refund_credits.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_import_number_rejects_agent_outside_organization(
        self, phone_number_service, mock_supabase_client, sample_org_id, sample_agent_id
    ):
        """Customer numbers cannot be assigned across organization boundaries."""
        from shared.organization.phone_number_models import PhoneNumberImportRequest

        mock_supabase_client.table.return_value.execute.return_value = MagicMock(
            data=[]
        )

        result, error = await phone_number_service.import_number(
            sample_org_id,
            PhoneNumberImportRequest(
                phone_number="+15551234567", agent_id=sample_agent_id
            ),
        )

        assert result is None
        assert error == "Agent not found in this organization"


def test_add_month_handles_year_boundary_and_short_months():
    """Rental billing advances calendar months without invalid dates."""
    from src.phone_numbers.service import _add_month

    assert (
        _add_month(datetime(2026, 1, 31, tzinfo=timezone.utc)).date()
        == datetime(2026, 2, 28, tzinfo=timezone.utc).date()
    )
    assert (
        _add_month(datetime(2026, 12, 31, tzinfo=timezone.utc)).date()
        == datetime(2027, 1, 31, tzinfo=timezone.utc).date()
    )


class TestPhoneNumberServiceLifecycleBranches:
    """Exercise idempotency, verification, and transactional failure paths."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("status", "expected_error"),
        [
            ("provisioning", "already provisioning"),
            ("release_pending", "awaiting provider release"),
        ],
    )
    async def test_purchase_idempotency_rejects_nonterminal_attempts(
        self,
        phone_number_service,
        mock_supabase_client,
        sample_org_id,
        sample_purchased_phone_number,
        status,
        expected_error,
    ):
        """Retries cannot start a second provider operation for an active attempt."""
        from shared.organization.phone_number_models import PhoneNumberPurchaseRequest

        row = {
            **sample_purchased_phone_number,
            "status": status,
            "provisioning_idempotency_key": "same-attempt",
        }
        mock_supabase_client.table.return_value.execute.return_value = MagicMock(
            data=[row]
        )

        with patch.object(phone_number_service, "twilio_service") as twilio:
            twilio.is_configured.return_value = True
            result, error = await phone_number_service.purchase_number(
                sample_org_id,
                PhoneNumberPurchaseRequest(phone_number="+15551234567"),
                idempotency_key="same-attempt",
            )

        assert result is None
        assert expected_error in error
        phone_number_service.billing_service.consume_credits.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("status", ["cancelled", "disconnected"])
    async def test_purchase_idempotency_rejects_terminal_attempts(
        self,
        phone_number_service,
        mock_supabase_client,
        sample_org_id,
        sample_purchased_phone_number,
        status,
    ):
        """Terminal attempts require a new key so refunded debits cannot replay."""
        from shared.organization.phone_number_models import PhoneNumberPurchaseRequest

        row = {
            **sample_purchased_phone_number,
            "status": status,
            "provisioning_idempotency_key": "terminal-attempt",
        }
        mock_supabase_client.table.return_value.execute.return_value = MagicMock(
            data=[row]
        )

        with patch.object(phone_number_service, "twilio_service") as twilio:
            twilio.is_configured.return_value = True
            result, error = await phone_number_service.purchase_number(
                sample_org_id,
                PhoneNumberPurchaseRequest(phone_number="+15551234567"),
                idempotency_key="terminal-attempt",
            )

        assert result is None
        assert error == (
            "This purchase attempt has ended. Start a new purchase with a fresh idempotency key."
        )
        phone_number_service.billing_service.consume_credits.assert_not_called()
        twilio.purchase_phone_number.assert_not_called()

    @pytest.mark.asyncio
    async def test_retry_after_failed_row_save_uses_a_fresh_ledger_key(
        self,
        phone_number_service,
        mock_supabase_client,
        sample_org_id,
        sample_phone_number_id,
        sample_purchased_phone_number,
    ):
        """A refunded debit key is not replayed as a free number on retry."""
        from shared.organization.phone_number_models import PhoneNumberPurchaseRequest

        phone_number_service._phone_number_limit_error = AsyncMock(return_value=None)
        phone_number_service._has_active_included_us_local_number = AsyncMock(
            return_value=True
        )
        phone_number_service._get_credits_for_type = AsyncMock(return_value=80)
        phone_number_service.billing_service.consume_credits = AsyncMock(
            side_effect=[
                MagicMock(success=True, balance_after=920),
                MagicMock(success=True, balance_after=840),
            ]
        )
        phone_number_service.billing_service.refund_credits = AsyncMock()

        table = mock_supabase_client.table.return_value
        purchased_row = {
            **sample_purchased_phone_number,
            "id": str(sample_phone_number_id),
            "organization_id": str(sample_org_id),
            "status": "purchased",
            "phone_number": "+15551234567",
            "monthly_cost_credits": 80,
            "provisioning_idempotency_key": "client-key",
        }
        table.execute.side_effect = [
            MagicMock(data=[]),
            MagicMock(data=[]),
            MagicMock(data=[]),
            MagicMock(data=[{"id": str(sample_phone_number_id)}]),
            MagicMock(data=[purchased_row]),
        ]

        request = PhoneNumberPurchaseRequest(phone_number="+15551234567")
        with patch.object(phone_number_service, "twilio_service") as twilio:
            twilio.is_configured.return_value = True
            twilio.purchase_phone_number.return_value = MagicMock(sid="PN1234567890")

            failed_result, failed_error = await phone_number_service.purchase_number(
                sample_org_id, request, idempotency_key="client-key"
            )
            retry_result, retry_error = await phone_number_service.purchase_number(
                sample_org_id, request, idempotency_key="client-key"
            )

        assert failed_result is None
        assert failed_error == "Failed to save phone number provisioning record"
        assert retry_error is None
        assert retry_result is not None
        debit_keys = [
            call.args[0].idempotency_key
            for call in phone_number_service.billing_service.consume_credits.call_args_list
        ]
        assert len(set(debit_keys)) == 2
        assert all(key != "client-key" for key in debit_keys)
        assert phone_number_service.billing_service.refund_credits.await_args.kwargs[
            "idempotency_key"
        ].endswith(debit_keys[0])
        twilio.purchase_phone_number.assert_called_once()

    @pytest.mark.asyncio
    async def test_purchase_idempotency_replays_completed_attempt_with_balance(
        self,
        phone_number_service,
        mock_supabase_client,
        sample_org_id,
        sample_purchased_phone_number,
    ):
        """A completed retry returns the local record without another charge."""
        from shared.organization.phone_number_models import PhoneNumberPurchaseRequest

        row = {
            **sample_purchased_phone_number,
            "status": "purchased",
            "provisioning_idempotency_key": "completed-attempt",
        }
        mock_supabase_client.table.return_value.execute.return_value = MagicMock(
            data=[row]
        )
        phone_number_service.billing_service.get_credit_balance = AsyncMock(
            return_value=MagicMock(total_credits=321)
        )

        with patch.object(phone_number_service, "twilio_service") as twilio:
            twilio.is_configured.return_value = True
            result, error = await phone_number_service.purchase_number(
                sample_org_id,
                PhoneNumberPurchaseRequest(phone_number="+15551234567"),
                idempotency_key="completed-attempt",
            )

        assert error is None
        assert result.success is True
        assert result.credit_balance_after == 321
        phone_number_service.billing_service.consume_credits.assert_not_called()

    @pytest.mark.asyncio
    async def test_purchase_idempotency_key_cannot_be_reused_for_another_number(
        self,
        phone_number_service,
        mock_supabase_client,
        sample_org_id,
        sample_purchased_phone_number,
    ):
        """A retry key is bound to the original normalized number and type."""
        from shared.organization.phone_number_models import PhoneNumberPurchaseRequest

        row = {
            **sample_purchased_phone_number,
            "provisioning_idempotency_key": "reused-key",
        }
        mock_supabase_client.table.return_value.execute.return_value = MagicMock(
            data=[row]
        )

        with patch.object(phone_number_service, "twilio_service") as twilio:
            twilio.is_configured.return_value = True
            result, error = await phone_number_service.purchase_number(
                sample_org_id,
                PhoneNumberPurchaseRequest(phone_number="+15551230000"),
                idempotency_key="reused-key",
            )

        assert result is None
        assert error == "This idempotency key was already used for another number"

    @pytest.mark.asyncio
    async def test_purchase_returns_entitlement_error_before_charging(
        self, phone_number_service, sample_org_id
    ):
        """Plan limits are enforced before the credit debit or provider call."""
        from src.billing.entitlement_models import EntitlementDenied

        from shared.organization.phone_number_models import PhoneNumberPurchaseRequest

        phone_number_service.entitlement_service.assert_limit.side_effect = (
            EntitlementDenied("max_phone_numbers", "No phone number capacity")
        )

        with patch.object(phone_number_service, "twilio_service") as twilio:
            twilio.is_configured.return_value = True
            result, error = await phone_number_service.purchase_number(
                sample_org_id,
                PhoneNumberPurchaseRequest(phone_number="+15551234567"),
            )

        assert result is None
        assert error == "No phone number capacity"
        phone_number_service.billing_service.consume_credits.assert_not_called()

    @pytest.mark.asyncio
    async def test_purchase_refunds_when_pending_record_cannot_be_saved(
        self, phone_number_service, mock_supabase_client, sample_org_id
    ):
        """A failed local reservation refunds the debit before returning."""
        from shared.organization.phone_number_models import PhoneNumberPurchaseRequest

        phone_number_service._get_credits_for_type = AsyncMock(return_value=200)
        phone_number_service.billing_service.consume_credits = AsyncMock(
            return_value=MagicMock(success=True, balance_after=0)
        )
        phone_number_service.billing_service.refund_credits = AsyncMock()
        mock_supabase_client.table.return_value.execute.return_value = MagicMock(
            data=[]
        )

        with patch.object(phone_number_service, "twilio_service") as twilio:
            twilio.is_configured.return_value = True
            result, error = await phone_number_service.purchase_number(
                sample_org_id,
                PhoneNumberPurchaseRequest(phone_number="+15551234567"),
            )

        assert result is None
        assert error == "Failed to save phone number provisioning record"
        phone_number_service.billing_service.refund_credits.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_import_returns_save_error_when_insert_is_empty(
        self, phone_number_service, mock_supabase_client, sample_org_id
    ):
        """Customer-number setup fails cleanly when its local row is not written."""
        from shared.organization.phone_number_models import PhoneNumberImportRequest

        mock_supabase_client.table.return_value.execute.return_value = MagicMock(
            data=[]
        )

        result, error = await phone_number_service.import_number(
            sample_org_id,
            PhoneNumberImportRequest(phone_number="+15551234567"),
        )

        assert result is None
        assert error == "Failed to save customer phone number"

    @pytest.mark.asyncio
    async def test_import_returns_validation_detail_for_invalid_number(
        self, phone_number_service, sample_org_id
    ):
        """Invalid customer numbers return the validation detail to the caller."""
        from shared.organization.phone_number_models import PhoneNumberImportRequest

        result, error = await phone_number_service.import_number(
            sample_org_id,
            PhoneNumberImportRequest(phone_number="not-a-phone-number"),
        )

        assert result is None
        assert (
            error == "Phone number must be a valid E.164 number or a 10-digit US number"
        )

    @pytest.mark.asyncio
    async def test_verification_details_return_not_found(
        self,
        phone_number_service,
        mock_supabase_client,
        sample_org_id,
        sample_phone_number_id,
    ):
        """Verification details are scoped to an existing organization row."""
        mock_supabase_client.table.return_value.execute.return_value = MagicMock(
            data=[]
        )

        result, error = await phone_number_service.get_verification_details(
            sample_org_id, sample_phone_number_id
        )

        assert result is None
        assert error == "Phone number not found"

    @pytest.mark.asyncio
    async def test_verification_details_report_failed_token_replacement(
        self,
        phone_number_service,
        mock_supabase_client,
        sample_org_id,
        sample_phone_number_id,
    ):
        """Legacy pending rows fail safely when token persistence is unavailable."""
        row = {
            "id": str(sample_phone_number_id),
            "phone_number": "+15551234567",
            "status": "verification_required",
            "provisioning_source": "customer",
            "management_mode": "customer_managed",
            "connection_token_encrypted": None,
        }
        table = mock_supabase_client.table.return_value
        table.execute.side_effect = [MagicMock(data=[row]), MagicMock(data=[])]

        result, error = await phone_number_service.get_verification_details(
            sample_org_id, sample_phone_number_id
        )

        assert result is None
        assert error == "Verification details are no longer available"

    @pytest.mark.asyncio
    async def test_verify_customer_number_returns_false_for_unknown_token(
        self, phone_number_service, mock_supabase_client
    ):
        """A missing or incorrect token cannot activate a customer number."""
        mock_supabase_client.table.return_value.execute.return_value = MagicMock(
            data=[]
        )

        verified = await phone_number_service.verify_customer_number(
            "+15551234567", "wrong-token"
        )

        assert verified is False

    @pytest.mark.asyncio
    async def test_verify_customer_number_enables_incoming_calls(
        self, phone_number_service, mock_supabase_client, sample_phone_number_id
    ):
        """A valid customer token activates routing and retires the token."""
        table = mock_supabase_client.table.return_value
        table.execute.side_effect = [
            MagicMock(data=[{"id": str(sample_phone_number_id)}]),
            MagicMock(data=[{"id": str(sample_phone_number_id)}]),
        ]

        verified = await phone_number_service.verify_customer_number(
            "+15551234567", "correct-token"
        )

        assert verified is True
        update_payload = table.update.call_args.args[0]
        assert update_payload["status"] == "active"
        assert update_payload["is_incoming_enabled"] is True
        assert update_payload["connection_token_encrypted"] is None


class TestPhoneNumberServiceFailureCompensation:
    """Verify compensation and persistence behavior when lifecycle steps fail."""

    @pytest.mark.asyncio
    async def test_purchase_releases_provider_number_after_finalize_failure(
        self,
        phone_number_service,
        mock_supabase_client,
        sample_org_id,
        sample_phone_number_id,
    ):
        """A failed final write releases the just-purchased provider asset."""
        from shared.organization.phone_number_models import PhoneNumberPurchaseRequest

        phone_number_service._get_credits_for_type = AsyncMock(return_value=200)
        phone_number_service.billing_service.consume_credits = AsyncMock(
            return_value=MagicMock(success=True, balance_after=0)
        )
        phone_number_service.billing_service.refund_credits = AsyncMock()
        table = mock_supabase_client.table.return_value
        table.execute.side_effect = [
            MagicMock(data=[{"id": str(sample_phone_number_id)}]),
            MagicMock(data=[]),
            MagicMock(data=[{"id": str(sample_phone_number_id)}]),
        ]

        with patch.object(phone_number_service, "twilio_service") as twilio:
            twilio.is_configured.return_value = True
            twilio.purchase_phone_number.return_value = MagicMock(
                sid="PN-compensate", phone_number="+15551234567"
            )
            twilio.release_phone_number.return_value = True
            result, error = await phone_number_service.purchase_number(
                sample_org_id,
                PhoneNumberPurchaseRequest(phone_number="+15551234567"),
            )

        assert result is None
        from src.phone_numbers.service import PHONE_NUMBER_PURCHASE_UNAVAILABLE

        assert error == PHONE_NUMBER_PURCHASE_UNAVAILABLE
        twilio.release_phone_number.assert_called_once_with("PN-compensate")
        phone_number_service.billing_service.refund_credits.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_purchase_marks_release_pending_when_compensation_fails(
        self,
        phone_number_service,
        mock_supabase_client,
        sample_org_id,
        sample_phone_number_id,
    ):
        """A provider release failure is persisted for the daily retry worker."""
        from shared.organization.phone_number_models import PhoneNumberPurchaseRequest

        phone_number_service._get_credits_for_type = AsyncMock(return_value=200)
        phone_number_service.billing_service.consume_credits = AsyncMock(
            return_value=MagicMock(success=True, balance_after=0)
        )
        phone_number_service.billing_service.refund_credits = AsyncMock()
        table = mock_supabase_client.table.return_value
        table.execute.side_effect = [
            MagicMock(data=[{"id": str(sample_phone_number_id)}]),
            MagicMock(data=[]),
            MagicMock(data=[{"id": str(sample_phone_number_id)}]),
        ]

        with patch.object(phone_number_service, "twilio_service") as twilio:
            twilio.is_configured.return_value = True
            twilio.purchase_phone_number.return_value = MagicMock(
                sid="PN-release-pending", phone_number="+15551234567"
            )
            twilio.release_phone_number.side_effect = RuntimeError("provider down")
            result, error = await phone_number_service.purchase_number(
                sample_org_id,
                PhoneNumberPurchaseRequest(phone_number="+15551234567"),
            )

        assert result is None
        from src.phone_numbers.service import PHONE_NUMBER_PURCHASE_UNAVAILABLE

        assert error == PHONE_NUMBER_PURCHASE_UNAVAILABLE
        assert table.update.call_args.args[0]["status"] == "release_pending"
        phone_number_service.billing_service.refund_credits.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_compensation_state_failure_does_not_skip_credit_refund(
        self,
        phone_number_service,
        mock_supabase_client,
        sample_org_id,
        sample_phone_number_id,
        caplog,
    ):
        """A failed release-state write cannot bypass purchase credit refund."""
        from shared.organization.phone_number_models import PhoneNumberPurchaseRequest
        from src.phone_numbers.service import PHONE_NUMBER_PURCHASE_UNAVAILABLE

        phone_number_service._get_credits_for_type = AsyncMock(return_value=200)
        phone_number_service.billing_service.consume_credits = AsyncMock(
            return_value=MagicMock(success=True, balance_after=0)
        )
        phone_number_service.billing_service.refund_credits = AsyncMock()
        table = mock_supabase_client.table.return_value
        table.execute.side_effect = [
            MagicMock(data=[{"id": str(sample_phone_number_id)}]),
            MagicMock(data=[]),
        ]

        with patch.object(
            phone_number_service,
            "_set_release_pending",
            side_effect=RuntimeError("database details"),
        ) as persist_release_state:
            with patch.object(phone_number_service, "twilio_service") as twilio:
                twilio.is_configured.return_value = True
                twilio.purchase_phone_number.return_value = MagicMock(
                    sid="PN-sensitive", phone_number="+15551234567"
                )
                twilio.release_phone_number.side_effect = RuntimeError("provider down")
                result, error = await phone_number_service.purchase_number(
                    sample_org_id,
                    PhoneNumberPurchaseRequest(phone_number="+15551234567"),
                )

        assert result is None
        assert error == PHONE_NUMBER_PURCHASE_UNAVAILABLE
        persist_release_state.assert_called_once()
        phone_number_service.billing_service.refund_credits.assert_awaited_once()
        assert "database details" not in caplog.text
        assert "provider down" not in caplog.text
        assert "PN-sensitive" not in caplog.text
        assert "+15551234567" not in caplog.text

    @pytest.mark.asyncio
    async def test_import_returns_database_error_for_unexpected_insert_failure(
        self, phone_number_service, mock_supabase_client, sample_org_id
    ):
        """Unexpected import failures remain actionable without leaking internals."""
        from shared.organization.phone_number_models import PhoneNumberImportRequest

        mock_supabase_client.table.return_value.execute.side_effect = RuntimeError(
            "database unavailable"
        )

        result, error = await phone_number_service.import_number(
            sample_org_id,
            PhoneNumberImportRequest(phone_number="+15551234567"),
        )

        assert result is None
        assert error == "Failed to import phone number: database unavailable"

    @pytest.mark.asyncio
    async def test_verification_details_sanitize_database_exception(
        self,
        phone_number_service,
        mock_supabase_client,
        sample_org_id,
        sample_phone_number_id,
    ):
        """Verification-detail database failures use a stable public error."""
        mock_supabase_client.table.return_value.execute.side_effect = RuntimeError(
            "database unavailable"
        )

        result, error = await phone_number_service.get_verification_details(
            sample_org_id, sample_phone_number_id
        )

        assert result is None
        assert error == "Failed to load phone-number verification details"

    @pytest.mark.asyncio
    async def test_purchase_marks_local_attempt_cancelled_when_provider_purchase_fails(
        self,
        phone_number_service,
        mock_supabase_client,
        sample_org_id,
        sample_phone_number_id,
        caplog,
    ):
        """A provider failure before a SID exists still closes the local attempt."""
        from shared.organization.phone_number_models import PhoneNumberPurchaseRequest

        phone_number_service._get_credits_for_type = AsyncMock(return_value=200)
        phone_number_service.billing_service.consume_credits = AsyncMock(
            return_value=MagicMock(success=True, balance_after=0)
        )
        phone_number_service.billing_service.refund_credits = AsyncMock()
        table = mock_supabase_client.table.return_value
        table.execute.side_effect = [
            MagicMock(data=[{"id": str(sample_phone_number_id)}]),
            MagicMock(data=[{"id": str(sample_phone_number_id)}]),
        ]

        with patch.object(phone_number_service, "twilio_service") as twilio:
            twilio.is_configured.return_value = True
            twilio.purchase_phone_number.side_effect = RuntimeError("provider down")
            result, error = await phone_number_service.purchase_number(
                sample_org_id,
                PhoneNumberPurchaseRequest(phone_number="+15551234567"),
            )

        assert result is None
        from src.phone_numbers.service import PHONE_NUMBER_PURCHASE_UNAVAILABLE

        assert error == PHONE_NUMBER_PURCHASE_UNAVAILABLE
        assert "provider down" not in error
        assert "provider down" not in caplog.text
        assert "+15551234567" not in caplog.text
        assert table.update.call_args.args[0]["status"] == "cancelled"
        phone_number_service.billing_service.refund_credits.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_import_can_assign_number_to_an_active_agent(
        self,
        phone_number_service,
        mock_supabase_client,
        sample_org_id,
        sample_agent_id,
        sample_purchased_phone_number,
    ):
        """Import validates and preserves an optional in-organization assignment."""
        from shared.organization.phone_number_models import PhoneNumberImportRequest

        row = {
            **sample_purchased_phone_number,
            "status": "verification_required",
            "organization_id": str(sample_org_id),
            "assigned_agent_id": str(sample_agent_id),
            "is_incoming_enabled": False,
            "billing_mode": "none",
            "management_mode": "customer_managed",
            "provisioning_source": "customer",
            "configuration_status": "verification_required",
        }
        table = mock_supabase_client.table.return_value
        table.execute.side_effect = [
            MagicMock(data=[{"id": str(sample_agent_id)}]),
            MagicMock(data=[row]),
        ]

        result, error = await phone_number_service.import_number(
            sample_org_id,
            PhoneNumberImportRequest(
                phone_number="+15551234567", agent_id=sample_agent_id
            ),
        )

        assert error is None
        assert result.success is True
        assert result.phone_number.assigned_agent_id == sample_agent_id


class TestPhoneNumberServiceAssignmentBranches:
    """Cover assignment scoping, idempotence, and update failure handling."""

    @pytest.mark.asyncio
    async def test_assign_rejects_terminal_status_with_organization_scope(
        self,
        phone_number_service,
        mock_supabase_client,
        sample_org_id,
        sample_phone_number_id,
        sample_agent_id,
        sample_purchased_phone_number,
    ):
        """Cancelled numbers cannot be reattached to an agent."""
        from shared.organization.phone_number_models import PhoneNumberAssignRequest

        row = {
            **sample_purchased_phone_number,
            "status": "cancelled",
            "organization_id": str(sample_org_id),
        }
        mock_supabase_client.table.return_value.execute.return_value = MagicMock(
            data=[row]
        )

        result, error = await phone_number_service.assign_to_agent(
            sample_phone_number_id,
            PhoneNumberAssignRequest(agent_id=sample_agent_id),
            organization_id=sample_org_id,
        )

        assert result is None
        assert "Cannot assign number with status" in error

    @pytest.mark.asyncio
    async def test_assign_is_idempotent_for_same_agent_with_organization_scope(
        self,
        phone_number_service,
        mock_supabase_client,
        sample_org_id,
        sample_phone_number_id,
        sample_agent_id,
        sample_purchased_phone_number,
    ):
        """Repeating an existing mapping is a successful no-op."""
        from shared.organization.phone_number_models import PhoneNumberAssignRequest

        row = {
            **sample_purchased_phone_number,
            "status": "active",
            "organization_id": str(sample_org_id),
            "assigned_agent_id": str(sample_agent_id),
        }
        mock_supabase_client.table.return_value.execute.return_value = MagicMock(
            data=[row]
        )

        result, error = await phone_number_service.assign_to_agent(
            sample_phone_number_id,
            PhoneNumberAssignRequest(agent_id=sample_agent_id),
            organization_id=sample_org_id,
        )

        assert error is None
        assert result.assigned_agent_id == sample_agent_id
        mock_supabase_client.table.return_value.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_assign_reports_update_failure_after_scoped_agent_check(
        self,
        phone_number_service,
        mock_supabase_client,
        sample_org_id,
        sample_phone_number_id,
        sample_agent_id,
        sample_purchased_phone_number,
    ):
        """An empty update response does not report a false assignment success."""
        from shared.organization.phone_number_models import PhoneNumberAssignRequest

        row = {
            **sample_purchased_phone_number,
            "organization_id": str(sample_org_id),
            "assigned_agent_id": None,
        }
        table = mock_supabase_client.table.return_value
        table.execute.side_effect = [
            MagicMock(data=[row]),
            MagicMock(data=[{"id": str(sample_agent_id)}]),
            MagicMock(data=[]),
        ]

        result, error = await phone_number_service.assign_to_agent(
            sample_phone_number_id,
            PhoneNumberAssignRequest(agent_id=sample_agent_id),
            organization_id=sample_org_id,
        )

        assert result is None
        assert error == "Failed to update phone number"

    @pytest.mark.asyncio
    async def test_assign_sanitizes_database_exception(
        self,
        phone_number_service,
        mock_supabase_client,
        sample_phone_number_id,
        sample_agent_id,
    ):
        """Assignment database failures return a service-level error."""
        from shared.organization.phone_number_models import PhoneNumberAssignRequest

        mock_supabase_client.table.return_value.execute.side_effect = RuntimeError(
            "database unavailable"
        )

        result, error = await phone_number_service.assign_to_agent(
            sample_phone_number_id,
            PhoneNumberAssignRequest(agent_id=sample_agent_id),
        )

        assert result is None
        assert "Failed to assign phone number" in error


class TestPhoneNumberServiceCancellationAndRentalBranches:
    """Cover provider release retries and rental state transitions."""

    @pytest.mark.asyncio
    async def test_cancel_queues_release_when_provider_release_fails(
        self,
        phone_number_service,
        mock_supabase_client,
        sample_org_id,
        sample_phone_number_id,
        sample_purchased_phone_number,
    ):
        """A provider outage leaves a platform number in release_pending."""
        row = {
            **sample_purchased_phone_number,
            "organization_id": str(sample_org_id),
            "status": "purchased",
        }
        table = mock_supabase_client.table.return_value
        table.execute.side_effect = [MagicMock(data=[row]), MagicMock(data=[row])]

        with patch.object(phone_number_service, "twilio_service") as twilio:
            twilio.is_configured.return_value = True
            twilio.release_phone_number.side_effect = RuntimeError("provider down")
            success, error = await phone_number_service.cancel_number(
                sample_phone_number_id, organization_id=sample_org_id
            )

        assert success is True
        assert error == "release_pending"
        assert table.update.call_args.args[0]["status"] == "release_pending"

    @pytest.mark.asyncio
    async def test_cancel_reports_empty_status_update(
        self,
        phone_number_service,
        mock_supabase_client,
        sample_org_id,
        sample_phone_number_id,
        sample_purchased_phone_number,
    ):
        """Cancellation does not succeed when its status update is empty."""
        row = {
            **sample_purchased_phone_number,
            "organization_id": str(sample_org_id),
            "status": "active",
            "management_mode": "customer_managed",
            "provisioning_source": "customer",
            "billing_mode": "none",
        }
        table = mock_supabase_client.table.return_value
        table.execute.side_effect = [MagicMock(data=[row]), MagicMock(data=[])]

        success, error = await phone_number_service.cancel_number(
            sample_phone_number_id, organization_id=sample_org_id
        )

        assert success is False
        assert error == "Failed to update phone number status"

    @pytest.mark.asyncio
    async def test_cancel_sanitizes_database_exception(
        self, phone_number_service, mock_supabase_client, sample_phone_number_id
    ):
        """Cancellation database failures return an actionable error."""
        mock_supabase_client.table.return_value.execute.side_effect = RuntimeError(
            "database unavailable"
        )

        success, error = await phone_number_service.cancel_number(
            sample_phone_number_id
        )

        assert success is False
        assert "Failed to cancel phone number" in error

    @pytest.mark.asyncio
    async def test_get_by_id_returns_a_phone_number(
        self,
        phone_number_service,
        mock_supabase_client,
        sample_phone_number_id,
        sample_purchased_phone_number,
    ):
        """Successful detail loading returns the normalized model."""
        mock_supabase_client.table.return_value.execute.return_value = MagicMock(
            data=[sample_purchased_phone_number]
        )

        number, error = await phone_number_service.get_by_id(sample_phone_number_id)

        assert error is None
        assert number.id == sample_phone_number_id

    @pytest.mark.asyncio
    async def test_process_due_rentals_counts_release_retry_errors(
        self, phone_number_service, mock_supabase_client, sample_purchased_phone_number
    ):
        """A failed release retry is visible in the maintenance summary."""
        row = {
            **sample_purchased_phone_number,
            "status": "release_pending",
            "billing_mode": "platform_rental",
        }
        table = mock_supabase_client.table.return_value
        table.execute.return_value = MagicMock(data=[row])

        with patch.object(phone_number_service, "twilio_service") as twilio:
            twilio.release_phone_number.side_effect = RuntimeError("provider down")
            result = await phone_number_service.process_due_rentals()

        assert result.errors == 1
        assert result.released == 0

    @pytest.mark.asyncio
    async def test_process_due_rentals_skips_number_not_yet_due(
        self, phone_number_service, mock_supabase_client, sample_purchased_phone_number
    ):
        """Future rental dates do not trigger a debit."""
        row = {
            **sample_purchased_phone_number,
            "status": "purchased",
            "billing_mode": "platform_rental",
            "next_billing_at": (
                datetime.now(timezone.utc) + timedelta(days=5)
            ).isoformat(),
        }
        mock_supabase_client.table.return_value.execute.return_value = MagicMock(
            data=[row]
        )
        phone_number_service.billing_service.consume_credits = AsyncMock()

        result = await phone_number_service.process_due_rentals()

        assert result.processed == 0
        phone_number_service.billing_service.consume_credits.assert_not_awaited()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("cancel_result", "expected_processed", "expected_released", "expected_errors"),
        [
            ((True, None), 1, 1, 0),
            ((True, "release_pending"), 1, 0, 1),
            ((False, "provider error"), 0, 0, 1),
        ],
    )
    async def test_process_due_rentals_handles_expired_grace_period(
        self,
        phone_number_service,
        mock_supabase_client,
        sample_purchased_phone_number,
        cancel_result,
        expected_processed,
        expected_released,
        expected_errors,
    ):
        """Expired grace periods account for success, pending, and failed release."""
        now = datetime.now(timezone.utc)
        row = {
            **sample_purchased_phone_number,
            "status": "active",
            "billing_mode": "platform_rental",
            "billing_status": "past_due",
            "next_billing_at": (now - timedelta(days=2)).isoformat(),
            "billing_grace_ends_at": (now - timedelta(days=1)).isoformat(),
        }
        mock_supabase_client.table.return_value.execute.return_value = MagicMock(
            data=[row]
        )
        phone_number_service.cancel_number = AsyncMock(return_value=cancel_result)

        result = await phone_number_service.process_due_rentals(now=now)

        assert result.processed == expected_processed
        assert result.released == expected_released
        assert result.errors == expected_errors
        phone_number_service.cancel_number.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_process_due_rentals_counts_malformed_rows_as_errors(
        self, phone_number_service, mock_supabase_client
    ):
        """Malformed legacy rows do not abort processing of the remaining batch."""
        mock_supabase_client.table.return_value.execute.return_value = MagicMock(
            data=[{"id": "malformed"}]
        )

        result = await phone_number_service.process_due_rentals()

        assert result.errors == 1

    @pytest.mark.asyncio
    async def test_retry_release_pending_without_provider_sid_marks_cancelled(
        self, phone_number_service, mock_supabase_client, sample_purchased_phone_number
    ):
        """Rows without a provider SID are safe to finalize locally."""
        from shared.organization.phone_number_models import PhoneNumber

        row = {
            **sample_purchased_phone_number,
            "status": "release_pending",
            "provider_sid": None,
        }
        phone_number = PhoneNumber(**row)
        mock_supabase_client.table.return_value.execute.return_value = MagicMock(
            data=[row]
        )

        released, error = await phone_number_service._retry_release_pending(
            phone_number
        )

        assert released is True
        assert error is None
        assert (
            mock_supabase_client.table.return_value.update.call_args.args[0]["status"]
            == "cancelled"
        )

    @pytest.mark.asyncio
    async def test_retry_release_pending_returns_provider_error(
        self, phone_number_service, sample_purchased_phone_number
    ):
        """A failed pending-release retry remains eligible for the next run."""
        from shared.organization.phone_number_models import PhoneNumber

        row = {**sample_purchased_phone_number, "status": "release_pending"}
        phone_number = PhoneNumber(**row)
        phone_number_service.twilio_service.release_phone_number = MagicMock(
            side_effect=RuntimeError("provider down")
        )

        released, error = await phone_number_service._retry_release_pending(
            phone_number
        )

        assert released is False
        assert error == "provider down"
