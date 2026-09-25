#!/usr/bin/env python3
"""Render a deployment environment from non-secret config + GCP Secret Manager.

The output is intended for a short-lived migration/deploy process.  It is
created with mode 0600 and must be removed by the caller after use.  Secret
values are never printed; only resource names and counts are reported.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from secret_config import (
    SECRET_KEYS,
    normalize_secret_id,
    parse_env_file,
    validate_production_stripe_credentials,
)

DEFAULT_REQUIRED_KEYS = frozenset(
    {
        "SUPABASE_SERVICE_KEY",
        "SUPABASE_ANON_KEY",
        "NEXT_PUBLIC_SUPABASE_ANON_KEY",
        "DATABASE_URL",
        "ENCRYPTION_KEY",
        "JWT_SECRET_KEY",
        "GEMINI_API_KEY",
    }
)


def _fetch_secret(project: str, secret_id: str) -> tuple[str | None, bool]:
    """Fetch one secret version without exposing its value in command output."""

    result = subprocess.run(
        [
            "gcloud",
            "secrets",
            "versions",
            "access",
            "latest",
            f"--secret={secret_id}",
            f"--project={project}",
            "--quiet",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        value = result.stdout.rstrip("\n")
        if not value:
            return None, False
        if "\n" in value or "\r" in value:
            raise RuntimeError(
                f"secret {secret_id} contains a newline; deployment env files "
                "only support single-line secret values"
            )
        return value, True

    # A missing optional secret is allowed.  Other gcloud failures are
    # actionable authentication/IAM/configuration errors and must stop the
    # deployment rather than silently producing a partially configured runtime.
    error = result.stderr.strip()
    if "NOT_FOUND" in error or "not found" in error.lower():
        return None, False
    raise RuntimeError(f"could not read secret {secret_id}: {error or 'gcloud failed'}")


def _write_env(path: Path, values: dict[str, str]) -> None:
    """Write a deterministic, private dotenv file without shell expansion."""

    path.parent.mkdir(parents=True, exist_ok=True)
    content = "".join(f"{key}={value}\n" for key, value in sorted(values.items()))
    try:
        os.chmod(path, 0o600)
    except FileNotFoundError:
        pass
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
        0o600,
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as output:
        output.write(content)
    os.chmod(path, 0o600)


def render(
    config_path: Path,
    output_path: Path,
    project: str,
    prefix: str,
    required_keys: set[str],
) -> tuple[int, int]:
    """Merge the non-secret config with values fetched from Secret Manager."""

    config = parse_env_file(config_path)
    leaked = sorted(key for key in SECRET_KEYS if config.get(key, "").strip())
    if leaked:
        raise ValueError(
            "deployment config contains secret values; move these keys to "
            f"Secret Manager: {', '.join(leaked)}"
        )

    values = {key: value for key, value in config.items() if key not in SECRET_KEYS}
    values["SECRET_MANAGER_MODE"] = "gcp"
    values["GCP_SECRET_NAME_PREFIX"] = prefix

    fetched = 0
    missing_required: list[str] = []
    requested_secret_keys = {key for key in SECRET_KEYS if key in config}
    for key in sorted(SECRET_KEYS):
        # A stale manager version must not become runtime configuration merely
        # because it still exists. Optional secrets are opt-in via an empty
        # ``KEY=`` entry in the non-secret config; required bootstrap keys are
        # always fetched.
        if key not in requested_secret_keys and key not in required_keys:
            continue
        secret_id = normalize_secret_id(prefix, key)
        value, found = _fetch_secret(project, secret_id)
        if found and value is not None:
            values[key] = value
            fetched += 1
        elif key in required_keys:
            missing_required.append(secret_id)

    if missing_required:
        raise ValueError(
            "required Secret Manager versions are missing: "
            + ", ".join(missing_required)
        )

    validate_production_stripe_credentials(
        values,
        production=config.get("ENVIRONMENT", "").strip().lower() == "production",
    )

    _write_env(output_path, values)
    return fetched, len(values)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--secret-prefix", required=True)
    parser.add_argument(
        "--required-key",
        action="append",
        dest="required_keys",
        help="Secret env key that must exist; may be repeated",
    )
    args = parser.parse_args()

    required_keys = (
        set(args.required_keys) if args.required_keys else set(DEFAULT_REQUIRED_KEYS)
    )
    unknown = sorted(required_keys - SECRET_KEYS)
    if unknown:
        parser.error(
            "--required-key is not in the secret inventory: " + ", ".join(unknown)
        )

    try:
        fetched, value_count = render(
            args.config_file,
            args.output,
            args.project,
            args.secret_prefix,
            required_keys,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Secret environment rendering failed: {exc}", file=sys.stderr)
        return 2

    print(
        f"Rendered {value_count} environment values; fetched {fetched} managed secrets."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
