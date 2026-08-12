"""Tests for the fixed, system-wide usage-pricing catalog."""

from shared.organization.phone_number_models import PhoneNumberType
from src.billing.system_pricing import (
    SYSTEM_PRICING_EVENT_NAMES,
    get_phone_number_pricing_event_name,
    get_system_pricing_definition,
)


def test_system_pricing_contains_only_supported_billable_activities():
    """The catalog exposes call minutes and monthly phone-number rentals only."""
    assert SYSTEM_PRICING_EVENT_NAMES == (
        "voice_call_minute",
        "phone_number_local_month",
        "phone_number_mobile_month",
        "phone_number_toll_free_month",
    )


def test_call_minutes_have_fixed_duration_semantics():
    """Voice calls are priced per connected minute, not by arbitrary measures."""
    definition = get_system_pricing_definition("voice_call_minute")

    assert definition.meter_type == "duration"
    assert definition.billing_unit == "minute"
    assert "connected" in definition.description.lower()


def test_phone_number_type_maps_to_monthly_system_event():
    """Each supported phone-number type resolves to its own monthly rate."""
    assert (
        get_phone_number_pricing_event_name(PhoneNumberType.LOCAL)
        == "phone_number_local_month"
    )
    assert (
        get_phone_number_pricing_event_name(PhoneNumberType.MOBILE)
        == "phone_number_mobile_month"
    )
    assert (
        get_phone_number_pricing_event_name(PhoneNumberType.TOLL_FREE)
        == "phone_number_toll_free_month"
    )
