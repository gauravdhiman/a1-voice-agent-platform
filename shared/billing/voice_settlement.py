"""Atomic voice settlement with a durable pending marker on the call row."""

import asyncio

from shared.observability.signals import failure, observed


@observed("billing.settle")
async def settle_voice_call(client: object, call_log_id: str) -> bool:
    """Settle once through the service-only RPC; failures remain pending for retry.

    The database owns price calculation, demo exemption, ledger idempotency and
    call linkage in one transaction. False never means usage was discarded.
    """
    try:
        response = await asyncio.to_thread(
            lambda: client.rpc(
                "settle_voice_call", {"p_call_log_id": call_log_id}
            ).execute()
        )
        if isinstance(response.data, dict) and response.data.get("success") is True:
            return True
    except Exception:
        pass
    failure("BILLING_SETTLEMENT_PENDING")
    return False
