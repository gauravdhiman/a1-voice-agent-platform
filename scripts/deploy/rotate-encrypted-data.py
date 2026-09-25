#!/usr/bin/env python3
"""Re-encrypt application-managed ciphertext with the current Fernet key.

The command is intentionally dry-run by default. During a planned key
rotation, configure the new key as ``ENCRYPTION_KEY`` and the previous key(s)
as ``ENCRYPTION_KEY_FALLBACKS`` in the selected operator environment. The
command verifies every populated encrypted column, rewrites values that still
decrypt only with a fallback key, and verifies the rewritten values before the
transaction is committed.

It never prints ciphertext or decrypted values. ``--apply`` is required for a
database write, and an unreadable populated value aborts the transaction.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path
from typing import Any, Iterable

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

# Keep the inventory explicit. A new Fernet-encrypted column must be added here
# and covered by the deployment postcondition checks before it can be rotated.
ENCRYPTED_COLUMNS: tuple[tuple[str, str], ...] = (
    ("organizations", "provider_credentials"),
    ("agent_tools", "sensitive_config"),
    ("platform_tools", "mcp_server_secret_headers"),
    ("platform_tools", "oauth_client_secret_encrypted"),
    ("phone_numbers", "connection_token_encrypted"),
    ("platform_notification_settings", "telegram_bot_token_encrypted"),
)

DEFAULT_BATCH_SIZE = 200


class RotationError(RuntimeError):
    """Raised when encrypted data cannot be safely verified or rewritten."""


def parse_env_file(path: Path) -> dict[str, str]:
    """Read simple ``NAME=value`` entries without sourcing shell code."""
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        values[name.strip()] = value.strip().strip("\"'")
    return values


def _fernet(raw_key: str, label: str) -> Fernet:
    """Validate one configured Fernet key without exposing its value."""
    if not raw_key:
        raise RotationError(f"{label} is missing")
    try:
        return Fernet(raw_key.encode("utf-8"))
    except (TypeError, ValueError) as exc:
        raise RotationError(f"{label} is not a valid Fernet key") from exc


def build_keyring(values: dict[str, str]) -> tuple[Fernet, MultiFernet]:
    """Build the current-key verifier and the current-plus-fallback keyring."""
    current = _fernet(values.get("ENCRYPTION_KEY", "").strip(), "ENCRYPTION_KEY")
    keys = [current]
    seen = {values["ENCRYPTION_KEY"].strip()}
    for index, raw_fallback in enumerate(
        values.get("ENCRYPTION_KEY_FALLBACKS", "").split(","), start=1
    ):
        fallback_value = raw_fallback.strip()
        if not fallback_value or fallback_value in seen:
            continue
        keys.append(_fernet(fallback_value, f"ENCRYPTION_KEY_FALLBACKS[{index}]"))
        seen.add(fallback_value)
    return current, MultiFernet(keys)


def _decode_object(blob: str, fernet: Fernet | MultiFernet) -> dict[str, Any] | None:
    """Decode one Fernet JSON object without logging its contents."""
    try:
        payload = json.loads(fernet.decrypt(blob.encode("utf-8")).decode("utf-8"))
    except (
        InvalidToken,
        UnicodeDecodeError,
        json.JSONDecodeError,
        ValueError,
        TypeError,
    ):
        return None
    return payload if isinstance(payload, dict) else None


def rotate_blob(
    blob: str, *, current: Fernet, keyring: MultiFernet
) -> tuple[str | None, bool]:
    """Return a current-key ciphertext and whether the old key was used.

    ``None`` means the value was already valid under the current key. A
    ``RotationError`` means the populated value is not decryptable by the
    configured keyring and must not be overwritten.
    """
    if _decode_object(blob, current) is not None:
        return None, False

    payload = _decode_object(blob, keyring)
    if payload is None:
        raise RotationError("an encrypted value could not be decrypted")

    try:
        rotated = keyring.rotate(blob.encode("utf-8")).decode("utf-8")
    except (InvalidToken, TypeError, ValueError) as exc:
        raise RotationError("re-encryption failed for a decryptable value") from exc
    if _decode_object(rotated, current) != payload:
        raise RotationError("re-encrypted value failed current-key verification")
    return rotated, True


def _selected_columns(only: Iterable[str] | None) -> list[tuple[str, str]]:
    """Resolve optional ``table.column`` filters against the allowlist."""
    if not only:
        return list(ENCRYPTED_COLUMNS)

    allowed = {
        f"{table}.{column}": (table, column) for table, column in ENCRYPTED_COLUMNS
    }
    selected: list[tuple[str, str]] = []
    for item in only:
        try:
            selected.append(allowed[item])
        except KeyError as exc:
            choices = ", ".join(sorted(allowed))
            raise RotationError(
                f"unsupported --only target {item!r}; choose from {choices}"
            ) from exc
    return selected


def _rows(
    cursor: Any, table: str, column: str, batch_size: int
) -> Iterable[tuple[Any, str]]:
    """Yield non-empty encrypted rows using a server-side cursor."""
    cursor.itersize = batch_size
    cursor.execute(
        f'SELECT id, "{column}" FROM public."{table}" '
        f'WHERE "{column}" IS NOT NULL AND btrim("{column}") <> \'\''
    )
    yield from cursor


def rotate(
    path: Path,
    *,
    apply: bool,
    batch_size: int = DEFAULT_BATCH_SIZE,
    only: Iterable[str] | None = None,
) -> int:
    """Preview or apply current-key re-encryption and return update count."""
    if batch_size < 1:
        raise RotationError("batch size must be positive")

    values = parse_env_file(path)
    dsn = values.get("DATABASE_URL", "").strip()
    if not dsn:
        raise RotationError("DATABASE_URL is missing from the selected env file")
    current, keyring = build_keyring(values)
    targets = _selected_columns(only)

    try:
        import psycopg2
        from psycopg2 import sql
    except ImportError as exc:  # pragma: no cover - operator environment guard
        raise RotationError(
            "psycopg2 is required to rotate database ciphertext"
        ) from exc

    try:
        connection = psycopg2.connect(dsn)
    except Exception as exc:  # pragma: no cover - depends on operator network
        raise RotationError(
            f"database connection failed ({type(exc).__name__})"
        ) from None

    total_updated = 0
    unresolved = 0
    try:
        with connection:
            with connection.cursor() as write_cursor:
                for table, column in targets:
                    total = 0
                    current_count = 0
                    fallback_count = 0
                    table_unresolved = 0
                    updated = 0
                    read_cursor = connection.cursor(
                        name=f"secret_rotation_{uuid.uuid4().hex}"
                    )
                    try:
                        for row_id, blob in _rows(
                            read_cursor, table, column, batch_size
                        ):
                            total += 1
                            original_blob = str(blob)
                            try:
                                rotated, used_fallback = rotate_blob(
                                    original_blob, current=current, keyring=keyring
                                )
                            except RotationError:
                                table_unresolved += 1
                                unresolved += 1
                                continue

                            if not used_fallback:
                                current_count += 1
                                continue

                            fallback_count += 1
                            if apply and rotated is not None:
                                write_cursor.execute(
                                    sql.SQL(
                                        "UPDATE public.{table} SET {column} = %s "
                                        "WHERE id = %s AND {column} = %s"
                                    ).format(
                                        table=sql.Identifier(table),
                                        column=sql.Identifier(column),
                                    ),
                                    (rotated, row_id, original_blob),
                                )
                                if write_cursor.rowcount != 1:
                                    raise RotationError(
                                        "a ciphertext row changed during rotation; "
                                        "no changes were committed"
                                    )
                                updated += 1
                    finally:
                        read_cursor.close()

                    mode = "updated" if apply else "would_update"
                    print(
                        f"{table}.{column}: total={total} current={current_count} "
                        f"fallback={fallback_count} unresolved={table_unresolved} "
                        f"{mode}={updated if apply else fallback_count}"
                    )
                    total_updated += updated if apply else fallback_count

                if unresolved:
                    raise RotationError(
                        f"{unresolved} populated encrypted value(s) were unreadable; "
                        "no changes were committed"
                    )

                if apply:
                    with connection.cursor() as verify_cursor:
                        for table, column in targets:
                            verify_cursor.execute(
                                sql.SQL(
                                    "SELECT {column} FROM public.{table} "
                                    "WHERE {column} IS NOT NULL AND btrim({column}) <> ''"
                                ).format(
                                    table=sql.Identifier(table),
                                    column=sql.Identifier(column),
                                )
                            )
                            for (blob,) in verify_cursor:
                                if _decode_object(str(blob), current) is None:
                                    raise RotationError(
                                        f"postcondition failed for {table}.{column}"
                                    )
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
        help="Environment file containing DATABASE_URL and the Fernet keyring",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Commit verified re-encryption updates",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Rows to stream at a time (default: {DEFAULT_BATCH_SIZE})",
    )
    parser.add_argument(
        "--only",
        action="append",
        metavar="TABLE.COLUMN",
        help="Limit the run to an allowlisted encrypted column; repeatable",
    )
    args = parser.parse_args()

    try:
        rotate(
            args.env_file,
            apply=args.apply,
            batch_size=args.batch_size,
            only=args.only,
        )
    except Exception as exc:
        print(f"rotation failed ({type(exc).__name__}): {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
