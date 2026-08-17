"""Provider-neutral OAuth capability and security helpers.

OAuth 2.0 does not guarantee that every authorization response contains a
refresh token.  This module keeps the distinction between provider metadata
(``grant_types_supported`` or an explicit platform declaration) and the live
connection state (whether this connection actually has a refresh token).
The same helpers are used by native and MCP-backed tools so the UI, callback,
and background refresh service cannot drift into different interpretations.
"""

from __future__ import annotations

import ipaddress
import os
import socket
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Optional
from urllib.parse import urlsplit


class OAuthRefreshMode(str, Enum):
    """How an OAuth connection is expected to remain authenticated."""

    AUTOMATIC = "automatic"
    MANUAL = "manual"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class OAuthRefreshMetadata:
    """Public, non-secret guidance for an OAuth connection.

    Attributes:
        mode: Automatic, manual, or unknown refresh behavior.
        message: Safe explanation suitable for platform and org admins.
        manual_reauth_interval_minutes: Optional interval declared by the
            platform admin or OAuth provider; ``None`` means the provider's
            access-token lifetime controls the next reauthorization.
    """

    mode: OAuthRefreshMode
    message: str
    manual_reauth_interval_minutes: Optional[int] = None


_REFRESH_MODE_KEYS = (
    "oauth_refresh_mode",
    "refresh_support",
    "auto_refresh_supported",
    "refresh_token_supported",
    "supports_refresh_token",
)
_MANUAL_INTERVAL_KEYS = (
    "manual_reauth_interval_minutes",
    "reauth_interval_minutes",
    "manual_refresh_interval_minutes",
)
_SUPPORTED_CLIENT_AUTH_METHODS = {
    "none": "none",
    "public": "none",
    "client_secret_post": "client_secret_post",
    "post": "client_secret_post",
    "client_secret_basic": "client_secret_basic",
    "basic": "client_secret_basic",
}
_OAUTH_SECRET_KEYS = {
    "access_token",
    "accesstoken",
    "refresh_token",
    "refreshtoken",
    "id_token",
    "idtoken",
    "client_secret",
    "clientsecret",
    "client_secret_encrypted",
    "clientsecretencrypted",
    "oauth_client_secret",
    "oautoclientsecret",
    "oauth_client_secret_encrypted",
    "oautoclientsecretencrypted",
    "client_assertion",
    "clientassertion",
    "client_assertion_value",
    "clientassertionvalue",
    "code",
    "authorization_code",
    "authorizationcode",
    "code_verifier",
    "codeverifier",
    "private_key",
    "privatekey",
    "api_key",
    "apikey",
    "api_token",
    "apitoken",
    "auth_token",
    "authtoken",
    "bearer_token",
    "bearertoken",
    "mcp_server_secret_headers",
    "mcpserversecretheaders",
    "secret_headers",
    "secretheaders",
    "credential",
    "credentials",
    "authorization",
    "password",
    "secret",
}


def _value(config: Mapping[str, Any] | Any, key: str, default: Any = None) -> Any:
    """Read a field from a mapping or Pydantic-style model."""
    if isinstance(config, Mapping):
        return config.get(key, default)
    return getattr(config, key, default)


