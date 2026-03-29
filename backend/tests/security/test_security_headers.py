"""Tests for security middleware: headers and rate limiting."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from starlette.testclient import TestClient
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import JSONResponse

from src.security.headers import SecurityHeadersMiddleware


def homepage(request):
    return JSONResponse({"hello": "world"})


@pytest.fixture
def test_app():
    """Create a minimal Starlette app with security headers middleware."""
    app = Starlette(routes=[Route("/", homepage)])
    app.add_middleware(SecurityHeadersMiddleware)
    return app


@pytest.fixture
def client(test_app):
    return TestClient(test_app)


class TestSecurityHeaders:
    """Test that security headers are present on all responses."""

    def test_x_content_type_options(self, client):
        response = client.get("/")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"

    def test_x_frame_options(self, client):
        response = client.get("/")
        assert response.headers.get("X-Frame-Options") == "DENY"

    def test_x_xss_protection(self, client):
        response = client.get("/")
        assert response.headers.get("X-XSS-Protection") == "1; mode=block"

    def test_referrer_policy(self, client):
        response = client.get("/")
        assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    def test_permissions_policy(self, client):
        response = client.get("/")
        assert "camera=()" in response.headers.get("Permissions-Policy", "")

    def test_csp_header_present(self, client):
        response = client.get("/")
        csp = response.headers.get("Content-Security-Policy", "")
        assert "default-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp

    def test_headers_on_all_responses(self, client):
        """Security headers must be present even on error responses."""
        response = client.get("/nonexistent")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
