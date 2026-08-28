"""
Voice session entitlement pre-checks shared by the voice-ws worker.

Resolves plan-version entitlements from Supabase (same binding rules as backend
``EntitlementService``) and enforces concurrent call limits plus minimum credit
headroom before a WebSocket session starts.

New sessions are prepaid-admitted: the pre-check passes when the combined
balance (plan credits + platform-granted credits + purchased credits) covers at
least one billable voice minute. An admitted session may finish below zero; the
final settlement still charges its complete rounded duration and blocks the
next session until credits are restored.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional
from uuid import UUID, uuid4

from shared.billing.call_status import ACTIVE_VOICE_CALL_STATUSES
from shared.config import supabase_config

logger = logging.getLogger(__name__)

FREE_PLAN_PRODUCT_SLUG = "free"
ACTIVE_SUBSCRIPTION_STATUSES = frozenset({"active", "trial"})
DEFAULT_VOICE_MINUTE_EVENT = "voice_call_minute"
DEMO_UNLIMITED = -1
DEMO_CALL_LIMIT_REACHED = "DEMO_CALL_LIMIT_REACHED"
DEMO_CALL_RESERVATION_UNAVAILABLE = "DEMO_CALL_RESERVATION_UNAVAILABLE"
DEMO_CALL_RESERVATION_INVALID = "DEMO_CALL_RESERVATION_INVALID"
DEMO_CALL_ALREADY_USED = "DEMO_CALL_ALREADY_USED"
DEMO_CALL_LIMIT_MESSAGE = (
    "This demo agent has used all available trial calls. Please contact the "
    "platform administrator for further details or to have the demo re-enabled."
)


@dataclass(frozen=True)
class DemoCallReservation:
    """Atomic reservation returned when a demo call budget is claimed.

    ``calls_remaining`` is the post-reservation value. A value of ``-1`` means
    the platform administrator configured unlimited demo calls. The duration is
    captured in the signed voice-session token so changing an agent's settings
    affects new reservations without changing an active call.
    """

    reservation_id: str
    session_id: str
    calls_remaining: int
    max_call_duration_seconds: int


def _coerce_demo_limit(raw: Any, *, default: int = DEMO_UNLIMITED) -> int:
    """Convert a database/API value to a safe demo-limit integer."""
    if raw is None or isinstance(raw, bool):
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _parse_reserved_demo_limit(raw: Any, *, duration: bool = False) -> int:
    """Parse an RPC limit response and reject malformed values closed."""
    if raw is None or isinstance(raw, bool):
        raise ValueError("missing demo limit")
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid demo limit") from exc
    if value < DEMO_UNLIMITED or (duration and value != DEMO_UNLIMITED and value <= 0):
        raise ValueError("invalid demo limit")
    return value


def is_demo_agent(agent: object) -> bool:
    """Return whether an agent explicitly has the demo flag enabled."""
    return getattr(agent, "is_demo", False) is True


class VoiceSessionEntitlementError(Exception):
    """Raised when a voice session cannot start due to plan limits."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _parse_entitlement_value(raw: Optional[dict[str, Any]]) -> tuple[Any, bool]:
    if not raw:
        return None, False
    value_type = raw.get("type")
    if value_type == "unlimited":
        return None, True
    if value_type == "integer":
        return raw.get("value"), False
    if value_type == "boolean":
        return bool(raw.get("value")), False
    return raw.get("value"), False


def assert_demo_call_available(agent: object) -> None:
    """Raise when a demo agent has no calls left in its configured budget.

    This is a fast response-layer check used to give public callers an
    immediate, stable error. The database reservation RPC remains the source
    of truth for the race-safe decrement at token issuance.

    Args:
        agent: Agent-like object with ``is_demo`` and
            ``demo_calls_remaining`` attributes.

    Raises:
        VoiceSessionEntitlementError: If the demo budget is exhausted.
    """
    if not is_demo_agent(agent):
        return
    remaining = _coerce_demo_limit(getattr(agent, "demo_calls_remaining", None))
    if remaining == 0:
        raise VoiceSessionEntitlementError(
            DEMO_CALL_LIMIT_REACHED,
            DEMO_CALL_LIMIT_MESSAGE,
        )