def _as_bool(value: Any) -> Optional[bool]:
    """Normalize a boolean-like capability declaration."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "yes", "1", "supported", "automatic", "auto"}:
            return True
        if normalized in {
            "false",
            "no",
            "0",
            "unsupported",
            "manual",
            "none",
        }:
            return False
    return None


def _manual_interval(config: Mapping[str, Any] | Any) -> Optional[int]:
    """Read and validate a safe admin-facing manual reauthorization interval."""
    for key in _MANUAL_INTERVAL_KEYS:
        raw_value = _value(config, key)
        if raw_value in (None, ""):
            continue
        try:
            value = int(raw_value)
        except (TypeError, ValueError):
            continue
        if 1 <= value <= 525_600:  # one year in minutes
            return value
    return None


def _configured_mode(config: Mapping[str, Any] | Any) -> Optional[OAuthRefreshMode]:
    """Resolve an explicit provider/platform refresh declaration."""
    for key in _REFRESH_MODE_KEYS:
        raw_value = _value(config, key)
        if raw_value in (None, ""):
            continue
        if key == "oauth_refresh_mode" or key == "refresh_support":
            normalized = str(raw_value).strip().lower()
            if normalized in {"automatic", "supported", "auto", "true"}:
                return OAuthRefreshMode.AUTOMATIC
            if normalized in {"manual", "unsupported", "false", "none"}:
                return OAuthRefreshMode.MANUAL
            if normalized in {"unknown", "conditional"}:
                return OAuthRefreshMode.UNKNOWN
        else:
            boolean_value = _as_bool(raw_value)
            if boolean_value is not None:
                return (
                    OAuthRefreshMode.AUTOMATIC
                    if boolean_value
                    else OAuthRefreshMode.MANUAL
                )

    grant_types = _value(config, "grant_types_supported")
    if isinstance(grant_types, str):
        grant_types = grant_types.replace(",", " ").split()
    if isinstance(grant_types, (list, tuple, set)) and grant_types:
        return (
            OAuthRefreshMode.AUTOMATIC
            if "refresh_token" in {str(value).lower() for value in grant_types}
            else OAuthRefreshMode.MANUAL
        )

    # Google and a few other providers use access_type=offline to request a
    # refresh grant. It is a strong signal, but the callback still verifies
    # that the provider actually returned a refresh token.
    if str(_value(config, "access_type", "")).strip().lower() == "offline":
        return OAuthRefreshMode.AUTOMATIC
    return None


def get_oauth_client_auth_method(
    config: Mapping[str, Any] | Any,
) -> Optional[str]:
    """Resolve the OAuth token-endpoint client-auth method from metadata.

    Explicit configuration wins. When only authorization-server discovery
    capabilities are present, the first method supported by this platform is
    selected. If the server advertises only a proprietary method, that method
    is returned so callers can fail closed and explain why automatic refresh is
    unavailable instead of silently sending a client secret with the wrong
    authentication scheme.

    Args:
        config: OAuth metadata represented by a mapping or Pydantic-style model.

    Returns:
        A canonical supported method (``none``, ``client_secret_post``, or
        ``client_secret_basic``), an unsupported method name, or ``None`` when
        the server did not declare a method.
    """
    for key in ("token_endpoint_auth_method", "client_auth_method"):
        value = _value(config, key)
        if value not in (None, ""):
            normalized = str(value).strip().lower()
            return _SUPPORTED_CLIENT_AUTH_METHODS.get(normalized, normalized)

    advertised = _value(config, "token_endpoint_auth_methods_supported")
    if isinstance(advertised, str):
        advertised = advertised.replace(",", " ").split()
    if isinstance(advertised, (list, tuple, set)):
        normalized_methods = [str(value).strip().lower() for value in advertised]
        for method in normalized_methods:
            canonical = _SUPPORTED_CLIENT_AUTH_METHODS.get(method)
            if canonical:
                return canonical
        if normalized_methods:
            return normalized_methods[0]
    return None


def is_supported_oauth_client_auth_method(method: Any) -> bool:
    """Return whether a token endpoint auth method is implemented safely.

    Args:
        method: Method name from OAuth authorization-server metadata.

    Returns:
        ``True`` for public, client-secret-post, and client-secret-basic
        authentication (including their common aliases); otherwise ``False``.
    """
    if method in (None, ""):
        return True
    normalized = str(method).strip().lower()
    return normalized in _SUPPORTED_CLIENT_AUTH_METHODS


def get_oauth_refresh_metadata(
    config: Mapping[str, Any] | Any,
    *,
    has_refresh_token: Optional[bool] = None,
) -> OAuthRefreshMetadata:
    """Derive safe admin guidance for native or MCP OAuth.

    Args:
        config: OAuth authorization-server/tool metadata.
        has_refresh_token: ``True`` or ``False`` when the encrypted connection
            was inspected; ``None`` when only platform metadata is available.

    Returns:
        :class:`OAuthRefreshMetadata` with no credential material.

    Notes:
        A live connection without a refresh token is always manual, even when
        the provider advertises the refresh grant. This prevents the UI from
        promising persistence that the particular authorization cannot provide.
    """
    interval = _manual_interval(config)
    declared_mode = _configured_mode(config)
    client_auth_method = get_oauth_client_auth_method(config)
    unsupported_client_auth = not is_supported_oauth_client_auth_method(
        client_auth_method
    )
    has_token_endpoint = bool(
        _value(config, "token_url") or _value(config, "token_endpoint")
    )
    if declared_mode is OAuthRefreshMode.MANUAL:
        # An explicit manual declaration is an administrative safety boundary;
        # do not silently turn it into an auto-refresh promise just because a
        # provider happened to return a refresh token for one connection.
        mode = OAuthRefreshMode.MANUAL
    elif unsupported_client_auth or not has_token_endpoint:
        mode = OAuthRefreshMode.MANUAL
    elif has_refresh_token is True:
        mode = OAuthRefreshMode.AUTOMATIC
    elif has_refresh_token is False:
        mode = OAuthRefreshMode.MANUAL
    elif declared_mode is not None:
        mode = declared_mode
    else:
        mode = OAuthRefreshMode.UNKNOWN

    if unsupported_client_auth:
        message = (
            "Automatic refresh is unavailable because this provider requires "
            f"unsupported OAuth client authentication ({client_auth_method}). "
            "An admin must re-authenticate or configure a supported provider "
            "adapter."
        )
    elif not has_token_endpoint:
        message = (
            "Automatic refresh is unavailable because no OAuth token endpoint "
            "is configured. An admin must re-authenticate or complete the "
            "provider configuration."
        )
    elif mode is OAuthRefreshMode.AUTOMATIC:
        message = (
            "Automatic refresh is enabled when this authorization returns a "
            "refresh token. The platform refreshes access tokens before expiry."
        )
    elif mode is OAuthRefreshMode.MANUAL:
        if interval:
            message = (
                "This connection requires manual reauthorization approximately "
                f"every {interval} minutes because automatic refresh is not "
                "available."
            )
        else:
            message = (
                "Automatic refresh is not available for this connection. An "
                "admin must re-authenticate when the access token expires."
            )
    else:
        message = (
            "Refresh support is not declared by this provider. The platform "
            "will refresh automatically if a refresh token is returned; "
            "otherwise an admin must re-authenticate when the access token expires."
        )
    return OAuthRefreshMetadata(mode, message, interval)


def sanitize_oauth_config(config: Mapping[str, Any] | Any) -> dict[str, Any]:
    """Remove credentials and grant artifacts from public OAuth metadata.

    OAuth endpoints, scopes, client IDs, and capability declarations are safe
    to return to an admin UI. Client secrets, bearer grants, authorization
    codes, and PKCE verifiers are not. This is deliberately allow-by-field
    removal so future descriptive metadata survives without exposing known
    credential keys.
    """
    if isinstance(config, Mapping):
        values = dict(config)
    elif hasattr(config, "model_dump"):
        values = config.model_dump()
    else:
        values = dict(config)

    def _sanitize(value: Any) -> Any:
        if isinstance(value, Mapping):
            result: dict[Any, Any] = {}
            for key, nested_value in value.items():
                if str(key).strip().lower().replace("-", "_") in _OAUTH_SECRET_KEYS:
                    continue
                sanitized_value = _sanitize(nested_value)
                if isinstance(nested_value, Mapping) and not sanitized_value:
                    continue
                result[key] = sanitized_value
            return result
        if isinstance(value, list):
            return [_sanitize(item) for item in value]
        if isinstance(value, tuple):
            return [_sanitize(item) for item in value]
        return value

    sanitized = _sanitize(values)
    return sanitized if isinstance(sanitized, dict) else {}


def extract_oauth_client_secret(config: Mapping[str, Any] | Any) -> Optional[str]:
    """Find a legacy OAuth client secret without returning other grant data.

    Older platform-tool rows could place a confidential client secret inside
    ``auth_config``. New rows use the dedicated encrypted column, but a
    one-time application migration needs to recognize both snake_case and
    camelCase forms, including nested OAuth client metadata. This helper is
    intentionally limited to client-secret field names; access and refresh
    grants are never copied into platform metadata.

    Args:
        config: OAuth metadata represented as a mapping or Pydantic-style
            model.

    Returns:
        The first non-empty string client secret, or ``None`` when no legacy
        client secret is present.
    """
    if isinstance(config, Mapping):
        values: Any = config
    elif hasattr(config, "model_dump"):
        values = config.model_dump()
    else:
        try:
            values = dict(config)
        except (TypeError, ValueError):
            return None

    def _find(value: Any) -> Optional[str]:
        if isinstance(value, Mapping):
            for key, nested_value in value.items():
                normalized_key = (
                    str(key).strip().lower().replace("-", "").replace("_", "")
                )
                if normalized_key in {"clientsecret", "oauthclientsecret"}:
                    if isinstance(nested_value, str) and nested_value.strip():
                        return nested_value
                found = _find(nested_value)
                if found:
                    return found
        elif isinstance(value, (list, tuple)):
            for item in value:
                found = _find(item)
                if found:
                    return found
        return None

    return _find(values)


def _allow_local_urls() -> bool:
    """Return whether explicitly enabled local OAuth endpoints are allowed."""
    environment = os.getenv("ENVIRONMENT") or os.getenv("APP_ENV") or "development"
    if environment.strip().lower() in {"production", "prod", "staging", "stage"}:
        return False
    return os.getenv("MCP_ALLOW_LOCAL_URLS", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def _resolve_oauth_host(host: str) -> list[str]:
    """Resolve an OAuth endpoint hostname for SSRF-aware network checks."""
    infos = socket.getaddrinfo(host, None)
    addresses: list[str] = []
    for info in infos:
        address = info[4][0]
        if address not in addresses:
            addresses.append(address)
    return addresses


def validate_oauth_endpoint_url(
    url: Any,
    *,
    resolve_dns: bool = False,
    allow_loopback_redirect: bool = False,
) -> tuple[bool, str]:
    """Validate an OAuth endpoint before sending codes or grants to it.

    Public OAuth endpoints must use HTTPS, cannot contain userinfo or a URL
    fragment, and explicit private IP literals are rejected. When
    ``resolve_dns`` is true, every resolved address is checked as well; this is
    required for authorization-server metadata and token-exchange network
    boundaries. HTTP is allowed only for loopback development when
    ``MCP_ALLOW_LOCAL_URLS`` is enabled. A loopback browser redirect may opt
    into HTTP independently of the deployment environment because the backend
    does not contact the redirect URI; server-side OAuth endpoints never use
    this exception.

    Args:
        url: Authorization, token, registration, or redirect endpoint.
        resolve_dns: Resolve hostname addresses and reject private/local
            results. Keep false for display-only validation; use true before
            server-side network requests.
        allow_loopback_redirect: Allow an explicitly enabled HTTP loopback
            redirect URI even when the application is using staging settings.
            This must only be set for a browser callback URI, never for an
            authorization, token, or registration endpoint.

    Returns:
        ``(True, "")`` when acceptable, otherwise ``(False, reason)``.
    """
    if not isinstance(url, str) or not url.strip():
        return False, "OAuth URL is required"
    try:
        parsed = urlsplit(url.strip())
    except Exception:
        return False, "Invalid OAuth URL"
    if parsed.scheme not in {"https", "http"} or not parsed.hostname:
        return False, "OAuth URL must use https and include a host"
    if parsed.username or parsed.password:
        return False, "OAuth URL must not contain userinfo"
    if parsed.fragment:
        return False, "OAuth URL must not contain a fragment"

    local_flag_enabled = os.getenv("MCP_ALLOW_LOCAL_URLS", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    loopback_redirect_allowed = allow_loopback_redirect and local_flag_enabled

    try:
        address = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        address = None

    addresses: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
    if address is not None:
        addresses.append(address)
    elif resolve_dns:
        try:
            addresses = [
                ipaddress.ip_address(value)
                for value in _resolve_oauth_host(parsed.hostname)
            ]
        except socket.gaierror:
            return False, "OAuth URL host could not be resolved"
        except (TypeError, ValueError, OSError):
            return False, "OAuth URL host returned an invalid address"
        if not addresses:
            return False, "OAuth URL host could not be resolved"

    for resolved_address in addresses:
        if (
            resolved_address.is_private
            or resolved_address.is_link_local
            or resolved_address.is_loopback
            or resolved_address.is_reserved
            or resolved_address.is_unspecified
        ):
            if (
                parsed.scheme == "http"
                and (loopback_redirect_allowed or _allow_local_urls())
                and resolved_address.is_loopback
            ):
                continue
            return False, "OAuth URL resolves to a private or local address"

    if parsed.scheme == "http":
        if loopback_redirect_allowed and parsed.hostname.lower() in {
            "localhost",
            "127.0.0.1",
            "::1",
        }:
            return True, ""
        if _allow_local_urls() and parsed.hostname.lower() in {
            "localhost",
            "127.0.0.1",
            "::1",
        }:
            return True, ""
        return False, "Public OAuth endpoints must use https"
    return True, ""


__all__ = [
    "OAuthRefreshMetadata",
    "OAuthRefreshMode",
    "extract_oauth_client_secret",
    "get_oauth_client_auth_method",
    "get_oauth_refresh_metadata",
    "is_supported_oauth_client_auth_method",
    "sanitize_oauth_config",
    "validate_oauth_endpoint_url",
]
