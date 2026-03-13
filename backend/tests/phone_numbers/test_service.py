"""
Phone Number Service Tests
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from shared.organization.phone_number_models import (
    PhoneNumberStatus,
    PhoneNumberType,
)


@pytest.fixture
def phone_number_service(mock_supabase_client):
    """Create PhoneNumberService instance with fresh mocks for each test."""
    from src.phone_numbers.service import PhoneNumberService

    with patch("src.phone_numbers.service.supabase_config") as mock_config:
        mock_config.client = mock_supabase_client

        service = PhoneNumberService()
        service.supabase = mock_supabase_client
        service.billing_service = MagicMock()

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
            assert result.items[0].monthly_cost_credits == 200

    @pytest.mark.asyncio
    async def test_search_returns_empty_when_not_configured(self, phone_number_service):
        """Returns empty list when Twilio is not configured."""
        from shared.organization.phone_number_models import PhoneNumberSearchRequest

        with patch.object(phone_number_service, "twilio_service") as mock_twilio:
            mock_twilio.is_configured.return_value = False

            request = PhoneNumberSearchRequest()

            result, error = await phone_number_service.search_available(request)

            assert error is None
            assert result.items == []
            assert result.total_count == 0

    @pytest.mark.asyncio
    async def test_search_handles_exception(
        self, phone_number_service, mock_supabase_client
    ):
        """Returns error message when search fails."""
        from shared.organization.phone_number_models import PhoneNumberSearchRequest

        with patch.object(phone_number_service, "twilio_service") as mock_twilio:
            mock_twilio.is_configured.return_value = True
            mock_twilio.search_available_numbers.side_effect = Exception(
                "Twilio API error"
            )

            request = PhoneNumberSearchRequest()

            result, error = await phone_number_service.search_available(request)

            assert error is not None
            assert "Failed to search available numbers" in error

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
    async def test_purchase_number_success(
        self,
        phone_number_service,
        mock_supabase_client,
        sample_org_id,
        sample_phone_number_id,
    ):
        """Purchases a phone number successfully."""
        from shared.organization.phone_number_models import (
            PhoneNumberPurchaseRequest,
        )
        from src.billing.models import CreditBalance

        now = datetime.now(timezone.utc)

        mock_balance = MagicMock()
        mock_balance.total_credits = 1000

        phone_number_service.billing_service.get_credit_balance = AsyncMock(
            return_value=mock_balance
        )
        phone_number_service.billing_service.consume_credits = AsyncMock(
            return_value=MagicMock(success=True, remaining_credits=800)
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
            mock_supabase_client.table.return_value.insert.return_value.execute.return_value = mock_response

            request = PhoneNumberPurchaseRequest(
                phone_number="+15551234567",
                country_code="US",
                phone_number_type=PhoneNumberType.LOCAL,
            )

            result, error = await phone_number_service.purchase_number(
                sample_org_id, request
            )

            assert error is None
            assert result is not None
            assert result.success is True
            assert result.phone_number.phone_number == "+15551234567"
            assert result.credit_balance_after == 800

    @pytest.mark.asyncio
    async def test_purchase_number_insufficient_credits(
        self, phone_number_service, sample_org_id
    ):
        """Fails purchase when organization has insufficient credits."""
        from shared.organization.phone_number_models import (
            PhoneNumberPurchaseRequest,
        )
        from src.billing.models import CreditBalance

        mock_balance = MagicMock()
        mock_balance.total_credits = 100

        phone_number_service.billing_service.get_credit_balance = AsyncMock(
            return_value=mock_balance
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
        from shared.organization.phone_number_models import (
            PhoneNumberPurchaseRequest,
        )

        with patch.object(phone_number_service, "twilio_service") as mock_twilio:
            mock_twilio.is_configured.return_value = False

            request = PhoneNumberPurchaseRequest(phone_number="+15551234567")

            result, error = await phone_number_service.purchase_number(
                sample_org_id, request
            )

            assert result is None
            assert error == "Phone number provider not configured"


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
        mock_agent_response.data = [{"name": "Test Agent"}]

        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.side_effect = [
            mock_phone_response,
            mock_agent_response,
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

        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        result, error = await phone_number_service.get_organization_numbers(
            sample_org_id
        )

        assert error is None
        assert result.items == []
        assert result.total_count == 0


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
        from shared.organization.phone_number_models import (
            PhoneNumberAssignRequest,
        )

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
        mock_supabase_client.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_update_response

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
        from shared.organization.phone_number_models import (
            PhoneNumberAssignRequest,
        )

        mock_response = MagicMock()
        mock_response.data = []

        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

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
        from shared.organization.phone_number_models import (
            PhoneNumberAssignRequest,
        )

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

        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

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
        from shared.organization.phone_number_models import (
            PhoneNumberAssignRequest,
        )

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


class TestPhoneNumberServiceCancel:
    """Test cases for canceling phone numbers."""

    @pytest.mark.asyncio
    async def test_cancel_number_success(
        self,
        phone_number_service,
        mock_supabase_client,
        sample_phone_number_id,
    ):
        """Cancels phone number successfully."""
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
            MagicMock(data=update_data)
        ]

        result, error = await phone_number_service.cancel_number(
            sample_phone_number_id
        )

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
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

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

        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        result, error = await phone_number_service.cancel_number(sample_phone_number_id)

        assert result is False
        assert "already cancelled" in error


class TestPhoneNumberServiceGetCreditsForType:
    """Test cases for credit cost calculation."""

    def test_credits_for_local_number(self, phone_number_service):
        """Returns correct credits for local number."""
        result = phone_number_service._get_credits_for_type(PhoneNumberType.LOCAL)
        assert result == 200

    def test_credits_for_toll_free_number(self, phone_number_service):
        """Returns correct credits for toll-free number."""
        result = phone_number_service._get_credits_for_type(PhoneNumberType.TOLL_FREE)
        assert result == 500

    def test_credits_for_mobile_number(self, phone_number_service):
        """Returns correct credits for mobile number."""
        result = phone_number_service._get_credits_for_type(PhoneNumberType.MOBILE)
        assert result == 200

    def test_credits_for_unknown_type(self, phone_number_service):
        """Returns default credits for unknown type."""
        result = phone_number_service._get_credits_for_type(None)
        assert result == 200
