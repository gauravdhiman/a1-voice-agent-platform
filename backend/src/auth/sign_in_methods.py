"""Helpers for inferring how an existing Supabase auth user can sign in."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Optional

SignInMethod = Literal["email", "google", "linkedin"]

SIGN_IN_METHOD_LABELS: dict[SignInMethod, str] = {
    "email": "Email and password",
    "google": "Google",
    "linkedin": "LinkedIn",
}

GENERIC_EXISTING_ACCOUNT_MESSAGE = (
    "An account with this email already exists. Please sign in to continue."
)


@dataclass(frozen=True)
class SignInGuidance:
    """Structured signup guidance for an email that is already registered."""

    sign_in_methods: list[SignInMethod]
    message: str

    @property
    def show_methods(self) -> bool:
        """Whether the UI should list specific sign-in methods."""
        return bool(self.sign_in_methods)


def normalize_auth_provider(provider: str) -> Optional[SignInMethod]:
    """Map Supabase identity provider slugs to platform sign-in methods."""
    normalized = provider.lower()
    if normalized == "email":
        return "email"
    if normalized == "google":
        return "google"
    if normalized in {"linkedin", "linkedin_oidc", "oidc"}:
        return "linkedin"
    return None


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _user_has_password(user: Any) -> bool:
    """Return True when the auth user record indicates a password is set."""
    encrypted_password = getattr(user, "encrypted_password", None)
    if encrypted_password:
        return True

    # Some admin API payloads omit the hash but expose a boolean-ish hint.
    password_hint = getattr(user, "has_password", None)
    if isinstance(password_hint, bool):
        return password_hint

    return False


def _oauth_metadata_flags(metadata: dict[str, Any]) -> tuple[bool, bool]:
    return bool(metadata.get("google_sub")), bool(metadata.get("linkedin_sub"))


def _guidance_for_single_method(method: SignInMethod) -> SignInGuidance:
    label = SIGN_IN_METHOD_LABELS[method]
    return SignInGuidance(
        sign_in_methods=[method],
        message=(
            "An account with this email already exists. "
            f"Sign in with {label}."
        ),
    )


def resolve_sign_in_guidance(user: Any) -> SignInGuidance:
    """Resolve signup guidance for an existing auth user.

    Preference order:
    1. ``user_metadata.last_sign_in_method`` recorded by this platform on login
    2. Deterministic OAuth metadata (``google_sub`` / ``linkedin_sub``)
    3. Deterministic email/password account (password hash present, no OAuth subs)
    4. Generic message when the method cannot be determined reliably

    Our backend OAuth flow creates users with an email identity via magic link,
    so identity provider lists alone are not sufficient and must not imply
    email/password sign-in.
    """
    metadata = _as_dict(getattr(user, "user_metadata", None))
    last_method = metadata.get("last_sign_in_method")
    if last_method in SIGN_IN_METHOD_LABELS:
        label = SIGN_IN_METHOD_LABELS[last_method]
        return SignInGuidance(
            sign_in_methods=[last_method],
            message=(
                "An account with this email already exists. "
                f"You last signed in with {label}."
            ),
        )

    has_google, has_linkedin = _oauth_metadata_flags(metadata)
    has_password = _user_has_password(user)

    if has_google and not has_linkedin and not has_password:
        return _guidance_for_single_method("google")
    if has_linkedin and not has_google and not has_password:
        return _guidance_for_single_method("linkedin")
    if has_password and not has_google and not has_linkedin:
        return _guidance_for_single_method("email")

    confident_methods: list[SignInMethod] = []
    if has_password:
        confident_methods.append("email")
    if has_google:
        confident_methods.append("google")
    if has_linkedin:
        confident_methods.append("linkedin")

    if len(confident_methods) == 1:
        return _guidance_for_single_method(confident_methods[0])

    if len(confident_methods) > 1:
        labels = format_sign_in_methods(confident_methods)
        return SignInGuidance(
            sign_in_methods=confident_methods,
            message=(
                "An account with this email already exists. "
                f"Sign in with {labels}."
            ),
        )

    return SignInGuidance(
        sign_in_methods=[],
        message=GENERIC_EXISTING_ACCOUNT_MESSAGE,
    )


def extract_sign_in_methods(user: Any) -> list[SignInMethod]:
    """Return sign-in methods only when guidance is deterministic."""
    return resolve_sign_in_guidance(user).sign_in_methods


def format_sign_in_methods(methods: list[SignInMethod]) -> str:
    """Format sign-in methods for human-readable UI copy."""
    labels = [SIGN_IN_METHOD_LABELS[method] for method in methods]
    if len(labels) == 1:
        return labels[0]
    if len(labels) == 2:
        return f"{labels[0]} or {labels[1]}"
    return ", ".join(labels[:-1]) + f", or {labels[-1]}"
