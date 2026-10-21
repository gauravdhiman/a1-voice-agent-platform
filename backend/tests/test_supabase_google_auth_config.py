"""Regression tests for the local Supabase Google authentication configuration."""

from pathlib import Path
import tomllib


SUPABASE_CONFIG_PATH = (
    Path(__file__).resolve().parents[2] / "supabase" / "config.toml"
)


def test_local_google_auth_uses_env_backed_provider_credentials() -> None:
    """Ensure local Supabase accepts Google ID tokens with nonce validation."""
    with SUPABASE_CONFIG_PATH.open("rb") as config_file:
        config = tomllib.load(config_file)

    google_config = config["auth"]["external"]["google"]

    assert google_config["enabled"] is True
    assert (
        google_config["client_id"]
        == "env(SUPABASE_AUTH_EXTERNAL_GOOGLE_CLIENT_ID)"
    )
    assert (
        google_config["secret"]
        == "env(SUPABASE_AUTH_EXTERNAL_GOOGLE_CLIENT_SECRET)"
    )
    assert google_config["skip_nonce_check"] is False


def test_local_supabase_blocks_direct_signup_for_invite_only_onboarding() -> None:
    """Keep local Auth aligned with the backend's invitation-only signup gate."""
    with SUPABASE_CONFIG_PATH.open("rb") as config_file:
        config = tomllib.load(config_file)

    assert config["auth"]["enable_signup"] is False
    assert config["auth"]["email"]["enable_signup"] is False
