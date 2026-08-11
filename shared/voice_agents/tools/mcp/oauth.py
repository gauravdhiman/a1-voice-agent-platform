"""Provider-neutral OAuth helpers for remote MCP servers.

MCP does not define a vendor-specific config-file format. For HTTP servers it
does define an OAuth discovery and authorization contract: clients discover a
protected-resource metadata document, locate an authorization server, use
authorization-code + PKCE, and send a resource-bound Bearer token. This module
keeps that protocol work separate from FastAPI routes and database services.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any, Mapping
from urllib.parse import urlencode, urlsplit, urlunsplit

import httpx


def _state_secret() -> bytes:
    """Return the signing key used for short-lived OAuth callback state."""
    configured = os.getenv("MCP_OAUTH_STATE_SECRET") or os.getenv("JWT_SECRET_KEY")
    if not configured:
        try:
            from shared.config import settings

            configured = settings.jwt_secret_key
        except Exception:  # pragma: no cover - defensive import guard
            configured = None
    if not configured:
        raise ValueError(
            "MCP OAuth state signing requires MCP_OAUTH_STATE_SECRET or JWT_SECRET_KEY"
        )
    return configured.encode("utf-8")


def _encode(value: bytes) -> str:
    """Encode bytes as unpadded URL-safe base64."""
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _decode(value: str) -> bytes:
    """Decode unpadded URL-safe base64."""
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def pkce_challenge(verifier: str) -> str:
    """Create the RFC 7636 S256 challenge for an OAuth code verifier."""
    return _encode(hashlib.sha256(verifier.encode("ascii")).digest())


def create_mcp_oauth_state(payload: Mapping[str, Any]) -> str:
    """Create signed, short-lived state containing the PKCE verifier.

    The verifier is intentionally carried inside authenticated state so the
    callback remains stateless across backend instances. It is never logged or
    returned to the browser outside the opaque ``state`` value.
    """
    body = dict(payload)
    body.setdefault("issued_at", int(time.time()))
    encoded = _encode(json.dumps(body, separators=(",", ":"), sort_keys=True).encode())
    signature = _encode(
        hmac.new(_state_secret(), encoded.encode(), hashlib.sha256).digest()
    )
    return f"{encoded}.{signature}"


def decode_mcp_oauth_state(state: str, *, max_age_seconds: int = 600) -> dict[str, Any]:
    """Verify and decode callback state, rejecting tampering and replay windows."""
    try:
        encoded, signature = state.split(".", 1)
        expected = _encode(
            hmac.new(_state_secret(), encoded.encode(), hashlib.sha256).digest()
        )
        if not hmac.compare_digest(signature, expected):
            raise ValueError("Invalid MCP OAuth state signature")
        body = json.loads(_decode(encoded).decode("utf-8"))
        issued_at = int(body["issued_at"])
        if abs(int(time.time()) - issued_at) > max_age_seconds:
            raise ValueError("MCP OAuth state has expired")
        if not isinstance(body, dict):
            raise ValueError("MCP OAuth state payload must be an object")
        return body
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("Invalid MCP OAuth state") from exc


def build_mcp_authorization_url(
    authorization_endpoint: str,
    *,
    client_id: str,
    redirect_uri: str,
    state: str,
    code_challenge: str,
    scopes: list[str] | None = None,
    resource: str | None = None,
) -> str:
    """Build an RFC 7636 + MCP resource-indicator authorization URL."""
    params: dict[str, str] = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    if scopes:
        params["scope"] = " ".join(scopes)
    if resource:
        params["resource"] = resource
    separator = "&" if "?" in authorization_endpoint else "?"
    return f"{authorization_endpoint}{separator}{urlencode(params)}"


def _origin(url: str) -> str:
    """Return scheme + authority for a URL."""
    parsed = urlsplit(url)
    return urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))


def _well_known_urls(issuer: str) -> list[str]:
    """Return OAuth/OIDC metadata URLs in MCP's required order."""
    parsed = urlsplit(issuer)
    base = _origin(issuer)
    path = parsed.path.rstrip("/")
    if path:
        return [
            f"{base}/.well-known/oauth-authorization-server{path}",
            f"{base}/.well-known/openid-configuration{path}",
            f"{issuer.rstrip('/')}/.well-known/openid-configuration",
        ]
    return [
        f"{base}/.well-known/oauth-authorization-server",
        f"{base}/.well-known/openid-configuration",
    ]


