"""Recover terminal voice usage that could not settle during WebSocket teardown."""

import asyncio

from shared.billing.voice_settlement import settle_voice_call
from shared.config import supabase_config


async def retry_pending_voice_settlements() -> int:
    """Retry at most 100 calls; database locks prevent duplicate concurrent debits."""
    client = supabase_config.service_client
    await asyncio.to_thread(
        lambda: client.rpc(
            "reconcile_expired_voice_calls", {"p_organization_id": None}
        ).execute()
    )
    response = await asyncio.to_thread(
        lambda: client.table("call_logs")
        .select("id")
        .eq("billing_status", "pending")
        .in_("status", ["completed", "failed"])
        .order("ended_at")
        .limit(100)
        .execute()
    )
    settled = 0
    for row in response.data or []:
        settled += int(await settle_voice_call(client, str(row["id"])))
    return settled
