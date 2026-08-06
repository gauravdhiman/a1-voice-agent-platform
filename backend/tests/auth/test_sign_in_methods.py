"""Tests for sign-in method extraction helpers."""

from types import SimpleNamespace

from src.auth.sign_in_methods import (
    GENERIC_EXISTING_ACCOUNT_MESSAGE,
    format_sign_in_methods,
    resolve_sign_in_guidance,
)


class TestResolveSignInGuidance:
    """Infer signup guidance from Supabase auth user records."""

    def test_email_password_user(self) -> None:
        user = SimpleNamespace(
            identities=[SimpleNamespace(provider="email")],
            user_metadata={},
            encrypted_password="hashed",
        )

        guidance = resolve_sign_in_guidance(user)
        assert guidance.sign_in_methods == ["email"]
        assert "Email and password" in guidance.message

    def test_google_oauth_user_from_metadata(self) -> None:
        user = SimpleNamespace(
            identities=[SimpleNamespace(provider="email")],
            user_metadata={"google_sub": "google-123"},
            encrypted_password=None,
        )

        guidance = resolve_sign_in_guidance(user)
        assert guidance.sign_in_methods == ["google"]
        assert "Google" in guidance.message
        assert "Email and password" not in guidance.message

    def test_google_oauth_user_with_last_sign_in_method(self) -> None:
        user = SimpleNamespace(
            identities=[SimpleNamespace(provider="email")],
            user_metadata={
                "google_sub": "google-123",
                "last_sign_in_method": "google",
            },
            encrypted_password=None,
        )

        guidance = resolve_sign_in_guidance(user)
        assert guidance.sign_in_methods == ["google"]
        assert "last signed in with Google" in guidance.message

    def test_ambiguous_email_identity_only(self) -> None:
        user = SimpleNamespace(
            identities=[SimpleNamespace(provider="email")],
            user_metadata={},
            encrypted_password=None,
        )

        guidance = resolve_sign_in_guidance(user)
        assert guidance.sign_in_methods == []
        assert guidance.message == GENERIC_EXISTING_ACCOUNT_MESSAGE

    def test_google_and_email_user(self) -> None:
        user = SimpleNamespace(
            identities=[
                SimpleNamespace(provider="email"),
                SimpleNamespace(provider="google"),
            ],
            user_metadata={"google_sub": "google-123"},
            encrypted_password="hashed",
        )

        guidance = resolve_sign_in_guidance(user)
        assert guidance.sign_in_methods == ["email", "google"]

    def test_linkedin_provider_metadata(self) -> None:
        user = SimpleNamespace(
            identities=[SimpleNamespace(provider="email")],
            user_metadata={"linkedin_sub": "linkedin-123"},
            encrypted_password=None,
        )

        guidance = resolve_sign_in_guidance(user)
        assert guidance.sign_in_methods == ["linkedin"]


class TestFormatSignInMethods:
    """Format sign-in methods for UI copy."""

    def test_single_method(self) -> None:
        assert format_sign_in_methods(["google"]) == "Google"

    def test_two_methods(self) -> None:
        assert format_sign_in_methods(["google", "email"]) == "Google or Email and password"

    def test_three_methods(self) -> None:
        assert (
            format_sign_in_methods(["google", "linkedin", "email"])
            == "Google, LinkedIn, or Email and password"
        )