async def reserve_demo_call_slot(
    agent_id: UUID,
    *,
    session_id: Optional[str] = None,
) -> DemoCallReservation:
    """Atomically reserve one demo call and return its signed-session inputs.

    The Postgres function locks the agent row while checking and decrementing
    ``demo_calls_remaining``. Unlimited budgets (``-1``) are left unchanged.
    The reservation is persisted against the generated session id so
    ``voice-ws`` can consume it exactly once.

    Args:
        agent_id: Demo agent whose call budget should be reserved.
        session_id: Optional pre-generated session id for idempotent retries.

    Returns:
        A reservation containing the remaining budget and duration cap.

    Raises:
        VoiceSessionEntitlementError: If the budget is exhausted or the
            reservation service cannot be reached.
    """
    client = supabase_config.client
    if client is None:
        raise VoiceSessionEntitlementError(
            DEMO_CALL_RESERVATION_UNAVAILABLE,
            "Demo call availability could not be verified.",
        )

    resolved_session_id = session_id or str(uuid4())
    try:
        result = client.rpc(
            "reserve_demo_voice_call",
            {
                "p_agent_id": str(agent_id),
                "p_session_id": resolved_session_id,
            },
        ).execute()
    except Exception as exc:  # noqa: BLE001 - convert provider failure safely
        logger.exception("Failed to reserve demo call agent_id=%s", agent_id)
        raise VoiceSessionEntitlementError(
            DEMO_CALL_RESERVATION_UNAVAILABLE,
            "Demo call availability could not be verified.",
        ) from exc

    raw_data = getattr(result, "data", None)
    row = raw_data[0] if isinstance(raw_data, list) and raw_data else raw_data
    if not isinstance(row, dict) or not row.get("success"):
        error = row.get("error") if isinstance(row, dict) else None
        if error == "demo_call_limit_reached":
            raise VoiceSessionEntitlementError(
                DEMO_CALL_LIMIT_REACHED,
                DEMO_CALL_LIMIT_MESSAGE,
            )
        raise VoiceSessionEntitlementError(
            DEMO_CALL_RESERVATION_UNAVAILABLE,
            "Demo call availability could not be verified.",
        )

    reservation_id = row.get("reservation_id")
    if not isinstance(reservation_id, str) or not reservation_id:
        raise VoiceSessionEntitlementError(
            DEMO_CALL_RESERVATION_UNAVAILABLE,
            "Demo call availability could not be verified.",
        )

    try:
        calls_remaining = _parse_reserved_demo_limit(row.get("calls_remaining"))
        max_call_duration_seconds = _parse_reserved_demo_limit(
            row.get("max_call_duration_seconds"), duration=True
        )
    except ValueError as exc:
        raise VoiceSessionEntitlementError(
            DEMO_CALL_RESERVATION_UNAVAILABLE,
            "Demo call availability could not be verified.",
        ) from exc

    return DemoCallReservation(
        reservation_id=reservation_id,
        session_id=resolved_session_id,
        calls_remaining=calls_remaining,
        max_call_duration_seconds=max_call_duration_seconds,
    )


async def reserve_demo_call_if_needed(
    agent: object,
) -> Optional[DemoCallReservation]:
    """Reserve a call when ``agent`` is a demo agent; otherwise do nothing."""
    if not is_demo_agent(agent):
        return None
    assert_demo_call_available(agent)
    return await reserve_demo_call_slot(UUID(str(agent.id)))


