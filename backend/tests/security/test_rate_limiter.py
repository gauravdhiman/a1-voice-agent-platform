"""Tests for rate limiting configuration."""

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from src.security.rate_limiter import limiter, rate_limit_handler


@pytest.fixture
def rate_limited_app():
    """Create a FastAPI app with rate limiting for testing."""
    app = FastAPI()
    test_limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = test_limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
    app.add_middleware(SlowAPIMiddleware)

    @app.get("/limited")
    @test_limiter.limit("2/minute")
    async def limited_endpoint(request: Request):
        return {"ok": True}

    return app


class TestRateLimiter:
    """Test rate limiting behavior."""

    def test_within_limit_returns_200(self, rate_limited_app):
        client = TestClient(rate_limited_app)
        response = client.get("/limited")
        assert response.status_code == 200

    def test_exceeding_limit_returns_429(self, rate_limited_app):
        client = TestClient(rate_limited_app)
        # Make 2 requests (within limit)
        client.get("/limited")
        client.get("/limited")
        # 3rd request exceeds the 2/minute limit
        response = client.get("/limited")
        assert response.status_code == 429

    def test_429_response_has_retry_after_header(self, rate_limited_app):
        client = TestClient(rate_limited_app)
        client.get("/limited")
        client.get("/limited")
        response = client.get("/limited")
        assert response.status_code == 429
        assert "Retry-After" in response.headers

    def test_429_response_body(self, rate_limited_app):
        client = TestClient(rate_limited_app)
        client.get("/limited")
        client.get("/limited")
        response = client.get("/limited")
        data = response.json()
        assert data["error"] == "rate_limit_exceeded"
        assert "message" in data

    def test_limiter_default_limits_configured(self):
        """Confirm the shared limiter has a default global limit."""
        assert limiter._default_limits
