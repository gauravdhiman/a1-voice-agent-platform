"""Contract tests for platform-managed and customer-managed phone numbers."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from shared.organization.phone_number_models import (
    PhoneNumberBillingMode,
    PhoneNumberConfigurationStatus,
    PhoneNumberImportRequest,
    PhoneNumberManagementMode,
    PhoneNumberProvisioningSource,
    PhoneNumberStatus,
    PhoneNumberType,
)


def test_customer_import_request_accepts_e164_number():
    """Customer-owned numbers can enter the platform without a provider SID."""
    request = PhoneNumberImportRequest(
        phone_number="(415) 555-0100",
        country_code="US",
        phone_number_type=PhoneNumberType.LOCAL,
    )

    assert request.phone_number == "(415) 555-0100"
    assert request.agent_id is None


def test_phone_number_management_defaults_are_explicit():
    """Legacy platform rows retain platform-managed billing semantics."""
    assert PhoneNumberProvisioningSource.PLATFORM.value == "platform"
    assert PhoneNumberManagementMode.PLATFORM.value == "platform_managed"
    assert PhoneNumberConfigurationStatus.CONFIGURED.value == "configured"
    assert PhoneNumberBillingMode.PLATFORM_RENTAL.value == "platform_rental"
    assert PhoneNumberStatus.RELEASE_PENDING.value == "release_pending"


def test_purchase_configures_voice_and_status_webhooks():
    """The production Twilio adapter sends both callbacks during provisioning."""
    from src.phone_numbers.twilio_service import TwilioService

    service = TwilioService.__new__(TwilioService)
    service.client = MagicMock()
    service.client.incoming_phone_numbers.create.return_value = MagicMock(
        sid="PN123", phone_number="+14155550100"
    )

    service.purchase_phone_number(
        phone_number="+14155550100",
        voice_url="https://api.example.com/api/v1/voice/twilio/incoming",
        status_callback="https://api.example.com/api/v1/voice/twilio/status",
    )

    service.client.incoming_phone_numbers.create.assert_called_once_with(
        phone_number="+14155550100",
        voice_url="https://api.example.com/api/v1/voice/twilio/incoming",
        voice_method="POST",
        status_callback="https://api.example.com/api/v1/voice/twilio/status",
        status_callback_method="POST",
        voice_application_sid=None,
        sms_application_sid=None,
    )


@pytest.fixture
def lifecycle_service(mock_supabase_client):
    """Create a phone-number service with isolated provider and billing mocks."""
    from src.phone_numbers.service import PhoneNumberService

    service = PhoneNumberService.__new__(PhoneNumberService)
    service.supabase = mock_supabase_client
    service.twilio_service = MagicMock()
    service.twilio_service.is_configured.return_value = True
    service.billing_service = MagicMock()
    service.entitlement_service = MagicMock()
    service.entitlement_service.assert_limit = AsyncMock()
    return service


def test_webhook_urls_include_a_customer_connection_token():
    """Imported numbers receive per-number URLs without exposing a raw secret."""
    from src.phone_numbers.service import build_phone_number_webhook_urls

    urls = build_phone_number_webhook_urls(
        "https://api.example.com", connection_token="opaque-token"
    )

    assert urls.voice_url.startswith(
        "https://api.example.com/api/v1/voice/twilio/incoming?"
    )
    assert "connection_token=opaque-token" in urls.voice_url
    assert urls.status_callback.endswith("connection_token=opaque-token")


def test_number_normalization_supports_e164_and_us_national_input():
    """Routing accepts common US display formats and preserves E.164 values."""
    from src.phone_numbers.utils import normalize_phone_number

    assert normalize_phone_number("(415) 555-0100") == "+14155550100"
    assert normalize_phone_number("+442071838750", "GB") == "+442071838750"


def test_number_normalization_rejects_ambiguous_international_national_input():
    """Non-US numbers must be supplied in E.164 until country parsers are added."""
    from fastapi import HTTPException
    from src.phone_numbers.utils import normalize_phone_number

    with pytest.raises(HTTPException):
        normalize_phone_number("2071838750", "GB")


@pytest.mark.asyncio
async def test_search_forwards_digits_only_contains_pattern(lifecycle_service):
    """Formatting characters do not change the provider's generic contains search."""
    from src.phone_numbers.service import PhoneNumberService

    lifecycle_service.twilio_service.search_available_numbers.return_value = []
    lifecycle_service._get_credits_for_type = AsyncMock(return_value=200)

    from shared.organization.phone_number_models import PhoneNumberSearchRequest

    await PhoneNumberService.search_available(
        lifecycle_service,
        PhoneNumberSearchRequest(country_code="us", contains="+1 (415)"),
    )

    lifecycle_service.twilio_service.search_available_numbers.assert_called_once_with(
        country_code="US",
        number_type="local",
        area_code=None,
        contains="1415",
        limit=50,
    )


