#!/usr/bin/env python3
"""Build a private runtime env file from versioned config and a secret overlay.

The checked-in config is the source of truth for non-secret values. The
overlay is ignored by Git and may contain only values from the shared secret
inventory. The output is a short-lived, mode-0600 runtime file for local or
manual operations; managed cloud releases should fetch values directly from
GCP Secret Manager or OCI Vault instead.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

try:
    from secret_config import SECRET_KEYS, parse_env_file
except ModuleNotFoundError:  # pragma: no cover - supports direct execution
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from secret_config import SECRET_KEYS, parse_env_file


def _write_private_env(path: Path, values: dict[str, str]) -> None:
    """Write deterministic dotenv content with mode 0600 permissions."""

    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
        0o600,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            for key in sorted(values):
                output.write(f"{key}={values[key]}\n")
    finally:
        os.chmod(path, 0o600)


def build(config_file: Path, secret_file: Path, output_file: Path) -> int:
    """Merge safe config with a validated local secret overlay."""

    config = parse_env_file(config_file)
    overlay = parse_env_file(secret_file)

    config_secrets = sorted(key for key in SECRET_KEYS if config.get(key, "").strip())
    if config_secrets:
        raise ValueError(
            "versioned config contains secret values; move these keys to the "
            "ignored overlay: " + ", ".join(config_secrets)
        )

    unknown = sorted(set(overlay) - set(config))
    if unknown:
        raise ValueError(
            "secret overlay contains keys not declared by the versioned "
            "config: " + ", ".join(unknown)
        )

    non_secret_overlay = sorted(
        key
        for key, value in overlay.items()
        if key not in SECRET_KEYS and value.strip()
    )
    if non_secret_overlay:
        raise ValueError(
            "non-secret values belong in versioned config, not the secret "
            "overlay: " + ", ".join(non_secret_overlay)
        )

    merged = dict(config)
    merged.update(overlay)
    _write_private_env(output_file, merged)
    return len(merged)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config-file", type=Path, required=True)
    parser.add_argument("--secret-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        count = build(args.config_file, args.secret_file, args.output)
    except (OSError, ValueError) as exc:
        print(f"Environment build failed: {exc}", file=sys.stderr)
        return 2

    print(f"Wrote {count} environment assignments to {args.output}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