async def consume_demo_call_reservation(
    *,
    agent_id: UUID,
    session_id: str,
    reservation_id: str,
) -> None:
    """Consume a demo reservation exactly once at WebSocket admission.

    A signed token alone is not treated as proof that the reservation is new:
    the row transition from ``reserved`` to ``consumed`` is atomic, so replaying
    the same token cannot open another voice session.
    """
    client = supabase_config.client
    if client is None:
        raise VoiceSessionEntitlementError(
            DEMO_CALL_RESERVATION_UNAVAILABLE,
            "Demo call availability could not be verified.",
        )

    try:
        result = client.rpc(
            "consume_demo_voice_call",
            {
                "p_agent_id": str(agent_id),
                "p_session_id": session_id,
                "p_reservation_id": reservation_id,
            },
        ).execute()
    except Exception as exc:  # noqa: BLE001 - convert provider failure safely
        logger.exception(
            "Failed to consume demo call reservation agent_id=%s session_id=%s",
            agent_id,
            session_id,
        )
        raise VoiceSessionEntitlementError(
            DEMO_CALL_RESERVATION_UNAVAILABLE,
            "Demo call availability could not be verified.",
        ) from exc

    raw_data = getattr(result, "data", None)
    row = raw_data[0] if isinstance(raw_data, list) and raw_data else raw_data
    if isinstance(row, dict) and row.get("success"):
        return

    error = row.get("error") if isinstance(row, dict) else None
    if error == "demo_call_already_used":
        raise VoiceSessionEntitlementError(
            DEMO_CALL_ALREADY_USED,
            "This demo call session has already been used.",
        )
    raise VoiceSessionEntitlementError(
        DEMO_CALL_RESERVATION_INVALID,
        "This demo call session is no longer available.",
    )


async def assert_voice_session_allowed(
    organization_id: UUID,
    *,
    min_event_name: str = DEFAULT_VOICE_MINUTE_EVENT,
    current_call_sid: Optional[str] = None,
    agent_is_demo: bool = False,
) -> None:
    """Raise ``VoiceSessionEntitlementError`` if the org cannot start a call.

    Checks:
    - ``max_concurrent_calls`` against active ``call_logs`` rows
    - Combined credit balance (plan + purchased) for at least one billable
      voice minute. An active call is allowed to complete and settle in full.

    Demo agents (``voice_agents.is_demo = true``) bypass both checks so
    showcase calls never block on billing. The caller should pass
    ``agent_is_demo=True`` when the session is for a demo agent; the check
    is best-effort and remains platform-admin-gated at the API layer.

    Args:
        organization_id: Tenant owning the voice agent.
        min_event_name: Credit event used to estimate minimum session cost.
        current_call_sid: Optional provider call identifier for a PSTN call
            already persisted by the backend webhook. That row is excluded
            from the active count before admitting the same call.
        agent_is_demo: When true, bypass credit and concurrency checks for
            this session (demo agent showcase).

    Raises:
        VoiceSessionEntitlementError: When concurrent or credit pre-check fails.
    """
    client = supabase_config.client
    if client is None:
        logger.warning("Supabase unavailable — skipping voice entitlement pre-check")
        return

    if agent_is_demo:
        logger.info(
            "Voice session allowed for demo agent organization_id=%s (bypass)",
            organization_id,
        )
        return

    entitlements = await _resolve_org_entitlements(client, organization_id)
    concurrent = entitlements["limits"].get("max_concurrent_calls")
    if concurrent is not None:
        effective, is_unlimited = _parse_entitlement_value(concurrent)
        if not is_unlimited:
            limit = int(effective or 0)
            active = await _count_active_calls(
                client,
                organization_id,
                current_call_sid=current_call_sid,
            )
            if active + 1 > limit:
                raise VoiceSessionEntitlementError(
                    "MAX_CONCURRENT_CALLS",
                    f"Your plan allows {limit} concurrent call(s). "
                    f"You currently have {active} active.",
                )

    min_cost = await _minimum_voice_credit_cost(client, min_event_name)
    if min_cost <= 0:
        return

    balance = await _get_credit_balance(client, organization_id)
    allowed, message = _evaluate_credit_headroom(balance, min_cost)
    if not allowed:
        raise VoiceSessionEntitlementError(
            "INSUFFICIENT_CREDITS",
            message or "Insufficient credits to start a voice call.",
        )


