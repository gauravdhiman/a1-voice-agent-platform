"""Tests for Google OAuth redirect routes."""

from unittest.mock import patch

import pytest
from starlette.requests import Request


def _request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/auth/google",
            "headers": [],
            "query_string": b"",
            "server": ("testserver", 8000),
            "client": ("testclient", 50000),
            "scheme": "http",
        }
    )


@pytest.mark.asyncio
async def test_google_authorize_redirects_to_provider() -> None:
    from src.auth.routes import google_authorize

    with patch("src.auth.routes.google_oauth_service") as service:
        service.create_authorization_url.return_value = (
            "https://accounts.google.com/o/oauth2/v2/auth?state=signed",
            "signed",
        )

        response = await google_authorize(request=_request())

    assert response.status_code == 302
    assert response.headers["location"].startswith("https://accounts.google.com/")
