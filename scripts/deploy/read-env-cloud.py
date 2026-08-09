#!/usr/bin/env python3
"""Print a single key from .env.prod (for deploy scripts)."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: read-env-cloud.py <env-file> <KEY>", file=sys.stderr)
        return 1
    path = Path(sys.argv[1])
    key = sys.argv[2]
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        if k.strip() == key:
            print(v.strip())
            return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
