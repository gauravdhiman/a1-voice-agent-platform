#!/usr/bin/env python3
"""Re-encrypt ciphertext created by the removed development fallback key.

The pre-2026-08-17 security helper used a deterministic development Fernet
fallback when ``ENCRYPTION_KEY`` was absent. This command is a one-time,
explicitly enabled repair for data created with that fallback. It re-encrypts
only rows that successfully decrypt with the historical key and verifies each
payload with the current production key before committing.

It never prints ciphertext or decrypted values. Run without ``--apply`` first
to preview counts; ``--apply`` is required for the production write.
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


LEGACY_FALLBACK_SALT = b"ai-voice-agent-platform-salt"
LEGACY_FALLBACK_SEED = b"dev-secret-key"

# These are the application columns that store Fernet-encrypted JSON. Keep the
# list explicit so an operator cannot accidentally rewrite unrelated columns.
ENCRYPTED_COLUMNS: tuple[tuple[str, str], ...] = (
    ("organizations", "provider_credentials"),
    ("agent_tools", "sensitive_config"),
    ("platform_tools", "mcp_server_secret_headers"),
    ("platform_tools", "oauth_client_secret_encrypted"),
    ("phone_numbers", "connection_token_encrypted"),
    ("platform_notification_settings", "telegram_bot_token_encrypted"),
)


def parse_env_file(path: Path) -> dict[str, str]:
    """Read simple ``NAME=value`` entries without sourcing the file."""
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        values[name.strip()] = value.strip().strip("\"'")
    return values


def legacy_fallback_key() -> bytes:
    """Derive the exact Fernet key used by the removed development fallback."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=LEGACY_FALLBACK_SALT,
        iterations=100_000,
    )
    return base64.urlsafe_b64encode(kdf.derive(LEGACY_FALLBACK_SEED))


def decrypt_object(blob: str, fernet: Fernet) -> dict[str, Any] | None:
    """Decrypt one blob and return an object payload, without logging it."""
    try:
        payload = json.loads(fernet.decrypt(blob.encode("utf-8")).decode("utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _current_fernet(values: dict[str, str]) -> Fernet:
    """Validate and return the configured current production Fernet key."""
    raw_key = values.get("ENCRYPTION_KEY", "").strip()
    if not raw_key:
        raise ValueError("ENCRYPTION_KEY is missing from the selected env file")
    try:
        return Fernet(raw_key.encode("utf-8"))
    except (TypeError, ValueError) as exc:
        raise ValueError("ENCRYPTION_KEY is not a valid Fernet key") from exc


def rotate(path: Path, *, apply: bool) -> int:
    """Preview or apply the legacy-ciphertext rotation and return row count."""
    values = parse_env_file(path)
    dsn = values.get("DATABASE_URL", "").strip()
    if not dsn:
        raise ValueError("DATABASE_URL is missing from the selected env file")

    current = _current_fernet(values)
    legacy = Fernet(legacy_fallback_key())

    try:
        import psycopg2
        from psycopg2 import sql
    except ImportError as exc:  # pragma: no cover - operator environment guard
        raise RuntimeError("psycopg2 is required to rotate production data") from exc

    try:
        connection = psycopg2.connect(dsn)
    except Exception as exc:  # pragma: no cover - depends on operator network
        raise RuntimeError(f"database connection failed ({type(exc).__name__})") from None

    total_updated = 0
    try:
        with connection:
            with connection.cursor() as cursor:
                for table, column in ENCRYPTED_COLUMNS:
                    identifier = sql.Identifier(column)
                    cursor.execute(
                        sql.SQL(
                            "SELECT id, {column} FROM public.{table} "
                            "WHERE {column} IS NOT NULL "
                            "AND btrim({column}) <> ''"
                        ).format(
                            column=identifier,
                            table=sql.Identifier(table),
                        )
                    )
                    rows = cursor.fetchall()
                    current_count = 0
                    legacy_count = 0
                    unresolved_count = 0
                    updated_count = 0
                    for row_id, blob in rows:
                        if decrypt_object(blob, current) is not None:
                            current_count += 1
                            continue

                        payload = decrypt_object(blob, legacy)
                        if payload is None:
                            unresolved_count += 1
                            continue

                        legacy_count += 1
                        rotated_blob = current.encrypt(
                            json.dumps(payload, separators=(",", ":")).encode("utf-8")
                        ).decode("utf-8")
                        if decrypt_object(rotated_blob, current) != payload:
                            raise RuntimeError(
                                f"verification failed for {table}.{column}"
                            )

                        if apply:
                            cursor.execute(
                                sql.SQL(
                                    "UPDATE public.{table} SET {column} = %s "
                                    "WHERE id = %s"
                                ).format(
                                    table=sql.Identifier(table),
                                    column=identifier,
                                ),
                                (rotated_blob, row_id),
                            )
                            if cursor.rowcount != 1:
                                raise RuntimeError(
                                    f"row update verification failed for {table}.{column}"
                                )
                            updated_count += 1

                    mode = "updated" if apply else "would_update"
                    print(
                        f"{table}.{column}: total={len(rows)} "
                        f"current={current_count} legacy={legacy_count} "
                        f"unresolved={unresolved_count} {mode}={updated_count if apply else legacy_count}"
                    )
                    total_updated += updated_count if apply else legacy_count
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    print(f"total_{'updated' if apply else 'would_update'}={total_updated}")
    return total_updated


def main() -> int:
    """Run the guarded rotation command."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path(".env.prod"),
        help="Environment file containing DATABASE_URL and current ENCRYPTION_KEY",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Commit the verified re-encryption updates",
    )
    args = parser.parse_args()

    try:
        rotate(args.env_file, apply=args.apply)
    except Exception as exc:
        print(f"rotation failed ({type(exc).__name__}): {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
