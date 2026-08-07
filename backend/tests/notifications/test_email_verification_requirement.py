"""Tests for email verification requirement based on sender configuration."""

from src.notifications.platform_settings_models import verification_sender_configured


class TestVerificationSenderConfigured:
    """Verification is on when both From email and From name are set."""

    def test_returns_false_when_email_missing(self) -> None:
        assert verification_sender_configured(None, "Platform") is False
        assert verification_sender_configured("", "Platform") is False
        assert verification_sender_configured("   ", "Platform") is False

    def test_returns_false_when_name_missing(self) -> None:
        assert verification_sender_configured("noreply@example.com", None) is False
        assert verification_sender_configured("noreply@example.com", "") is False

    def test_returns_true_when_both_set(self) -> None:
        assert (
            verification_sender_configured("noreply@example.com", "24x7 AI") is True
        )
