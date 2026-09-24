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
