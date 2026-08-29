"""Preflight an Alembic database before applying the checked-out migrations.

This check is intentionally read-only. It protects shared staging and
production from an older checkout attempting to operate on a database whose
revision is newer than the migration files available to that checkout.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine


class MigrationCompatibilityError(ValueError):
    """Raised when a database revision is not understood by this checkout."""


@dataclass(frozen=True)
class MigrationCompatibilityResult:
    """Summarize the read-only migration compatibility decision."""

    current_heads: tuple[str, ...]
    repository_heads: tuple[str, ...]


def validate_revision_state(
    current_heads: Iterable[str],
    repository_heads: Iterable[str],
    known_revisions: Iterable[str],
) -> MigrationCompatibilityResult:
    """Validate that all database revisions exist in the current checkout.

    Args:
        current_heads: Revision IDs reported by the target database. An empty
            iterable is valid for a newly created database.
        repository_heads: Revision IDs at the heads of this checkout's
            migration graph.
        known_revisions: Every revision ID present in this checkout.

    Returns:
        A stable, sorted summary of the database and repository heads.

    Raises:
        MigrationCompatibilityError: If the database contains a revision that
            is absent from the checkout, or if the checkout does not have
            exactly one migration head.
    """
    current = tuple(sorted(set(current_heads)))
    heads = tuple(sorted(set(repository_heads)))
    known = set(known_revisions)

    unknown = sorted(set(current) - known)
    if unknown:
        raise MigrationCompatibilityError(
            "database contains unknown revision(s): " + ", ".join(unknown)
        )
    if not heads:
        raise MigrationCompatibilityError("checkout contains no Alembic head")
    if len(heads) > 1:
        raise MigrationCompatibilityError(
            "checkout contains multiple Alembic heads: "
            + ", ".join(heads)
            + "; create an Alembic merge revision before upgrading"
        )

    return MigrationCompatibilityResult(
        current_heads=current,
        repository_heads=heads,
    )


def _read_env_value(env_file: Path, key: str) -> str:
    """Read one simple KEY=value entry without sourcing the env file."""
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        if name.strip() == key:
            return value.strip().strip('"').strip("'")
    return ""


def _migration_script(root: Path) -> ScriptDirectory:
    """Load the repository's Alembic script directory from a repo root."""
    config = Config(str(root / "backend" / "alembic.ini"))
    config.set_main_option("script_location", str(root / "backend" / "alembic"))
    return ScriptDirectory.from_config(config)


def get_repository_heads(root: Path) -> tuple[str, ...]:
    """Return the sorted Alembic heads defined by the checkout."""
    return tuple(sorted(_migration_script(root).get_heads()))


def check_database(env_file: Path, root: Path) -> MigrationCompatibilityResult:
    """Read the target database revision and compare it with repository heads.

    Args:
        env_file: Environment file containing ``DATABASE_URL``.
        root: Repository root containing ``backend/alembic``.

    Returns:
        Migration compatibility summary.

    Raises:
        FileNotFoundError: If the env file or Alembic metadata is missing.
        MigrationCompatibilityError: If the database is ahead of the checkout.
        RuntimeError: If the database cannot be queried.
    """
    if not env_file.exists():
        raise FileNotFoundError(f"missing environment file: {env_file}")

    database_url = _read_env_value(env_file, "DATABASE_URL")
    if not database_url:
        raise ValueError(f"DATABASE_URL is missing from {env_file}")

    script = _migration_script(root)
    known_revisions = {revision.revision for revision in script.walk_revisions()}
    repository_heads = set(get_repository_heads(root))

    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            current_heads = MigrationContext.configure(connection).get_current_heads()
    except Exception as exc:  # pragma: no cover - provider-specific driver errors
        raise RuntimeError(
            "could not read the target database migration state"
        ) from exc
    finally:
        engine.dispose()

    return validate_revision_state(
        current_heads,
        repository_heads,
        known_revisions,
    )


def _format_revisions(revisions: tuple[str, ...]) -> str:
    """Format revision IDs without exposing any database credentials."""
    return ", ".join(revisions) if revisions else "(empty database)"


def main(argv: list[str] | None = None) -> int:
    """Run the migration compatibility preflight and return a process code."""
    parser = argparse.ArgumentParser(
        description="Check an Alembic repository graph or database before upgrades."
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        help="Environment file containing DATABASE_URL",
    )
    parser.add_argument(
        "--repository-only",
        action="store_true",
        help="Validate the repository migration graph without connecting to a database",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Repository root (defaults to the current checkout)",
    )
    args = parser.parse_args(argv)

    try:
        if args.repository_only:
            repository_heads = get_repository_heads(args.root.resolve())
            result = validate_revision_state(
                (),
                repository_heads,
                repository_heads,
            )
            print(
                "Repository migration graph is compatible: "
                f"repository_heads={_format_revisions(result.repository_heads)}"
            )
            return 0

        if args.env_file is None:
            parser.error("--env-file is required unless --repository-only is used")

        result = check_database(args.env_file.resolve(), args.root.resolve())
    except MigrationCompatibilityError as exc:
        print(f"Migration compatibility check failed: {exc}", file=sys.stderr)
        return 2
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"Migration compatibility check failed: {exc}", file=sys.stderr)
        return 2

    print(
        "Migration state is compatible: "
        f"current={_format_revisions(result.current_heads)}; "
        f"repository_heads={_format_revisions(result.repository_heads)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