def _protected_resource_urls(server_url: str) -> list[str]:
    """Return RFC 9728 protected-resource metadata candidates."""
    parsed = urlsplit(server_url)
    base = _origin(server_url)
    path = parsed.path.rstrip("/")
    candidates = []
    if path:
        candidates.append(f"{base}/.well-known/oauth-protected-resource{path}")
    candidates.append(f"{base}/.well-known/oauth-protected-resource")
    return candidates


async def discover_mcp_oauth_config(
    server_url: str,
    configured: Mapping[str, Any] | None = None,
    *,
    timeout: float = 10.0,
) -> dict[str, Any]:
    """Resolve MCP OAuth endpoints from config or standard metadata discovery.

    The returned mapping uses the platform's legacy-compatible names
    ``auth_url`` and ``token_url`` so the existing tool connection model can
    store it without a schema migration.
    """
    supplied = dict(configured or {})
    if supplied.get("auth_url") and supplied.get("token_url"):
        supplied.setdefault("provider", "mcp")
        supplied.setdefault("resource", server_url)
        return supplied

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        protected: dict[str, Any] = {}
        for metadata_url in _protected_resource_urls(server_url):
            try:
                response = await client.get(
                    metadata_url, headers={"Accept": "application/json"}
                )
                if response.is_success:
                    body = response.json()
                    if isinstance(body, dict):
                        protected = body
                        break
            except (httpx.HTTPError, ValueError):
                continue

        authorization_servers = protected.get("authorization_servers") or []
        if isinstance(authorization_servers, str):
            authorization_servers = [authorization_servers]
        issuer = next((str(value) for value in authorization_servers if value), None)
        if issuer is None:
            # Older MCP revisions allowed authorization metadata directly at
            # the host root when protected-resource metadata was unavailable.
            issuer = _origin(server_url)

        metadata: dict[str, Any] = {}
        for metadata_url in _well_known_urls(issuer):
            try:
                response = await client.get(
                    metadata_url, headers={"Accept": "application/json"}
                )
                if response.is_success:
                    body = response.json()
                    if isinstance(body, dict):
                        metadata = body
                        break
            except (httpx.HTTPError, ValueError):
                continue

    auth_url = metadata.get("authorization_endpoint") or supplied.get("auth_url")
    token_url = metadata.get("token_endpoint") or supplied.get("token_url")
    if not auth_url or not token_url:
        raise ValueError(
            "MCP server did not publish OAuth authorization metadata; provide "
            "authorization and token endpoints in the platform configuration"
        )

    scopes = (
        supplied.get("scopes")
        or metadata.get("scopes_supported")
        or protected.get("scopes_supported")
        or []
    )
    if isinstance(scopes, str):
        scopes = [part for part in scopes.replace(",", " ").split() if part]
    return {
        **supplied,
        "provider": "mcp",
        "auth_url": str(auth_url),
        "token_url": str(token_url),
        "scopes": [str(scope) for scope in scopes],
        "resource": supplied.get("resource") or protected.get("resource") or server_url,
        "registration_endpoint": metadata.get("registration_endpoint"),
    }


async def register_mcp_oauth_client(
    registration_endpoint: str,
    *,
    redirect_uri: str,
    client_name: str = "24x7 AI MCP connector",
    timeout: float = 10.0,
) -> str:
    """Register a public PKCE client through OAuth Dynamic Client Registration."""
    payload = {
        "client_name": client_name,
        "redirect_uris": [redirect_uri],
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none",
    }
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        response = await client.post(
            registration_endpoint,
            json=payload,
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        body = response.json()
    client_id = body.get("client_id") if isinstance(body, dict) else None
    if not client_id:
        raise ValueError("MCP OAuth client registration returned no client_id")
    return str(client_id)


__all__ = [
    "build_mcp_authorization_url",
    "create_mcp_oauth_state",
    "decode_mcp_oauth_state",
    "discover_mcp_oauth_config",
    "pkce_challenge",
    "register_mcp_oauth_client",
]
