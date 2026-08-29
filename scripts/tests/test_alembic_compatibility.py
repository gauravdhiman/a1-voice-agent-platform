"""Unit tests for the migration compatibility preflight."""

from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory

from scripts.deploy import check_alembic_compatibility


ROOT = Path(__file__).resolve().parents[2]


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


def test_multiple_repository_heads_fail_before_upgrade() -> None:
    """A new migration branch must be merged before startup can upgrade."""
    with pytest.raises(
        check_alembic_compatibility.MigrationCompatibilityError,
        match="multiple Alembic heads",
    ):
        check_alembic_compatibility.validate_revision_state(
            {"20260819000001"},
            {"20260820000002", "20260821000001"},
            {"20260819000001", "20260820000002", "20260821000001"},
        )


def test_repository_has_one_merged_head() -> None:
    """The checked-in graph must expose one target for ``upgrade head``."""
    config = Config(str(ROOT / "backend" / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "backend" / "alembic"))
    script = ScriptDirectory.from_config(config)

    assert script.get_heads() == ["20260822000001"]


def test_repository_head_helper_is_database_independent() -> None:
    """The CI graph check must not need a live database."""
    assert check_alembic_compatibility.get_repository_heads(ROOT) == (
        "20260822000001",
    )
