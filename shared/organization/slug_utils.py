"""URL slug helpers for organizations (shared org slug + public page URL)."""

from __future__ import annotations

import re

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

# Reserved path segments that would collide with app routes.
RESERVED_ORGANIZATION_SLUGS = frozenset(
    {
        "api",
        "admin",
        "embed",
        "auth",
        "dashboard",
        "organization",
        "agents",
        "platform",
        "onboarding",
    }
)


def normalize_organization_slug(value: str) -> str:
    """Normalize user input into a lowercase kebab-case slug."""
    normalized = value.lower().strip()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    normalized = re.sub(r"-+", "-", normalized).strip("-")
    return normalized[:100]


def validate_organization_slug(value: str) -> tuple[bool, str | None]:
    """Validate an organization slug.

    Returns:
        Tuple of (is_valid, error_message).
    """
    if not value:
        return False, "Slug is required"
    if len(value) > 100:
        return False, "Slug must be 100 characters or fewer"
    if not SLUG_PATTERN.match(value):
        return (
            False,
            "Slug must use lowercase letters, numbers, and hyphens only "
            "(e.g. acme-support)",
        )
    if value in RESERVED_ORGANIZATION_SLUGS:
        return False, f"'{value}' is reserved and cannot be used"
    return True, None


def suggest_organization_slug_from_name(name: str) -> str:
    """Suggest a slug from an organization name."""
    return normalize_organization_slug(name)


__all__ = [
    "RESERVED_ORGANIZATION_SLUGS",
    "normalize_organization_slug",
    "suggest_organization_slug_from_name",
    "validate_organization_slug",
]
