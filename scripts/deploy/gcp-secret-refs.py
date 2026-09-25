#!/usr/bin/env python3
"""Resolve pinned Secret Manager version references for Cloud Run."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from secret_config import configured_secret_keys, normalize_secret_id, parse_env_file


def _current_version(project: str, secret_id: str) -> str:
    """Return the newest enabled numeric version without reading its value."""

    result = subprocess.run(
        [
            "gcloud",
            "secrets",
            "versions",
            "list",
            secret_id,
            f"--project={project}",
            "--filter=state=ENABLED",
            "--sort-by=~createTime",
            "--limit=1",
            "--format=value(name)",
            "--quiet",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or "gcloud secret version lookup failed"
        raise RuntimeError(f"could not resolve version for {secret_id}: {detail}")
    version = result.stdout.strip().rsplit("/", 1)[-1]
    if not version.isdigit():
        raise RuntimeError(f"secret {secret_id} has no enabled numeric version")
    return version


def resolve(env_file: Path, project: str, service: str, prefix: str) -> str:
    """Build the comma-separated ``KEY=SECRET:VERSION`` Cloud Run flag."""

    env = parse_env_file(env_file)
    refs: list[str] = []
    for key in configured_secret_keys(env, service):
        secret_id = normalize_secret_id(prefix, key)
        version = _current_version(project, secret_id)
        refs.append(f"{key}={secret_id}:{version}")
    if not refs:
        raise ValueError(f"no configured secrets found for service {service}")
    return ",".join(refs)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--service", choices=["backend", "voice-ws"], required=True)
    parser.add_argument("--secret-prefix", required=True)
    args = parser.parse_args()

    try:
        print(resolve(args.env_file, args.project, args.service, args.secret_prefix))
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Cloud Run secret reference generation failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
