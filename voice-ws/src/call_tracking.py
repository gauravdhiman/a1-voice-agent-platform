"""Track voice WebSocket sessions in ``call_logs`` for concurrent call limits."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from shared.billing.voice_session_entitlement import resolve_voice_concurrency_limit
from shared.billing.voice_settlement import settle_voice_call
from shared.config import supabase_config
from shared.observability.signals import failure, observed
from shared.voice_agents.source_metadata import normalize_domain, normalize_source_url

logger = logging.getLogger(__name__)


async def renew_call_lease(call_log_id: str, session_id: str) -> bool:
    """Renew only this active session's lease; expired/final sessions cannot revive."""
    client = supabase_config.client
    if client is None:
        return False
    response = await asyncio.to_thread(
        lambda: client.rpc(
            "touch_voice_call",
            {
                "p_call_log_id": call_log_id,
                "p_session_id": session_id,
            },
        ).execute()
    )
    return response.data is True


@observed("call.start")
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
        failure("CALL_STORAGE_UNAVAILABLE")
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

    try:
        limit = await resolve_voice_concurrency_limit(client, organization_id)
        result = await asyncio.to_thread(
            lambda: client.rpc(
                "admit_voice_call",
                {
                    "p_session_id": session_id,
                    "p_call_sid": call_sid,
                    "p_organization_id": str(organization_id),
                    "p_agent_id": str(agent_id),
                    "p_concurrent_limit": limit,
                    "p_source_type": source_fields.get("source_type"),
                    "p_source_url": source_fields.get("source_url"),
                    "p_source_domain": source_fields.get("source_domain"),
                },
            ).execute()
        )
        admission = result.data or {}
        if admission.get("success") and admission.get("call_log_id"):
            return str(admission["call_log_id"])
        failure("CALL_ADMISSION_DENIED")
    except Exception:
        failure("CALL_START_FAILED")
        logger.exception("Failed to admit tracked voice session")
    return None


@observed("call.answer")
async def mark_call_answered(call_log_id: Optional[str]) -> None:
    """Mark a connected voice session as answered without overwriting a final state."""
    if not call_log_id:
        return
    client = supabase_config.client
    if client is None:
        failure("CALL_STORAGE_UNAVAILABLE")
        return

    try:
        await asyncio.to_thread(
            lambda: client.table("call_logs")
            .update(
                {
                    "status": "answered",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            .eq("id", call_log_id)
            .in_("status", ["initiated", "ringing"])
            .execute()
        )
    except Exception:
        failure("CALL_ANSWER_FAILED")
        logger.exception("Failed to mark call log id=%s as answered", call_log_id)


@observed("call.finalize")
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
        failure("CALL_STORAGE_UNAVAILABLE")
        return

    now_dt = datetime.now(timezone.utc)
    now = now_dt.isoformat()
    try:
        lookup = await asyncio.to_thread(
            lambda: client.table("call_logs")
            .select("organization_id, agent_id, started_at")
            .eq("id", call_log_id)
            .limit(1)
            .execute()
        )
        if not lookup.data:
            failure("CALL_LOG_MISSING")
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

        await asyncio.to_thread(
            lambda: client.table("call_logs")
            .update(final_update)
            .eq("id", call_log_id)
            .in_("status", ["initiated", "ringing", "answered"])
            .execute()
        )

        await _bill_completed_call(
            client,
            call_log_id=call_log_id,
            organization_id=UUID(str(row["organization_id"])),
            duration_seconds=duration_seconds,
            agent_id=row.get("agent_id"),
        )
    except Exception:
        failure("CALL_FINALIZE_FAILED")
        logger.exception("Failed to finalize call log id=%s", call_log_id)


@observed("billing.settle")
async def _bill_completed_call(
    client: object,
    *,
    call_log_id: str,
    organization_id: UUID,
    duration_seconds: int,
    agent_id: Optional[str] = None,
) -> None:
    """Attempt atomic settlement; the database retains pending work on failure.

    Compatibility parameters are retained for callers; the service-only RPC
    resolves the authoritative organization, duration and demo flag itself.
    """
    await settle_voice_call(client, call_log_id)
