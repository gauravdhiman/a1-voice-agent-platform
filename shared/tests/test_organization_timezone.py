"""Tests for organization IANA timezone validation and resolution."""

from types import SimpleNamespace

import pytest

from shared.organization.timezone import (
    normalize_timezone_input,
    resolve_organization_timezone,
    validate_iana_timezone,
)


class TestValidateIanaTimezone:
    """validate_iana_timezone accepts known IANA names and rejects garbage."""

    def test_accepts_america_phoenix(self) -> None:
        tz, error = validate_iana_timezone("America/Phoenix")
        assert error is None
        assert tz == "America/Phoenix"

    def test_rejects_invalid_name(self) -> None:
        tz, error = validate_iana_timezone("Not/A_Real_Zone")
        assert tz is None
        assert error is not None
        assert "invalid" in error.lower()

    def test_empty_string_is_unset(self) -> None:
        tz, error = validate_iana_timezone("")
        assert tz is None
        assert error is None

    def test_none_is_unset(self) -> None:
        tz, error = validate_iana_timezone(None)
        assert tz is None
        assert error is None


class TestNormalizeTimezoneInput:
    """normalize_timezone_input trims and maps blank to None."""

    def test_strips_whitespace(self) -> None:
        assert normalize_timezone_input("  America/Los_Angeles  ") == (
            "America/Los_Angeles",
            None,
        )

    def test_blank_becomes_none(self) -> None:
        assert normalize_timezone_input("   ") == (None, None)


class TestResolveOrganizationTimezone:
    """Resolution chain: org.timezone → platform default → UTC."""

    def test_uses_org_timezone_when_set(self) -> None:
        org = SimpleNamespace(timezone="America/Chicago")
        assert (
            resolve_organization_timezone(org, platform_default="America/New_York")
            == "America/Chicago"
        )

    def test_falls_back_to_platform_default(self) -> None:
        org = SimpleNamespace(timezone=None)
        assert (
            resolve_organization_timezone(org, platform_default="America/Denver")
            == "America/Denver"
        )

    def test_falls_back_to_utc_when_unset(self) -> None:
        assert resolve_organization_timezone(None, platform_default=None) == "UTC"
        assert resolve_organization_timezone(SimpleNamespace(timezone=None)) == "UTC"

    def test_invalid_platform_default_still_returns_utc(self) -> None:
        org = SimpleNamespace(timezone=None)
        assert (
            resolve_organization_timezone(org, platform_default="Bad/Zone") == "UTC"
        )
