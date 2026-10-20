"""A stalled payment provider must not stall the request event loop."""

import asyncio
import threading
from types import SimpleNamespace

import pytest
from src.billing.stripe_service import StripeService, stripe


@pytest.mark.asyncio
async def test_stripe_network_work_runs_off_event_loop(monkeypatch):
    loop_thread = threading.get_ident()
    entered = threading.Event()
    release = threading.Event()
    provider_threads = []

    def blocked_provider(**kwargs):
        provider_threads.append(threading.get_ident())
        entered.set()
        assert release.wait(2)
        return SimpleNamespace(id="customer-test")

    monkeypatch.setattr(stripe.Customer, "create", blocked_provider)
    task = asyncio.create_task(
        StripeService().create_customer("test@example.test", "Fixture", "org-test")
    )
    try:
        assert await asyncio.to_thread(entered.wait, 1)
        assert provider_threads == [provider_threads[0]]
        assert provider_threads[0] != loop_thread
    finally:
        release.set()
    assert (await task).id == "customer-test"
