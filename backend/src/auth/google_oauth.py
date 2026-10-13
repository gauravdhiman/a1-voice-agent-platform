"""Direct Google OpenID Connect OAuth broker for backend redirect sign-in."""

from __future__ import annotations

import logging
from typing import Any, Callable
from urllib.parse import urlencode

import httpx

from shared.config import settings as default_settings

from .oauth_identity import OAuthVerifiedIdentity
from .oauth_state import create_signed_state, validate_signed_state

logger = logging.getLogger(__name__)

GOOGLE_AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
GOOGLE_OAUTH_PURPOSE = "google-oauth"
HTTP_TIMEOUT_SECONDS = 10.0
GOOGLE_OAUTH_SCOPES = "openid email profile"


class GoogleOAuthConfigurationError(RuntimeError):
    """Raised when Google OAuth is not configured."""


class GoogleOAuthError(ValueError):
    """Raised when Google rejects or cannot complete an OAuth exchange."""


class GoogleOAuthService:
    """Create Google authorization URLs and exchange callback codes."""

    def __init__(
        self,
        settings_config: Any = default_settings,
        http_client_factory: Callable[..., Any] = httpx.AsyncClient,
    ) -> None:
        self.settings = settings_config
        self.http_client_factory = http_client_factory

    @property
    def redirect_uri(self) -> str:
        """Return the registered backend callback URL for Google."""
        return f"{self.settings.api_base_url.rstrip('/')}/api/v1/auth/google/callback"

    def create_authorization_url(
        self,
        invitation_token: str | None = None,
        terms_accepted: bool = False,
    ) -> tuple[str, str]:
        """Create a Google authorization URL and signed state value."""
        self._ensure_configuration()
        state = create_signed_state(
            purpose=GOOGLE_OAUTH_PURPOSE,
            redirect_uri=self.redirect_uri,
            jwt_secret_key=self.settings.jwt_secret_key,
            invitation_token=invitation_token,
            terms_accepted=terms_accepted,
        )
        query = urlencode(
            {
                "response_type": "code",
                "client_id": self.settings.google_client_id,
                "redirect_uri": self.redirect_uri,
                "scope": GOOGLE_OAUTH_SCOPES,
                "state": state,
                "access_type": "online",
                "prompt": "select_account",
            }
        )
        return f"{GOOGLE_AUTHORIZATION_URL}?{query}", state

    async def exchange_code(self, code: str, state: str) -> OAuthVerifiedIdentity:
        """Exchange a Google authorization code for a verified profile."""
        self._ensure_configuration()
        state_payload = validate_signed_state(
            state,
            purpose=GOOGLE_OAUTH_PURPOSE,
            redirect_uri=self.redirect_uri,
            jwt_secret_key=self.settings.jwt_secret_key,
        )
        if not code or len(code) > 2048:
            raise GoogleOAuthError("Invalid Google authorization code.")

        async with self.http_client_factory(timeout=HTTP_TIMEOUT_SECONDS) as client:
            token_response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self.redirect_uri,
                    "client_id": self.settings.google_client_id,
                    "client_secret": self.settings.google_client_secret,
                },
            )
            if token_response.status_code != 200:
                logger.warning(
                    "Google authorization-code exchange failed with status %s",
                    token_response.status_code,
                )
                raise GoogleOAuthError("Google authorization could not be completed.")

            token_data = token_response.json()
            access_token = token_data.get("access_token")
            if not access_token:
                raise GoogleOAuthError("Google did not return an access token.")

            userinfo_response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if userinfo_response.status_code != 200:
                logger.warning(
                    "Google userinfo request failed with status %s",
                    userinfo_response.status_code,
                )
                raise GoogleOAuthError(
                    "Google profile information could not be loaded."
                )

            userinfo = userinfo_response.json()
            email = self._verified_email(userinfo)
            if not email:
                raise GoogleOAuthError("Google must provide a verified email address.")

            first_name, last_name = self._profile_names(userinfo)
            google_sub = str(userinfo.get("sub") or "").strip()
            if not google_sub:
                raise GoogleOAuthError("Google did not return a subject claim.")

            picture = userinfo.get("picture")
            normalized_picture = (
                picture.strip()
                if isinstance(picture, str) and picture.strip()
                else None
            )
            invitation_token = state_payload.get("invitation_token")
            normalized_invitation = (
                invitation_token.strip()
                if isinstance(invitation_token, str) and invitation_token.strip()
                else None
            )
            return OAuthVerifiedIdentity(
                provider="google",
                email=email,
                first_name=first_name,
                last_name=last_name,
                provider_sub=google_sub,
                picture=normalized_picture,
                invitation_token=normalized_invitation,
                terms_accepted=bool(state_payload.get("terms_accepted", False)),
            )

    def _ensure_configuration(self) -> None:
        """Validate the credentials required by the complete OAuth flow."""
        required_values = {
            "google_client_id": getattr(self.settings, "google_client_id", None),
            "google_client_secret": getattr(
                self.settings, "google_client_secret", None
            ),
            "jwt_secret_key": getattr(self.settings, "jwt_secret_key", None),
        }
        if any(not value for value in required_values.values()):
            missing = [name for name, value in required_values.items() if not value]
            raise GoogleOAuthConfigurationError(
                "Google OAuth is not configured. Missing: "
                f"{', '.join(missing)}. Set SUPABASE_AUTH_EXTERNAL_GOOGLE_CLIENT_ID "
                "and SUPABASE_AUTH_EXTERNAL_GOOGLE_CLIENT_SECRET in the selected "
                "root environment file."
            )

    @staticmethod
    def _profile_names(userinfo: dict[str, Any]) -> tuple[str, str]:
        """Extract display names from Google OIDC userinfo claims."""
        given_name = userinfo.get("given_name")
        family_name = userinfo.get("family_name")
        if isinstance(given_name, str) and given_name.strip():
            first_name = given_name.strip()
            last_name = (
                family_name.strip()
                if isinstance(family_name, str) and family_name.strip()
                else ""
            )
            return first_name, last_name

        full_name = userinfo.get("name")
        if isinstance(full_name, str) and full_name.strip():
            parts = full_name.strip().split(" ", 1)
            return parts[0], parts[1] if len(parts) > 1 else ""

        return "", ""

    @staticmethod
    def _verified_email(userinfo: dict[str, Any]) -> str | None:
        """Return a normalized email only when Google marks it verified."""
        email = userinfo.get("email")
        verified = userinfo.get("email_verified")
        if (
            not isinstance(email, str)
            or not email.strip()
            or verified is not True
            and str(verified).lower() != "true"
        ):
            return None
        return email.strip().lower()


google_oauth_service = GoogleOAuthService()
