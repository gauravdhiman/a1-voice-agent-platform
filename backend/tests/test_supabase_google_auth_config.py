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