@pytest.mark.asyncio
async def test_import_existing_number_is_not_billed_or_released(
    lifecycle_service, mock_supabase_client
):
    """Customer-owned imports create a verification record without Twilio billing."""
    from src.phone_numbers.service import PhoneNumberService

    now = datetime.now(timezone.utc).isoformat()
    row = {
        "id": str(uuid4()),
        "organization_id": str(uuid4()),
        "phone_number": "+14155550100",
        "provider": "twilio",
        "provider_sid": None,
        "phone_number_type": "local",
        "country_code": "US",
        "area_code": "415",
        "monthly_cost_credits": 0,
        "status": "verification_required",
        "assigned_agent_id": None,
        "is_incoming_enabled": False,
        "is_outgoing_enabled": False,
        "billing_status": "active",
        "billing_mode": "none",
        "provisioning_source": "customer",
        "management_mode": "customer_managed",
        "configuration_status": "verification_required",
        "next_billing_at": None,
        "billing_grace_ends_at": None,
        "purchased_at": now,
        "cancelled_at": None,
        "created_at": now,
        "updated_at": now,
    }
    mock_supabase_client.table.return_value.insert.return_value.execute.return_value = (
        MagicMock(data=[row])
    )

    result, error = await PhoneNumberService.import_number(
        lifecycle_service,
        organization_id=uuid4(),
        import_request=PhoneNumberImportRequest(phone_number="+14155550100"),
    )

    assert error is None
    assert result.success is True
    assert "connection_token=" in result.voice_url
    lifecycle_service.billing_service.consume_credits.assert_not_called()
    lifecycle_service.twilio_service.purchase_phone_number.assert_not_called()


@pytest.mark.asyncio
async def test_customer_owned_number_disconnects_without_twilio_release(
    lifecycle_service, mock_supabase_client
):
    """Disconnecting an imported number must never release the customer's asset."""
    from src.phone_numbers.service import PhoneNumberService

    number_id = uuid4()
    organization_id = uuid4()
    now = datetime.now(timezone.utc).isoformat()
    row = {
        "id": str(number_id),
        "organization_id": str(organization_id),
        "phone_number": "+14155550100",
        "provider": "twilio",
        "provider_sid": "PN-CUSTOMER",
        "phone_number_type": "local",
        "country_code": "US",
        "monthly_cost_credits": 0,
        "status": "active",
        "assigned_agent_id": None,
        "is_incoming_enabled": True,
        "is_outgoing_enabled": False,
        "billing_status": "active",
        "billing_mode": "none",
        "provisioning_source": "customer",
        "management_mode": "customer_managed",
        "configuration_status": "configured",
        "purchased_at": now,
        "cancelled_at": None,
        "created_at": now,
        "updated_at": now,
    }
    table = mock_supabase_client.table.return_value
    table.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[row]
    )
    table.update.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[row]
    )

    success, error = await PhoneNumberService.cancel_number(
        lifecycle_service, number_id, organization_id
    )

    assert success is True
    assert error is None
    lifecycle_service.twilio_service.release_phone_number.assert_not_called()
    assert table.update.call_args.args[0]["status"] == "disconnected"


@pytest.mark.asyncio
async def test_purchase_refunds_and_marks_release_pending_when_provider_compensation_fails(
    lifecycle_service, mock_supabase_client
):
    """Provider failures are compensated and orphaned SIDs become retryable."""
    from src.billing.models import CreditConsumptionResponse
    from src.phone_numbers.service import PhoneNumberService

    from shared.organization.phone_number_models import PhoneNumberPurchaseRequest

    organization_id = uuid4()
    record_id = uuid4()
    lifecycle_service.billing_service.consume_credits = AsyncMock(
        return_value=CreditConsumptionResponse(
            success=True,
            credits_consumed=200,
            balance_after=800,
            transaction_id=uuid4(),
        )
    )
    lifecycle_service.billing_service.refund_credits = AsyncMock()
    lifecycle_service._get_credits_for_type = AsyncMock(return_value=200)
    lifecycle_service.twilio_service.purchase_phone_number.return_value = MagicMock(
        sid="PN-ORPHAN"
    )
    lifecycle_service.twilio_service.release_phone_number.side_effect = RuntimeError(
        "provider unavailable"
    )
    table = mock_supabase_client.table.return_value
    table.execute.side_effect = [
        MagicMock(data=[{"id": str(record_id)}]),
        MagicMock(data=[]),
        MagicMock(data=[]),
    ]

    result, error = await PhoneNumberService.purchase_number(
        lifecycle_service,
        organization_id,
        PhoneNumberPurchaseRequest(phone_number="+14155550100"),
    )

    assert result is None
    assert "Failed to purchase" in error
    lifecycle_service.billing_service.refund_credits.assert_awaited_once()
    assert table.update.call_args.args[0]["status"] == "release_pending"


@pytest.mark.asyncio
async def test_purchase_idempotency_key_does_not_purchase_twice(
    lifecycle_service, mock_supabase_client
):
    """A client retry returns the existing row before touching Twilio again."""
    from src.phone_numbers.service import PhoneNumberService

    from shared.organization.phone_number_models import PhoneNumberPurchaseRequest

    now = datetime.now(timezone.utc).isoformat()
    row = {
        "id": str(uuid4()),
        "organization_id": str(uuid4()),
        "phone_number": "+14155550100",
        "provider": "twilio",
        "provider_sid": "PN-EXISTING",
        "phone_number_type": "local",
        "country_code": "US",
        "monthly_cost_credits": 200,
        "status": "purchased",
        "assigned_agent_id": None,
        "is_incoming_enabled": True,
        "is_outgoing_enabled": False,
        "billing_status": "active",
        "billing_mode": "platform_rental",
        "provisioning_source": "platform",
        "management_mode": "platform_managed",
        "configuration_status": "configured",
        "purchased_at": now,
        "cancelled_at": None,
        "created_at": now,
        "updated_at": now,
    }
    table = mock_supabase_client.table.return_value
    table.execute.return_value = MagicMock(data=[row])

    result, error = await PhoneNumberService.purchase_number(
        lifecycle_service,
        uuid4(),
        PhoneNumberPurchaseRequest(phone_number="+14155550100"),
        idempotency_key="purchase-key",
    )

    assert error is None
    assert result.phone_number.provider_sid == "PN-EXISTING"
    lifecycle_service.twilio_service.purchase_phone_number.assert_not_called()
