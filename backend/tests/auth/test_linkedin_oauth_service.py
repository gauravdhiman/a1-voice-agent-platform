"""Tests for the direct LinkedIn OAuth broker."""

from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import pytest
from src.auth.linkedin_oauth import (
    LinkedInOAuthConfigurationError,
    LinkedInOAuthService,
)


class FakeResponse:
    """Minimal async HTTP response used by the service tests."""

    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict:
        """Return the configured JSON payload."""
        return self._payload


class FakeHttpClient:
    """Minimal async HTTP client for LinkedIn and Supabase requests."""

    def __init__(self, responses: list[FakeResponse]):
        self.responses = responses
        self.requests: list[dict] = []

    async def __aenter__(self) -> "FakeHttpClient":
        """Return the fake client for an async context manager."""
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        """Close the fake client without doing network I/O."""

    async def post(self, url: str, **kwargs) -> FakeResponse:
        """Record a POST request and return the next configured response."""
        self.requests.append({"method": "POST", "url": url, **kwargs})
        return self.responses.pop(0)

    async def get(self, url: str, **kwargs) -> FakeResponse:
        """Record a GET request and return the next configured response."""
        self.requests.append({"method": "GET", "url": url, **kwargs})
        return self.responses.pop(0)


class FakeSettings:
    """Settings required by the LinkedIn OAuth service."""

    app_base_url = "http://localhost:3000"
    api_base_url = "http://localhost:8000"
    jwt_secret_key = "test-jwt-secret"
    linkedin_client_id = "linkedin-client-id"
    linkedin_client_secret = "linkedin-client-secret"
    linkedin_oauth_scopes = "openid profile email"


def _service(
    responses: list[FakeResponse],
) -> tuple[LinkedInOAuthService, FakeHttpClient]:
    """Build a service with deterministic settings and HTTP responses."""
    http_client = FakeHttpClient(responses)
    service = LinkedInOAuthService(
        settings_config=FakeSettings,
        http_client_factory=lambda **_: http_client,
    )
    return service, http_client


def test_authorization_url_targets_linkedin_directly() -> None:
    """The browser authorization URL must not be a Supabase URL."""
    service, _ = _service([])

    authorization_url, state = service.create_authorization_url()
    parsed = urlparse(authorization_url)
    query = parse_qs(parsed.query)

    assert parsed.netloc == "www.linkedin.com"
    assert parsed.path == "/oauth/v2/authorization"
    assert query["client_id"] == ["linkedin-client-id"]
    assert query["redirect_uri"] == [
        "http://localhost:8000/api/v1/auth/linkedin/callback"
    ]
    assert query["scope"] == ["openid profile email"]
    assert query["state"] == [state]
    assert "supabase" not in authorization_url


def test_authorization_requires_openid_scope() -> None:
    """The broker must request LinkedIn's OIDC scope to receive an ID token."""

    class MissingOpenIdSettings(FakeSettings):
        """Settings without the required LinkedIn OpenID scope."""

        linkedin_oauth_scopes = "profile email"

    service = LinkedInOAuthService(settings_config=MissingOpenIdSettings)

    with pytest.raises(
        LinkedInOAuthConfigurationError,
        match="LINKEDIN_OAUTH_SCOPES must include openid",
    ):
        service.create_authorization_url()


def test_authorization_requires_linkedin_credentials() -> None:
    """Missing provider credentials fail before a URL is generated."""

    class MissingCredentialsSettings(FakeSettings):
        """Settings without the LinkedIn client secret."""

        linkedin_client_secret = None

    service = LinkedInOAuthService(settings_config=MissingCredentialsSettings)

    with pytest.raises(
        LinkedInOAuthConfigurationError,
        match="linkedin_client_secret",
    ):
        service.create_authorization_url()


