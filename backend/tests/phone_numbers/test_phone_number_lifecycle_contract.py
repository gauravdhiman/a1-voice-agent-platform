"""Contract tests for platform-managed and customer-managed phone numbers."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from shared.common.security import decrypt_data
from shared.organization.phone_number_models import (
    PhoneNumberBillingMode,
    PhoneNumberConfigurationStatus,
    PhoneNumberImportRequest,
    PhoneNumberManagementMode,
    PhoneNumberProvisioningSource,
    PhoneNumberSearchMode,
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


def test_search_mode_defaults_to_contains():
    """The existing generic search remains the default match mode."""
    from shared.organization.phone_number_models import PhoneNumberSearchRequest

    request = PhoneNumberSearchRequest()

    assert request.search_mode is PhoneNumberSearchMode.CONTAINS


def test_search_pattern_matches_twilio_maximum_length():
    """Provider-bound search patterns do not exceed Twilio's 16-character limit."""
    from pydantic import ValidationError
    from shared.organization.phone_number_models import PhoneNumberSearchRequest

    with pytest.raises(ValidationError):
        PhoneNumberSearchRequest(contains="12345678901234567")


def test_search_pattern_accepts_string_match_modes_for_direct_callers():
    """The normalization helper remains safe for non-Pydantic callers."""
    from src.phone_numbers.utils import normalize_search_contains

    assert normalize_search_contains("2168", "ends_with") == "2168$"


@pytest.mark.asyncio
async def test_search_forwards_twilio_contains_pattern(lifecycle_service):
    """Formatting characters do not change the provider's contains search."""
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
        contains="%1415%",
        limit=50,
    )


@pytest.mark.asyncio
async def test_search_forwards_twilio_prefix_pattern_for_us_national_input(
    lifecycle_service,
):
    """Begin searches prepend the US country code for national input."""
    from src.phone_numbers.service import PhoneNumberService

    lifecycle_service.twilio_service.search_available_numbers.return_value = []

    from shared.organization.phone_number_models import PhoneNumberSearchRequest

    await PhoneNumberService.search_available(
        lifecycle_service,
        PhoneNumberSearchRequest(
            country_code="US",
            contains="(480)",
            search_mode=PhoneNumberSearchMode.BEGINS_WITH,
        ),
    )

    lifecycle_service.twilio_service.search_available_numbers.assert_called_once_with(
        country_code="US",
        number_type="local",
        area_code=None,
        contains="+1480",
        limit=50,
    )


@pytest.mark.asyncio
async def test_search_forwards_twilio_suffix_pattern(lifecycle_service):
    """End searches use Twilio's documented dollar-suffix pattern."""
    from src.phone_numbers.service import PhoneNumberService

    lifecycle_service.twilio_service.search_available_numbers.return_value = []

    from shared.organization.phone_number_models import PhoneNumberSearchRequest

    await PhoneNumberService.search_available(
        lifecycle_service,
        PhoneNumberSearchRequest(
            country_code="US",
            contains="21-68",
            search_mode=PhoneNumberSearchMode.ENDS_WITH,
        ),
    )

    lifecycle_service.twilio_service.search_available_numbers.assert_called_once_with(
        country_code="US",
        number_type="local",
        area_code=None,
        contains="2168$",
        limit=50,
    )


@pytest.mark.asyncio
async def test_import_existing_number_is_not_billed_or_released(
    lifecycle_service, mock_supabase_client
):
    """Customer-owned imports bypass platform number entitlements and billing."""
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
    lifecycle_service.entitlement_service.assert_limit.assert_not_awaited()
    lifecycle_service.billing_service.consume_credits.assert_not_called()
    lifecycle_service.twilio_service.purchase_phone_number.assert_not_called()
    inserted = mock_supabase_client.table.return_value.insert.call_args.args[0]
    assert decrypt_data(inserted["connection_token_encrypted"])["token"]


