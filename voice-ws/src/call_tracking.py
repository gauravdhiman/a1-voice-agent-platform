"""Track voice WebSocket sessions in ``call_logs`` for concurrent call limits."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from shared.billing.voice_call_metering import (
    DEFAULT_VOICE_CALL_EVENT,
    calculate_voice_call_credits,
)
from shared.config import supabase_config
from shared.voice_agents.source_metadata import normalize_domain, normalize_source_url

logger = logging.getLogger(__name__)


async def start_call_tracking(
    *,
    session_id: str,
    call_sid: Optional[str] = None,
    organization_id: UUID,
    agent_id: UUID,
    source_type: Optional[str] = None,
    source_url: Optional[str] = None,
    source_domain: Optional[str] = None,
) -> Optional[str]:
    """Insert an active call log row for a voice session.

    Args:
        session_id: Voice session identifier (stored as ``call_sid``).
        call_sid: Optional provider call identifier. For Twilio, reuse the
            backend-created row keyed by this value instead of inserting a
            second active row for the same call.
        organization_id: Owning organization UUID.
        agent_id: Voice agent UUID.
        source_type: Stable call-log source type from the signed session token.
        source_url: Sanitized web page URL from the signed session token.
        source_domain: Sanitized web source hostname from the signed session token.

    Returns:
        Call log row id string, or None if tracking could not be persisted.
    """
    client = supabase_config.client
    if client is None:
        return None

    normalized_source_url = normalize_source_url(source_url)
    normalized_source_domain = normalize_domain(source_domain or normalized_source_url)
    source_fields = {
        key: value
        for key, value in {
            "source_type": source_type,
            "source_url": normalized_source_url,
            "source_domain": normalized_source_domain,
        }.items()
        if value is not None
    }

    if call_sid:
        try:
            existing = (
                client.table("call_logs")
                .select("id")
                .eq("call_sid", call_sid)
                .limit(1)
                .execute()
            )
            if existing.data:
                existing_id = str(existing.data[0]["id"])
                if source_fields:
                    client.table("call_logs").update(source_fields).eq(
                        "id", existing_id
                    ).execute()
                return existing_id
        except Exception:
            logger.exception(
                "Failed to find existing call log for provider call_sid=%s",
                call_sid,
            )

    now = datetime.now(timezone.utc).isoformat()
    row = {
        "call_sid": call_sid or session_id,
        "organization_id": str(organization_id),
        "agent_id": str(agent_id),
        "status": "initiated",
        "duration": 0,
        "started_at": now,
        "created_at": now,
        "updated_at": now,
    }
    row.update(source_fields)
    try:
        result = client.table("call_logs").insert(row).execute()
        if result.data:
            return str(result.data[0]["id"])
    except Exception:
        logger.exception(
            "Failed to create call log for session_id=%s org=%s",
            session_id,
            organization_id,
        )
    return None


async def mark_call_answered(call_log_id: Optional[str]) -> None:
    """Mark a connected voice session as answered without overwriting a final state."""
    if not call_log_id:
        return
    client = supabase_config.client
    if client is None:
        return

    try:
        client.table("call_logs").update(
            {
                "status": "answered",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", call_log_id).in_("status", ["initiated", "ringing"]).execute()
    except Exception:
        logger.exception("Failed to mark call log id=%s as answered", call_log_id)


async def end_call_tracking(
    call_log_id: Optional[str],
    *,
    status: str = "completed",
    failure_code: Optional[str] = None,
    failure_message: Optional[str] = None,
) -> None:
    """Mark a tracked call log row as finished.

    ``failure_code`` and ``failure_message`` are safe, bounded classifications
    produced by the voice runtime. Raw provider exceptions must never be sent
    to this persistence boundary.
    """
    if not call_log_id:
        return
    client = supabase_config.client
    if client is None:
        return

    now_dt = datetime.now(timezone.utc)
    now = now_dt.isoformat()
    try:
        lookup = (
            client.table("call_logs")
            .select("organization_id, agent_id, started_at")
            .eq("id", call_log_id)
            .limit(1)
            .execute()
        )
        if not lookup.data:
            logger.warning(
                "Call log id=%s disappeared before finalization", call_log_id
            )
            return

        row = lookup.data[0]
        started_at = row.get("started_at")
        if isinstance(started_at, str):
            started_at = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        duration_seconds = max(
            0,
            (
                int((now_dt - started_at).total_seconds())
                if isinstance(started_at, datetime)
                else 0
            ),
        )
        final_update = {
            "status": status,
            "duration": duration_seconds,
            "ended_at": now,
            "updated_at": now,
        }
        if failure_code:
            final_update["failure_code"] = failure_code[:100]
            final_update["failure_message"] = (failure_message or "")[:1000]

        client.table("call_logs").update(final_update).eq("id", call_log_id).execute()

        await _bill_completed_call(
            client,
            call_log_id=call_log_id,
            organization_id=UUID(str(row["organization_id"])),
            duration_seconds=duration_seconds,
            agent_id=row.get("agent_id"),
        )
    except Exception:
        logger.exception("Failed to finalize call log id=%s", call_log_id)


async def _bill_completed_call(
    client: object,
    *,
    call_log_id: str,
    organization_id: UUID,
    duration_seconds: int,
    agent_id: Optional[str] = None,
) -> None:
    """Debit voice minutes and attach the ledger row to a completed call.

    Billing is best-effort during websocket teardown: a ledger failure is
    logged, but it must not keep the worker from closing the call cleanly.
    The atomic RPC still prevents concurrent sessions from overspending.

    Demo agents (``voice_agents.is_demo = true``) are not billed:
    the call is recorded with ``credits_consumed=0`` and no ledger row.
    """
    try:
        # Demo-agent fast-path: no debit, just mark zero consumption.
        if agent_id:
            try:
                demo_result = (
                    client.table("voice_agents")
                    .select("is_demo")
                    .eq("id", str(agent_id))
                    .limit(1)
                    .execute()
                )
                if demo_result.data and bool(demo_result.data[0].get("is_demo")):
                    logger.info(
                        "Skipping billing for demo agent agent_id=%s call_id=%s",
                        agent_id,
                        call_log_id,
                    )
                    client.table("call_logs").update({"credits_consumed": 0}).eq(
                        "id", call_log_id
                    ).execute()
                    return
            except Exception:
                logger.debug(
                    "Demo-agent check failed for agent_id=%s — proceeding to normal billing",
                    agent_id,
                    exc_info=True,
                )

        event_result = (
            client.table("credit_events")
            .select("id, credit_cost")
            .eq("name", DEFAULT_VOICE_CALL_EVENT)
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
        if not event_result.data:
            logger.error("Missing active credit event %s", DEFAULT_VOICE_CALL_EVENT)
            return

        event = event_result.data[0]
        credits_needed = calculate_voice_call_credits(
            duration_seconds, int(event.get("credit_cost") or 0)
        )
        if credits_needed == 0:
            client.table("call_logs").update({"credits_consumed": 0}).eq(
                "id", call_log_id
            ).execute()
            return

        debit_result = client.rpc(
            "consume_voice_call_credits",
            {
                "p_organization_id": str(organization_id),
                "p_credit_event_id": str(event["id"]),
                "p_credits_needed": credits_needed,
                "p_call_log_id": call_log_id,
                "p_duration_seconds": duration_seconds,
            },
        ).execute()
        debit = debit_result.data or {}
        if not debit.get("success"):
            logger.warning(
                "Call %s completed without credit headroom (needed=%s)",
                call_log_id,
                credits_needed,
            )
            return

        if int(debit.get("overdraft_used") or 0) > 0:
            logger.warning(
                "Call %s settled %s credits below zero; new calls will be blocked",
                call_log_id,
                debit["overdraft_used"],
            )

        transaction_id = debit.get("transaction_id")
        if not transaction_id:
            logger.error("Credit debit for call %s had no ledger row", call_log_id)
            return

        client.table("call_logs").update(
            {
                "credits_consumed": credits_needed,
                "credit_transaction_id": transaction_id,
            }
        ).eq("id", call_log_id).execute()
    except Exception:
        logger.exception("Failed to bill completed call id=%s", call_log_id)
