"""Tests for organization slug helpers."""

from shared.organization.slug_utils import (
    normalize_organization_slug,
    suggest_organization_slug_from_name,
    validate_organization_slug,
)


class TestOrganizationSlugUtils:
    def test_normalize_slug(self):
        assert normalize_organization_slug("  Acme Corp!  ") == "acme-corp"
        assert normalize_organization_slug("hello__world") == "hello-world"

    def test_suggest_from_name(self):
        assert suggest_organization_slug_from_name("Acme Support") == "acme-support"

    def test_validate_accepts_kebab_case(self):
        ok, err = validate_organization_slug("acme-support")
        assert ok is True
        assert err is None

    def test_validate_rejects_reserved(self):
        ok, err = validate_organization_slug("api")
        assert ok is False
        assert err is not None
