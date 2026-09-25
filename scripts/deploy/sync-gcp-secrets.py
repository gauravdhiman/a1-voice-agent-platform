#!/usr/bin/env python3
"""Preview or upload deployment secrets to Google Secret Manager.

Preview is the default.  ``--apply`` is required for writes and adds a new
version without deleting or overwriting an existing version.  Secret values are
passed to gcloud over stdin and are never printed.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

from secret_config import (
    SECRET_KEYS,
    normalize_secret_id,
    parse_env_file,
    validate_production_stripe_credentials,
)


PRODUCTION_PREFIX = re.compile(r"(?:^|[-_.])(?:production|prod)$", re.IGNORECASE)


def _is_production_prefix(prefix: str) -> bool:
    """Return whether a secret prefix unambiguously names production."""

    return bool(PRODUCTION_PREFIX.search(prefix.strip()))


def _validate_production_secret_modes(env: dict[str, str], prefix: str) -> None:
    """Prevent test Stripe credentials from entering production Secret Manager."""

    if _is_production_prefix(prefix):
        validate_production_stripe_credentials(env, production=True)


def _run(
    command: list[str], *, input_value: str | None = None
) -> subprocess.CompletedProcess[str]:
    """Run gcloud without echoing stdout/stderr, which could contain payloads."""

    return subprocess.run(
        command,
        input=input_value,
        text=True,
        capture_output=True,
        check=False,
    )


def _ensure_secret(project: str, secret_id: str) -> None:
    described = _run(
        ["gcloud", "secrets", "describe", secret_id, f"--project={project}", "--quiet"]
    )
    if described.returncode == 0:
        return

    created = _run(
        [
            "gcloud",
            "secrets",
            "create",
            secret_id,
            f"--project={project}",
            "--replication-policy=automatic",
            "--quiet",
        ]
    )
    if created.returncode != 0:
        # A concurrent first-time bootstrap may have created the secret after
        # the describe.  Verify before failing.
        described_again = _run(
            [
                "gcloud",
                "secrets",
                "describe",
                secret_id,
                f"--project={project}",
                "--quiet",
            ]
        )
        if described_again.returncode != 0:
            detail = created.stderr.strip() or "gcloud secret creation failed"
            raise RuntimeError(f"could not create secret {secret_id}: {detail}")


def sync(env_file: Path, project: str, prefix: str, apply: bool) -> int:
    """Synchronize configured secret values and return the number of versions."""

    env = parse_env_file(env_file)
    _validate_production_secret_modes(env, prefix)
    configured = [key for key in sorted(SECRET_KEYS) if env.get(key, "").strip()]
    if not configured:
        raise ValueError("no configured deployment secrets found in the env file")

    for key in configured:
        secret_id = normalize_secret_id(prefix, key)
        if not apply:
            print(secret_id)
            continue
        _ensure_secret(project, secret_id)
        added = _run(
            [
                "gcloud",
                "secrets",
                "versions",
                "add",
                secret_id,
                f"--project={project}",
                "--data-file=-",
                "--quiet",
            ],
            input_value=env[key],
        )
        if added.returncode != 0:
            detail = added.stderr.strip() or "gcloud secret version creation failed"
            raise RuntimeError(f"could not add a version to {secret_id}: {detail}")
        print(f"updated {secret_id}")
    return len(configured)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--secret-prefix", required=True)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Create missing secrets and add new versions; preview otherwise",
    )
    args = parser.parse_args()

    try:
        count = sync(args.env_file, args.project, args.secret_prefix, args.apply)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Secret synchronization failed: {exc}", file=sys.stderr)
        return 2

    action = "Synchronized" if args.apply else "Previewed"
    print(f"{action} {count} secret names.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
