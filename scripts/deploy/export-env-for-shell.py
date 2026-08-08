#!/usr/bin/env python3
"""Emit shell export statements for a dotenv file (safe for sourcing in bash).

Skips values that contain characters problematic for naive ``source`` parsing.
Use read-env-cloud.py for single-key lookup in scripts.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def _shell_escape(value: str) -> str:
    """Return a value safe to wrap in single quotes for bash export."""
    return "'" + value.replace("'", "'\"'\"'") + "'"


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: export-env-for-shell.py <env-file>", file=sys.stderr)
        return 1

    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"missing env file: {path}", file=sys.stderr)
        return 1

    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", key):
            continue
        # Skip unquoted values with spaces (handled via read-env-cloud for DATABASE_URL)
        if " " in value and not (
            value.startswith('"') or value.startswith("'") or value.startswith("[")
        ):
            continue
        print(f"export {key}={_shell_escape(value)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
