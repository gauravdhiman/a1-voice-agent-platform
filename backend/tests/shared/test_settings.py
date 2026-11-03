"""Tests for safety-critical application settings."""

import pytest
from pydantic import ValidationError

from shared.config.settings import Settings


def test_oauth_refresh_lease_has_minimum_safe_duration() -> None:
    """Reject a lease shorter than the bounded refresh request budget."""
    with pytest.raises(ValidationError):
        Settings(_env_file=None, token_refresh_lock_lease_seconds=179)

    settings = Settings(_env_file=None, token_refresh_lock_lease_seconds=180)
    assert settings.token_refresh_lock_lease_seconds == 180


@pytest.mark.parametrize(
    "environment,expected",
    [
        ("production", "external"),
        ("development", "in_process"),
        ("staging", "in_process"),
        ("test", "in_process"),
    ],
)
def test_maintenance_default_depends_on_environment(monkeypatch, environment, expected):
    monkeypatch.delenv("MAINTENANCE_MODE", raising=False)
    assert (
        Settings(_env_file=None, environment=environment).maintenance_mode == expected
    )


@pytest.mark.parametrize(
    "environment,override", [("production", "in_process"), ("staging", "external")]
)
def test_maintenance_mode_can_be_overridden(monkeypatch, environment, override):
    monkeypatch.setenv("MAINTENANCE_MODE", override)
    assert (
        Settings(_env_file=None, environment=environment).maintenance_mode == override
    )
