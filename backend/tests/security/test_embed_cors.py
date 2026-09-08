"""Tests for cross-origin public embed requests."""

from fastapi import FastAPI, Response
from starlette.testclient import TestClient

from src.security.embed_cors import EmbedAwareCORSMiddleware


EMBED_TOKEN_PATH = "/api/v1/embed/agent/agent-id/token"


def _create_test_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        EmbedAwareCORSMiddleware,
        allow_origins=["http://localhost:3150"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.post(EMBED_TOKEN_PATH)
    async def token() -> dict[str, str]:
        return {"token": "test-token"}

    @app.options(EMBED_TOKEN_PATH)
    async def token_options() -> Response:
        return Response(status_code=200)

    @app.get("/api/v1/private")
    async def private_endpoint() -> dict[str, bool]:
        return {"ok": True}

    return app


def test_embed_token_allows_external_origin_before_global_cors_filter() -> None:
    """Embed token responses are readable from a configured customer page."""
    with TestClient(_create_test_app()) as client:
        response = client.post(
            EMBED_TOKEN_PATH, headers={"Origin": "http://localhost:3250"}
        )

    assert response.status_code == 200
    assert response.json() == {"token": "test-token"}
    assert response.headers["access-control-allow-origin"] == "http://localhost:3250"
    assert response.headers["vary"] == "Origin"


def test_embed_token_preflight_allows_external_origin() -> None:
    """The explicit embed OPTIONS route can complete browser preflight."""
    with TestClient(_create_test_app()) as client:
        response = client.options(
            EMBED_TOKEN_PATH,
            headers={
                "Origin": "http://localhost:3250",
                "Access-Control-Request-Method": "POST",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3250"
    assert response.headers["access-control-allow-methods"] == "GET, POST, OPTIONS"


def test_non_embed_endpoint_keeps_configured_cors_policy() -> None:
    """Only public embed endpoints bypass the application CORS allowlist."""
    with TestClient(_create_test_app()) as client:
        response = client.get(
            "/api/v1/private", headers={"Origin": "http://localhost:3250"}
        )

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
