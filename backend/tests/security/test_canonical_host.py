"""Tests for CanonicalHostMiddleware (block *.run.app in production)."""

from unittest.mock import patch

import pytest
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from src.security.canonical_host import CanonicalHostMiddleware


def homepage(request):
    return JSONResponse({"ok": True})


def health(request):
    return JSONResponse({"status": "healthy"})


@pytest.fixture
def client():
    app = Starlette(
        routes=[
            Route("/", homepage),
            Route("/health", health),
            Route("/api/v1/organizations/", homepage),
        ]
    )
    app.add_middleware(CanonicalHostMiddleware)
    return TestClient(app)


class TestCanonicalHostMiddleware:
    def test_allows_custom_domain_in_production(self, client):
        with patch("src.security.canonical_host.settings") as s:
            s.environment = "production"
            response = client.get(
                "/api/v1/organizations/",
                headers={"Host": "api.247ai.live"},
            )
        assert response.status_code == 200

    def test_blocks_run_app_host_in_production(self, client):
        with patch("src.security.canonical_host.settings") as s:
            s.environment = "production"
            response = client.get(
                "/api/v1/organizations/",
                headers={"Host": "backend-247ai-xxxxx.us-central1.run.app"},
            )
        assert response.status_code == 403
        assert "api.247ai.live" in response.json()["detail"]

    def test_allows_health_on_run_app_host(self, client):
        with patch("src.security.canonical_host.settings") as s:
            s.environment = "production"
            response = client.get(
                "/health",
                headers={"Host": "backend-247ai-xxxxx.us-central1.run.app"},
            )
        assert response.status_code == 200

    def test_allows_run_app_in_development(self, client):
        with patch("src.security.canonical_host.settings") as s:
            s.environment = "development"
            response = client.get(
                "/",
                headers={"Host": "something.run.app"},
            )
        assert response.status_code == 200
