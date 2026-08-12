#!/usr/bin/env python3
"""Verify that legacy agent phone numbers have table-backed records.

This command is safe to run repeatedly.  It performs read-only checks and is
intended to run immediately after ``alembic upgrade head`` in production and
as an operator check during a staged rollout.
"""

from argparse import ArgumentParser
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any, Mapping, Sequence

import sqlalchemy as sa
from dotenv import dotenv_values


def _load_migration_module():
    """Load the migration's normalization logic without importing the app."""
    root = Path(__file__).parents[2]
    migration_path = (
        root
        / "backend"
        / "alembic"
        / "versions"
        / "20260812000006_backfill_phone_numbers_from_voice_agents.py"
    )
    spec = spec_from_file_location("phone_number_backfill_migration", migration_path)
    if not spec or not spec.loader:
        raise RuntimeError(f"Unable to load migration helper at {migration_path}")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def find_unmigrated_legacy_rows(
    legacy_rows: Sequence[Mapping[str, Any]],
    phone_number_rows: Sequence[Mapping[str, Any]],
) -> list[str]:
    """Find legacy agent rows without a matching phone-number record.

    Args:
        legacy_rows: Non-empty legacy ``voice_agents.phone_number`` rows.
        phone_number_rows: Current ``phone_numbers`` rows.

    Returns:
        Human-readable identifiers for rows that still need migration.

        The migration itself verifies the initial agent assignment. This
        post-deployment check intentionally accepts a later unassigned or
        released row so normal user lifecycle actions do not block future
        deployments while the legacy compatibility column remains populated.

    Raises:
        ValueError: If a legacy value cannot be normalized safely.
    """
    migration = _load_migration_module()
    phone_number_keys = {
        (
            str(row["organization_id"]),
            migration.normalize_legacy_phone(str(row["phone_number"])),
        )
        for row in phone_number_rows
    }
    problems: list[str] = []
    for row in legacy_rows:
        raw_phone = row.get("phone_number")
        if raw_phone is None or not str(raw_phone).strip():
            continue
        normalized = migration.normalize_legacy_phone(str(raw_phone))
        key = (str(row["organization_id"]), normalized)
        if key not in phone_number_keys:
            problems.append(f"{key[0]}/{row['agent_id']}: {normalized}")
    return problems


def _parse_args() -> Any:
    """Parse the environment-file argument for the deployment check."""
    parser = ArgumentParser(description=__doc__)
    parser.add_argument(
        "--env-file",
        default=".env.prod",
        help="Environment file containing DATABASE_URL (default: .env.prod)",
    )
    return parser.parse_args()


def main() -> int:
    """Run the read-only production backfill postcondition check."""
    args = _parse_args()
    env = dotenv_values(args.env_file)
    database_url = env.get("DATABASE_URL")
    if not database_url:
        raise SystemExit(f"DATABASE_URL is missing from {args.env_file}")

    engine = sa.create_engine(database_url, pool_pre_ping=True)
    with engine.connect() as connection:
        legacy_rows = (
            connection.execute(
                sa.text(
                    """
                SELECT organization_id::text AS organization_id,
                       id::text AS agent_id,
                       phone_number
                FROM voice_agents
                WHERE phone_number IS NOT NULL
                  AND btrim(phone_number) <> ''
                """
                )
            )
            .mappings()
            .all()
        )
        phone_number_rows = (
            connection.execute(
                sa.text(
                    """
                SELECT organization_id::text AS organization_id,
                       phone_number,
                       assigned_agent_id::text AS assigned_agent_id
                FROM phone_numbers
                """
                )
            )
            .mappings()
            .all()
        )

    problems = find_unmigrated_legacy_rows(legacy_rows, phone_number_rows)
    if problems:
        print(
            "Phone-number backfill verification failed. "
            f"{len(problems)} legacy assignments are missing:"
        )
        for problem in problems[:20]:
            print(f" - {problem}")
        if len(problems) > 20:
            print(f" - … and {len(problems) - 20} more")
        return 1

    print(
        "Phone-number backfill verified: "
        f"{len(legacy_rows)} legacy assignments have phone_numbers mappings."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
