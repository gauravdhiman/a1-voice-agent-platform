"""Tests for selecting the environment file used by shared application settings."""

from pathlib import Path

from shared.config.settings import Settings


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