@pytest.mark.asyncio
async def test_verification_details_can_be_retrieved_until_customer_number_is_verified(
    lifecycle_service, mock_supabase_client
):
    """Customer webhook URLs remain available while verification is pending."""
    from shared.common.security import encrypt_data
    from src.phone_numbers.service import PhoneNumberService

    row = {
        "id": str(uuid4()),
        "phone_number": "+14155550100",
        "status": "verification_required",
        "provisioning_source": "customer",
        "management_mode": "customer_managed",
        "connection_token_encrypted": encrypt_data({"token": "saved-token"}),
    }
    mock_supabase_client.table.return_value.execute.return_value = MagicMock(data=[row])

    result, error = await PhoneNumberService.get_verification_details(
        lifecycle_service,
        organization_id=uuid4(),
        phone_number_id=uuid4(),
    )

    assert error is None
    assert result is not None
    assert "connection_token=saved-token" in result.voice_url
    assert "connection_token=saved-token" in result.status_callback


@pytest.mark.asyncio
async def test_verification_details_are_unavailable_after_verification(
    lifecycle_service, mock_supabase_client
):
    """Configured customer numbers do not expose their retired setup token."""
    from src.phone_numbers.service import PhoneNumberService

    mock_supabase_client.table.return_value.execute.return_value = MagicMock(
        data=[
            {
                "id": str(uuid4()),
                "phone_number": "+14155550100",
                "status": "active",
                "provisioning_source": "customer",
                "management_mode": "customer_managed",
                "connection_token_encrypted": "encrypted-token",
            }
        ]
    )

    result, error = await PhoneNumberService.get_verification_details(
        lifecycle_service,
        organization_id=uuid4(),
        phone_number_id=uuid4(),
    )

    assert result is None
    assert error == "Verification details are only available while setup is pending"


@pytest.mark.asyncio
async def test_pending_legacy_number_gets_a_replacement_verification_token(
    lifecycle_service, mock_supabase_client
):
    """Pending rows created before encrypted storage can recover their setup URLs."""
    from src.phone_numbers.service import PhoneNumberService

    phone_number_id = uuid4()
    row = {
        "id": str(phone_number_id),
        "phone_number": "+14155550100",
        "status": "verification_required",
        "provisioning_source": "customer",
        "management_mode": "customer_managed",
        "connection_token_encrypted": None,
    }
    table = mock_supabase_client.table.return_value
    table.execute.return_value = MagicMock(data=[row])
    table.update.return_value.execute.return_value = MagicMock(data=[row])

    result, error = await PhoneNumberService.get_verification_details(
        lifecycle_service,
        organization_id=uuid4(),
        phone_number_id=phone_number_id,
    )

    assert error is None
    assert result is not None
    assert "connection_token=" in result.voice_url
    update_payload = table.update.call_args.args[0]
    assert update_payload["connection_token_hash"]
    assert update_payload["connection_token_encrypted"]


@pytest.mark.asyncio
async def test_import_duplicate_number_returns_actionable_error(
    lifecycle_service, mock_supabase_client
):
    """A number already connected is reported without leaking a DB error."""
    from src.phone_numbers.service import PhoneNumberService

    mock_supabase_client.table.return_value.insert.return_value.execute.side_effect = (
        Exception(
            "duplicate key value violates unique constraint "
            '"uq_phone_numbers_active_number"'
        )
    )

    result, error = await PhoneNumberService.import_number(
        lifecycle_service,
        organization_id=uuid4(),
        import_request=PhoneNumberImportRequest(phone_number="+14155550100"),
    )

    assert result is None
    assert error == (
        "This phone number is already connected. "
        "Select it from the phone-number list instead."
    )


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
    from shared.organization.phone_number_models import PhoneNumberPurchaseRequest
    from src.billing.models import CreditConsumptionResponse
    from src.phone_numbers.service import PhoneNumberService

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
    from shared.organization.phone_number_models import PhoneNumberPurchaseRequest
    from src.phone_numbers.service import PhoneNumberService

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
