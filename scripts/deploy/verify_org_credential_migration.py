#!/usr/bin/env python3
"""Verify that organization provider credentials no longer use plaintext storage.

This is a read-only postcondition check for the staged legacy-column migration.
It intentionally reports counts only: organization identifiers, ciphertext, and
decrypted provider values never appear in command output.
"""

from __future__ import annotations

import os
from argparse import ArgumentParser
from pathlib import Path

import sqlalchemy as sa
from dotenv import dotenv_values

from shared.common.security import decrypt_data


def _parse_args() -> object:
    """Parse the environment-file argument used by the deployment check."""
    parser = ArgumentParser(description=__doc__)
    parser.add_argument(
        "--env-file",
        default=".env.prod",
        help="Environment file containing DATABASE_URL and ENCRYPTION_KEY",
    )
    return parser.parse_args()


def _load_environment(path: Path) -> dict[str, str]:
    """Load only scalar dotenv values into the current process."""
    values = {
        key: str(value)
        for key, value in dotenv_values(path).items()
        if value is not None
    }
    for key, value in values.items():
        os.environ[key] = value
    return values


def main() -> int:
    """Run the read-only credential migration postcondition check."""
    args = _parse_args()
    env_file = Path(args.env_file)
    values = _load_environment(env_file)
    database_url = values.get("DATABASE_URL")
    if not database_url:
        raise SystemExit(f"DATABASE_URL is missing from {env_file}")

    engine = sa.create_engine(database_url, pool_pre_ping=True)
    with engine.connect() as connection:
        rows = (
            connection.execute(
                sa.text(
                    """
                    SELECT provider_credentials, google_api_key
                    FROM organizations
                    """
                )
            )
            .mappings()
            .all()
        )

    plaintext_rows = 0
    invalid_ciphertext_rows = 0
    encrypted_rows = 0
    for row in rows:
        if row["google_api_key"]:
            plaintext_rows += 1
        ciphertext = row["provider_credentials"]
        if not ciphertext:
            continue
        encrypted_rows += 1
        decrypted = decrypt_data(str(ciphertext))
        if not isinstance(decrypted, dict) or not decrypted:
            invalid_ciphertext_rows += 1

    if plaintext_rows or invalid_ciphertext_rows:
        print(
            "Organization credential migration verification failed: "
            f"{plaintext_rows} plaintext rows, "
            f"{invalid_ciphertext_rows} invalid encrypted rows."
        )
        return 1

    print(
        "Organization credential migration verified: "
        f"{len(rows)} organizations inspected, "
        f"{encrypted_rows} encrypted credential payloads, 0 plaintext rows."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
