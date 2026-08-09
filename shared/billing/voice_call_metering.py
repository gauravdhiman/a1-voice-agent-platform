"""Pure helpers for translating voice-call duration into credit usage."""

from __future__ import annotations

import math

DEFAULT_VOICE_CALL_EVENT = "voice_call_minute"


def billable_voice_minutes(duration_seconds: int) -> int:
    """Return prepaid billable minutes for a completed call.

    Calls have a one-minute minimum so a connected call cannot bypass the
    prepaid entitlement with a short duration. Non-positive durations are
    treated as one billable minute because a tracked session reached the
    connected voice pipeline.
    """
    return max(1, math.ceil(max(0, duration_seconds) / 60))


def calculate_voice_call_credits(duration_seconds: int, credit_cost: int) -> int:
    """Calculate total credits for a call at the configured per-minute cost.

    Args:
        duration_seconds: Completed call duration in seconds.
        credit_cost: Credit event cost for one voice minute.

    Returns:
        Total credits to debit from the organization's prepaid balance.

    Raises:
        ValueError: If ``credit_cost`` is negative.
    """
    if credit_cost < 0:
        raise ValueError("credit_cost cannot be negative")
    return billable_voice_minutes(duration_seconds) * credit_cost
