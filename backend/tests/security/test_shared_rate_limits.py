"""Separate backend instances must share the configured Redis quota."""

import os
from urllib.parse import urlsplit
from uuid import uuid4

import pytest
from limits import parse
from limits.storage import MemoryStorage
from src.security import rate_limiter


def test_local_limiter_uses_memory_without_redis(monkeypatch):
    monkeypatch.setattr(rate_limiter.settings, "redis_url", None)
    limiter = rate_limiter.build_rate_limiter()
    assert isinstance(limiter._storage, MemoryStorage)
    assert limiter._in_memory_fallback_enabled is False
    assert limiter._swallow_errors is False


def test_two_instances_share_redis_budget(monkeypatch):
    url = os.getenv("RATE_LIMIT_TEST_REDIS_URL")
    if not url:
        pytest.skip("RATE_LIMIT_TEST_REDIS_URL must select disposable loopback Redis")
    if urlsplit(url).hostname not in {"127.0.0.1", "localhost", "::1"}:
        pytest.fail("Rate-limit mutation tests refuse remote Redis")
    monkeypatch.setattr(rate_limiter.settings, "redis_url", url)
    first = rate_limiter.build_rate_limiter()
    second = rate_limiter.build_rate_limiter()
    scope = f"readiness-test/{uuid4()}"
    limit = parse("2/minute")
    try:
        assert first._limiter.hit(limit, scope)
        assert second._limiter.hit(limit, scope)
        assert not first._limiter.hit(limit, scope)
        assert not second._limiter.hit(limit, scope)
    finally:
        # Clear only this test's exact key, never another limiter's database.
        first._storage.clear(limit.key_for(scope))
