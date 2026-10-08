"""Definitions for the platform's fixed, system-wide credit prices.

The entries in this module are the contract between user activity handlers and
the platform-admin catalog. They are deliberately finite: administrators can
change a rate, including setting it to zero, but cannot invent a new meter that
the runtime does not know how to enforce.
"""

from __future__ import annotations

from dataclasses import dataclass

from shared.organization.phone_number_models import PhoneNumberType


@dataclass(frozen=True)
class SystemPricingDefinition:
    """Describe one supported system-level usage price."""

    event_name: str
    display_name: str
    description: str
    category: str
    meter_type: str
    billing_unit: str
    default_credit_cost: int


SYSTEM_PRICING: tuple[SystemPricingDefinition, ...] = (
    SystemPricingDefinition(
        event_name="voice_call_minute",
        display_name="Voice calls",
        description=(
            "A connected voice call is charged for each whole minute, rounded up."
        ),
        category="voice",
        meter_type="duration",
        billing_unit="minute",
        default_credit_cost=10,
    ),
    SystemPricingDefinition(
        event_name="phone_number_local_month",
        display_name="Existing non-US local phone numbers",
        description=(
            "Existing non-US platform local rentals retain their legacy monthly "
            "rate; new platform purchases are US-only in v1."
        ),
        category="phone_number",
        meter_type="count",
        billing_unit="month",
        default_credit_cost=200,
    ),
    SystemPricingDefinition(
        event_name="phone_number_us_local_month",
        display_name="Additional US local phone numbers",
        description=(
            "Each additional platform-provided US local phone number uses 80 "
            "credits per rental month."
        ),
        category="phone_number",
        meter_type="count",
        billing_unit="month",
        default_credit_cost=80,
    ),
    SystemPricingDefinition(
        event_name="phone_number_mobile_month",
        display_name="Existing mobile number rentals (legacy)",
        description=(
            "Legacy active mobile rentals retain their existing monthly rate. "
            "New mobile-number purchases are unavailable in v1."
        ),
        category="phone_number",
        meter_type="count",
        billing_unit="month",
        default_credit_cost=200,
    ),
    SystemPricingDefinition(
        event_name="phone_number_toll_free_month",
        display_name="Toll-free phone numbers",
        description=(
            "An active toll-free phone number uses 120 credits for each rental "
            "month. Its approximate USD equivalent depends on the credit pack."
        ),
        category="phone_number",
        meter_type="count",
        billing_unit="month",
        default_credit_cost=120,
    ),
)

SYSTEM_PRICING_EVENT_NAMES = tuple(item.event_name for item in SYSTEM_PRICING)

_PRICING_BY_NAME = {item.event_name: item for item in SYSTEM_PRICING}
_PHONE_NUMBER_EVENT_BY_TYPE = {
    PhoneNumberType.LOCAL: "phone_number_local_month",
    PhoneNumberType.MOBILE: "phone_number_mobile_month",
    PhoneNumberType.TOLL_FREE: "phone_number_toll_free_month",
}


def get_system_pricing_definition(event_name: str) -> SystemPricingDefinition:
    """Return the fixed definition for a supported event name.

    Args:
        event_name: Runtime credit-event key.

    Returns:
        The immutable system pricing definition.

    Raises:
        ValueError: If the event is not part of the supported catalog.
    """
    try:
        return _PRICING_BY_NAME[event_name]
    except KeyError as exc:
        raise ValueError(
            f"Credit event '{event_name}' must be a supported system pricing event"
        ) from exc


def get_phone_number_pricing_event_name(
    phone_type: PhoneNumberType, country_code: str = "US"
) -> str:
    """Return the monthly pricing event for a phone-number type and country."""
    if phone_type == PhoneNumberType.LOCAL:
        return (
            "phone_number_us_local_month"
            if country_code.strip().upper() == "US"
            else "phone_number_local_month"
        )
    return _PHONE_NUMBER_EVENT_BY_TYPE[phone_type]
