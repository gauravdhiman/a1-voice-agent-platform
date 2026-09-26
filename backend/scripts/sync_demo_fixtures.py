#!/usr/bin/env python3
"""Synchronize the code-owned public demo fixture in a deployed database.

This command is intentionally separate from application startup and from the
local worktree account seed. It creates only the shared public demo tenant,
the three code-owned demo agents, and their repository-owned tool links.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from src.worktree_seed import sync_public_demo_fixtures  # noqa: E402

ALLOWED_ENVIRONMENTS = frozenset({"development", "staging", "production"})


def _required_environment(name: str) -> str:
    """Return a required environment value without printing its contents."""
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required for demo fixture synchronization")
    return value


def main(argv: list[str] | None = None) -> int:
    """Run the guarded public-demo synchronization command."""
    parser = argparse.ArgumentParser(
        description="Synchronize the code-owned public demo agents."
    )
    parser.add_argument(
        "--allow-production",
        action="store_true",
        help="Confirm that this explicit release operation may write production data",
    )
    args = parser.parse_args(argv)

    environment = os.environ.get("ENVIRONMENT", "").strip().lower()
    if environment not in ALLOWED_ENVIRONMENTS:
        print(
            "Demo fixture synchronization requires ENVIRONMENT to be one of: "
            + ", ".join(sorted(ALLOWED_ENVIRONMENTS)),
            file=sys.stderr,
        )
        return 2
    if environment == "production" and not args.allow_production:
        print(
            "Production demo fixture synchronization requires --allow-production.",
            file=sys.stderr,
        )
        return 2

    try:
        result = sync_public_demo_fixtures(
            _required_environment("SUPABASE_URL"),
            _required_environment("SUPABASE_SERVICE_KEY"),
        )
    except Exception as exc:  # pragma: no cover - provider-specific failures
        print(
            "Demo fixture synchronization failed: " f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 2

    print("Public demo fixture synchronized:")
    for key, value in result.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