@pytest.mark.asyncio
async def test_exchange_code_returns_verified_identity() -> None:
    """The code exchange keeps secrets server-side and returns a verified profile."""
    service, http_client = _service(
        [
            FakeResponse(
                200,
                {
                    "access_token": "linkedin-access-token",
                    "id_token": "linkedin-id-token",
                },
            ),
            FakeResponse(
                200,
                {
                    "sub": "linkedin-user-id",
                    "email": "person@example.com",
                    "email_verified": True,
                    "given_name": "Person",
                    "family_name": "Example",
                    "name": "Person Example",
                    "picture": "https://example.com/avatar.png",
                },
            ),
        ]
    )
    _, state = service.create_authorization_url()

    identity = await service.exchange_code("linkedin-auth-code", state)

    assert identity.email == "person@example.com"
    assert identity.first_name == "Person"
    assert identity.last_name == "Example"
    assert identity.provider == "linkedin"
    assert identity.provider_sub == "linkedin-user-id"
    assert identity.picture == "https://example.com/avatar.png"

    token_request = http_client.requests[0]
    assert token_request["url"] == "https://www.linkedin.com/oauth/v2/accessToken"
    assert token_request["data"]["code"] == "linkedin-auth-code"
    assert token_request["data"]["client_secret"] == "linkedin-client-secret"
    assert "client_secret" not in token_request["url"]

    userinfo_request = http_client.requests[1]
    assert userinfo_request["headers"]["Authorization"] == (
        "Bearer linkedin-access-token"
    )


@pytest.mark.asyncio
async def test_exchange_rejects_invalid_authorization_code() -> None:
    """Invalid authorization codes must not reach LinkedIn."""
    service, http_client = _service([])
    _, state = service.create_authorization_url()

    with pytest.raises(ValueError, match="Invalid LinkedIn authorization code"):
        await service.exchange_code("", state)

    assert http_client.requests == []


@pytest.mark.asyncio
async def test_exchange_rejects_linkedin_token_error() -> None:
    """Provider token errors are returned as a generic OAuth failure."""
    service, http_client = _service([FakeResponse(400, {})])
    _, state = service.create_authorization_url()

    with pytest.raises(ValueError, match="could not be completed"):
        await service.exchange_code("linkedin-auth-code", state)

    assert len(http_client.requests) == 1


@pytest.mark.asyncio
async def test_exchange_requires_linkedin_access_token() -> None:
    """The backend must receive both LinkedIn tokens from the code exchange."""
    service, http_client = _service([FakeResponse(200, {"id_token": "id-token"})])
    _, state = service.create_authorization_url()

    with pytest.raises(ValueError, match="access token"):
        await service.exchange_code("linkedin-auth-code", state)

    assert len(http_client.requests) == 1


@pytest.mark.asyncio
async def test_exchange_rejects_linkedin_userinfo_error() -> None:
    """A failed userinfo request must not produce an identity token response."""
    service, http_client = _service(
        [
            FakeResponse(
                200,
                {
                    "access_token": "linkedin-access-token",
                    "id_token": "linkedin-id-token",
                },
            ),
            FakeResponse(503, {}),
        ]
    )
    _, state = service.create_authorization_url()

    with pytest.raises(ValueError, match="profile information"):
        await service.exchange_code("linkedin-auth-code", state)

    assert len(http_client.requests) == 2


@pytest.mark.asyncio
async def test_exchange_rejects_invalid_state_before_network_call() -> None:
    """A forged or expired state must not reach LinkedIn."""
    service, http_client = _service([])

    with pytest.raises(ValueError, match="Invalid OAuth state"):
        await service.exchange_code("linkedin-auth-code", "forged-state")

    assert http_client.requests == []


@pytest.mark.asyncio
async def test_exchange_rejects_unverified_linkedin_email() -> None:
    """Unverified LinkedIn emails cannot be used for account linking."""
    service, http_client = _service(
        [
            FakeResponse(
                200,
                {
                    "access_token": "linkedin-access-token",
                    "id_token": "linkedin-id-token",
                },
            ),
            FakeResponse(
                200,
                {
                    "sub": "linkedin-user-id",
                    "email": "person@example.com",
                    "email_verified": False,
                },
            ),
        ]
    )
    _, state = service.create_authorization_url()

    with pytest.raises(ValueError, match="verified email"):
        await service.exchange_code("linkedin-auth-code", state)

    assert len(http_client.requests) == 2


@pytest.mark.asyncio
async def test_exchange_requires_linkedin_id_token() -> None:
    """The Supabase custom OIDC provider must receive a signed ID token."""
    service, _ = _service(
        [
            FakeResponse(200, {"access_token": "linkedin-access-token"}),
        ]
    )
    _, state = service.create_authorization_url()

    with pytest.raises(ValueError, match="ID token"):
        await service.exchange_code("linkedin-auth-code", state)
