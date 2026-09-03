"""Tests for security middleware: headers."""

from unittest.mock import patch

import pytest
from src.security.headers import SecurityHeadersMiddleware
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient


def homepage(request):
    return JSONResponse({"hello": "world"})


def private_page(request):
    response = JSONResponse({"private": True})
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@pytest.fixture
def test_app():
    """Create a minimal Starlette app with security headers middleware."""
    app = Starlette(routes=[Route("/", homepage), Route("/private", private_page)])
    app.add_middleware(SecurityHeadersMiddleware)
    return app


@pytest.fixture
def client(test_app):
    return TestClient(test_app)


class TestSecurityHeaders:
    """Test that security headers are present on all responses."""

    def test_x_content_type_options(self, client):
        with patch("src.security.headers.settings") as s:
            s.environment = "production"
            response = client.get("/")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"

    def test_x_frame_options(self, client):
        with patch("src.security.headers.settings") as s:
            s.environment = "production"
            response = client.get("/")
        assert response.headers.get("X-Frame-Options") == "DENY"

    def test_x_xss_protection(self, client):
        with patch("src.security.headers.settings") as s:
            s.environment = "production"
            response = client.get("/")
        assert response.headers.get("X-XSS-Protection") == "1; mode=block"

    def test_referrer_policy(self, client):
        with patch("src.security.headers.settings") as s:
            s.environment = "production"
            response = client.get("/")
        assert (
            response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
        )

    def test_route_can_set_stricter_referrer_policy(self, client):
        with patch("src.security.headers.settings") as s:
            s.environment = "production"
            response = client.get("/private")
        assert response.headers.get("Referrer-Policy") == "no-referrer"

    def test_permissions_policy(self, client):
        with patch("src.security.headers.settings") as s:
            s.environment = "production"
            response = client.get("/")
        assert "camera=()" in response.headers.get("Permissions-Policy", "")

    def test_csp_header_present(self, client):
        with patch("src.security.headers.settings") as s:
            s.environment = "production"
            response = client.get("/")
        csp = response.headers.get("Content-Security-Policy", "")
        assert "default-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp
        # connect-src should be restricted to 'self', not open to all https:
        assert "connect-src 'self'" in csp
        assert "connect-src 'self' https:*" not in csp

    def test_headers_on_all_responses(self, client):
        """Security headers must be present even on error responses."""
        with patch("src.security.headers.settings") as s:
            s.environment = "production"
            response = client.get("/nonexistent")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"

    def test_hsts_present_in_production(self, client):
        """HSTS header must be set in production."""
        with patch("src.security.headers.settings") as s:
            s.environment = "production"
            response = client.get("/")
        assert "Strict-Transport-Security" in response.headers

    def test_hsts_absent_in_development(self, client):
        """HSTS header must NOT be set in development (breaks local HTTP)."""
        with patch("src.security.headers.settings") as s:
            s.environment = "development"
            response = client.get("/")
        assert "Strict-Transport-Security" not in response.headers

    def test_csp_allows_cdn_in_debug_mode(self, client):
        """CSP must allow cdn.jsdelivr.net and unsafe-inline in debug mode for Swagger UI."""
        with patch("src.security.headers.settings") as s:
            s.environment = "development"
            s.debug = True
            response = client.get("/")
        csp = response.headers.get("Content-Security-Policy", "")
        assert "'unsafe-inline'" in csp
        assert "https://cdn.jsdelivr.net" in csp
        assert "connect-src 'self' https://cdn.jsdelivr.net" in csp

    def test_csp_no_cdn_in_production(self, client):
        """CSP must NOT allow cdn.jsdelivr.net when debug is off."""
        with patch("src.security.headers.settings") as s:
            s.environment = "production"
            s.debug = False
            response = client.get("/")
        csp = response.headers.get("Content-Security-Policy", "")
        assert "cdn.jsdelivr.net" not in csp
