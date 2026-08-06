"""Tests for LinkedIn credential resolution in application settings."""

from shared.config.settings import Settings


def test_linkedin_settings_accept_supabase_prefixed_env_vars(
    monkeypatch,
) -> None:
    """LinkedIn credentials should resolve from Supabase env var names."""
    monkeypatch.delenv("LINKEDIN_CLIENT_ID", raising=False)
    monkeypatch.delenv("LINKEDIN_CLIENT_SECRET", raising=False)
    monkeypatch.setenv(
        "SUPABASE_AUTH_EXTERNAL_LINKEDIN_OIDC_CLIENT_ID",
        "linkedin-client-id",
    )
    monkeypatch.setenv(
        "SUPABASE_AUTH_EXTERNAL_LINKEDIN_OIDC_CLIENT_SECRET",
        "linkedin-client-secret",
    )

    settings = Settings()

    assert settings.linkedin_client_id == "linkedin-client-id"
    assert settings.linkedin_client_secret == "linkedin-client-secret"


def test_linkedin_settings_prefer_explicit_linkedin_env_vars(monkeypatch) -> None:
    """Explicit LINKEDIN_* env vars should override Supabase aliases."""
    monkeypatch.setenv("LINKEDIN_CLIENT_ID", "explicit-client-id")
    monkeypatch.setenv("LINKEDIN_CLIENT_SECRET", "explicit-client-secret")
    monkeypatch.setenv(
        "SUPABASE_AUTH_EXTERNAL_LINKEDIN_OIDC_CLIENT_ID",
        "supabase-client-id",
    )
    monkeypatch.setenv(
        "SUPABASE_AUTH_EXTERNAL_LINKEDIN_OIDC_CLIENT_SECRET",
        "supabase-client-secret",
    )

    settings = Settings()

    assert settings.linkedin_client_id == "explicit-client-id"
    assert settings.linkedin_client_secret == "explicit-client-secret"