async def _resolve_org_entitlements(
    client: Any, organization_id: UUID
) -> dict[str, dict[str, Any]]:
    """Return sparse limits/features maps keyed by entitlement key."""
    sub_result = (
        client.table("organization_subscriptions")
        .select("status, plan_version_id")
        .eq("organization_id", str(organization_id))
        .limit(1)
        .execute()
    )
    plan_version_id: Optional[str] = None
    if (
        sub_result.data
        and sub_result.data[0].get("status") in ACTIVE_SUBSCRIPTION_STATUSES
    ):
        plan_version_id = sub_result.data[0].get("plan_version_id")

    if not plan_version_id:
        free_result = (
            client.table("plan_versions")
            .select("id, plan_products!inner(slug)")
            .eq("plan_products.slug", FREE_PLAN_PRODUCT_SLUG)
            .eq("is_current_for_signup", True)
            .eq("status", "published")
            .order("version_number", desc=True)
            .limit(1)
            .execute()
        )
        if not free_result.data:
            return {"limits": {}, "features": {}}
        plan_version_id = free_result.data[0]["id"]

    assigned_result = (
        client.table("plan_version_entitlements")
        .select("entitlement_key, value")
        .eq("plan_version_id", str(plan_version_id))
        .execute()
    )
    catalog_result = (
        client.table("entitlement_definitions")
        .select("key, kind, default_when_absent")
        .eq("is_active", True)
        .execute()
    )
    assigned_by_key = {
        row["entitlement_key"]: row["value"] for row in (assigned_result.data or [])
    }
    limits: dict[str, Any] = {}
    features: dict[str, Any] = {}
    for row in catalog_result.data or []:
        key = row["key"]
        raw = assigned_by_key.get(key)
        if raw is None:
            raw = row.get("default_when_absent")
        if row["kind"] == "limit":
            limits[key] = raw
        else:
            effective, _ = _parse_entitlement_value(raw)
            features[key] = effective
    return {"limits": limits, "features": features}


async def _count_active_calls(
    client: Any,
    organization_id: UUID,
    *,
    current_call_sid: Optional[str] = None,
) -> int:
    result = (
        client.table("call_logs")
        .select("id, call_sid", count="exact")
        .eq("organization_id", str(organization_id))
        .in_("status", sorted(ACTIVE_VOICE_CALL_STATUSES))
        .execute()
    )
    if current_call_sid is not None:
        return sum(
            1 for row in (result.data or []) if row.get("call_sid") != current_call_sid
        )
    count = getattr(result, "count", None)
    if isinstance(count, int):
        return count
    return len(result.data or [])


async def _get_credit_balance(client: Any, organization_id: UUID) -> int:
    """Return combined prepaid balance across all credit pools."""
    result = (
        client.table("organizations")
        .select("credit_balance, admin_credit_balance, purchased_credit_balance")
        .eq("id", str(organization_id))
        .limit(1)
        .execute()
    )
    if not result.data:
        return 0
    plan_credits = int(result.data[0].get("credit_balance") or 0)
    admin_credits = int(result.data[0].get("admin_credit_balance") or 0)
    purchased_credits = int(result.data[0].get("purchased_credit_balance") or 0)
    return plan_credits + admin_credits + purchased_credits


async def _minimum_voice_credit_cost(client: Any, event_name: str) -> int:
    result = (
        client.table("credit_events")
        .select("credit_cost")
        .eq("name", event_name)
        .eq("is_active", True)
        .limit(1)
        .execute()
    )
    if not result.data:
        return 0
    return int(result.data[0].get("credit_cost") or 0)


def _evaluate_credit_headroom(
    balance: int,
    credits_needed: int,
) -> tuple[bool, Optional[str]]:
    """Evaluate whether the prepaid balance covers ``credits_needed``.

    No pay-as-you-go: consumption never goes below zero, so the check is a
    plain balance comparison.

    Args:
        balance: Combined prepaid balance (plan + purchased credits).
        credits_needed: Credits required to start the session.

    Returns:
        Tuple of (allowed, message). ``allowed`` is True when
        ``balance >= credits_needed``, else False with a denial message.
    """
    if balance >= credits_needed:
        return True, None
    return False, "Insufficient credits to start a voice call."
