"""Tests for permissive auth email validation (local/dev domains)."""

import pytest
from pydantic import ValidationError

from src.auth.models import SignInRequest
from src.notifications.platform_settings_models import ResendVerificationRequest


class TestAuthEmailValidation:
    """Auth endpoints accept Supabase-local email domains."""

    def test_sign_in_accepts_local_dev_email(self) -> None:
        request = SignInRequest(
            email="test@cogninets.local",
            password="Password123!",
        )
        assert request.email == "test@cogninets.local"

    def test_sign_in_rejects_missing_at(self) -> None:
        with pytest.raises(ValidationError):
            SignInRequest(email="not-an-email", password="x")

    def test_resend_verification_accepts_local_dev_email(self) -> None:
        request = ResendVerificationRequest(email="test@cogninets.local")
        assert request.email == "test@cogninets.local"
