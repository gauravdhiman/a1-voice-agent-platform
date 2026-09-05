"""Tests for selecting the environment file used by shared application settings."""

from pathlib import Path

from shared.config.settings import PROJECT_ROOT, Settings, resolve_env_file


def test_default_env_file_is_local(monkeypatch) -> None:
    """Direct application settings should default to the local root file."""
    monkeypatch.delenv("ENV_FILE", raising=False)

    assert resolve_env_file() == str(PROJECT_ROOT / ".env.local")


def test_relative_env_file_override_resolves_from_project_root(monkeypatch) -> None:
    """Relative ENV_FILE values should be resolved from the repository root."""
    monkeypatch.setenv("ENV_FILE", ".env.staging")

    assert resolve_env_file() == str(PROJECT_ROOT / ".env.staging")


def test_settings_honors_env_file_override(monkeypatch, tmp_path: Path) -> None:
    """Settings should load values from the file selected by ENV_FILE."""
    selected_file = tmp_path / ".env.staging"
    selected_file.write_text(
        "APP_NAME=staging-settings-test\n"
        "ENVIRONMENT=staging\n"
        "SUPABASE_URL=https://gdzwiwukcwbqohfwxxrx.supabase.co\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("ENV_FILE", str(selected_file))

    settings = Settings()

    assert settings.app_name == "staging-settings-test"
    assert settings.environment == "staging"
    assert settings.supabase_url == "https://gdzwiwukcwbqohfwxxrx.supabase.co"


def test_settings_parses_comma_separated_admin_allowlist_from_environment(
    monkeypatch,
) -> None:
    """The documented comma-separated allowlist must not trigger JSON parsing."""
    monkeypatch.delenv("ENV_FILE", raising=False)
    monkeypatch.setenv(
        "PLATFORM_ADMIN_ALLOWLIST",
        "admin@example.com, Founder@Example.com",
    )

    settings = Settings(_env_file=None)

    assert settings.platform_admin_allowlist == [
        "admin@example.com",
        "founder@example.com",
    ]
