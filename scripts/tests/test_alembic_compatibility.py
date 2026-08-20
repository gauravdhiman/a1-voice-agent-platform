"""Unit tests for the migration compatibility preflight."""

import pytest

from scripts.deploy import check_alembic_compatibility


def test_empty_database_is_compatible() -> None:
    """A newly created database may have no Alembic revision yet."""
    result = check_alembic_compatibility.validate_revision_state(
        set(), {"head"}, {"head"}
    )

    assert result.current_heads == ()
    assert result.repository_heads == ("head",)


def test_known_database_revision_is_compatible() -> None:
    """A known older revision can be upgraded by the current checkout."""
    result = check_alembic_compatibility.validate_revision_state(
        {"20260817000001"},
        {"20260818000001"},
        {
            "20260817000001",
            "20260818000001",
        },
    )

    assert result.current_heads == ("20260817000001",)
    assert result.repository_heads == ("20260818000001",)


def test_unknown_database_revision_fails_before_upgrade() -> None:
    """A database ahead of the checkout must not be mutated by Alembic."""
    with pytest.raises(
        check_alembic_compatibility.MigrationCompatibilityError,
        match="unknown revision",
    ):
        check_alembic_compatibility.validate_revision_state(
            {"20260901000001"},
            {"20260818000001"},
            {"20260818000001"},
        )
