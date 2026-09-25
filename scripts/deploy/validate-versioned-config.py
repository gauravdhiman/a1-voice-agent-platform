#!/usr/bin/env python3
"""Validate a version-controlled, non-secret deployment configuration."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    from secret_config import (
        SECRET_KEYS,
        parse_env_file,
        validate_production_stripe_credentials,
    )
except ModuleNotFoundError:  # pragma: no cover - supports direct execution
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from secret_config import (
        SECRET_KEYS,
        parse_env_file,
        validate_production_stripe_credentials,
    )


PLACEHOLDER = re.compile(
    r"(?:replace[-_ ]?with|your[-_]|example(?:\.|[-_]|$)|change[-_]?me|dummy)",
    re.IGNORECASE,
)

COMMON_REQUIRED_KEYS = (
    "APP_NAME",
    "APP_BASE_URL",
    "ENVIRONMENT",
    "API_BASE_URL",
    "CORS_ORIGINS",
    "NEXT_PUBLIC_API_URL",
    "NEXT_PUBLIC_APP_NAME",
)

CLOUD_REQUIRED_KEYS = (
    "SECRET_MANAGER_MODE",
    "GCP_SECRET_MANAGER_PROJECT_ID",
    "GCP_SECRET_NAME_PREFIX",
    "GCP_BACKEND_RUNTIME_SERVICE_ACCOUNT",
    "OCI_VAULT_ID",
    "OCI_SECRET_NAME_PREFIX",
)


def _is_placeholder(value: str) -> bool:
    return bool(PLACEHOLDER.search(value))


def validate(
    config_file: Path,
    *,
    environment: str,
    project: str | None = None,
) -> list[str]:
    """Return actionable validation errors without exposing secret values."""

    env = parse_env_file(config_file)
    errors: list[str] = []

    leaked = sorted(key for key in SECRET_KEYS if env.get(key, "").strip())
    if leaked:
        errors.append("versioned config contains secret values: " + ", ".join(leaked))

    for key in COMMON_REQUIRED_KEYS:
        if not env.get(key, "").strip():
            errors.append(f"missing required config: {key}")

    actual_environment = env.get("ENVIRONMENT", "").strip().lower()
    if actual_environment != environment:
        errors.append(
            f"ENVIRONMENT={actual_environment or '<empty>'} does not match "
            f"--environment {environment}"
        )

    if environment in {"staging", "production"}:
        for key in CLOUD_REQUIRED_KEYS:
            if not env.get(key, "").strip():
                errors.append(f"missing required cloud config: {key}")
        if env.get("SECRET_MANAGER_MODE", "").strip().lower() != "gcp":
            errors.append("cloud deployment config must set SECRET_MANAGER_MODE=gcp")

        if project and env.get("GCP_SECRET_MANAGER_PROJECT_ID", "").strip() not in {
            "",
            project,
        }:
            errors.append(
                "GCP_SECRET_MANAGER_PROJECT_ID must match the deployment project"
            )

    if environment == "production":
        try:
            validate_production_stripe_credentials(env, production=True)
        except ValueError as exc:
            errors.append(str(exc))

    # Observability endpoints may intentionally be placeholders while the
    # feature is disabled. All other populated config values must be real.
    skip_placeholder_keys = {
        key
        for key in env
        if key.startswith("OTEL_EXPORTER_OTLP_")
        or key.startswith("NEXT_PUBLIC_OTEL_EXPORTER_OTLP_")
    }
    telemetry_disabled = env.get("OTEL_ENABLED", "").strip().lower() != "true"
    browser_telemetry_disabled = (
        env.get("NEXT_PUBLIC_OTEL_ENABLED", "").strip().lower() != "true"
    )
    for key, value in env.items():
        if not value.strip():
            continue
        if key in skip_placeholder_keys and telemetry_disabled:
            continue
        if (
            key.startswith("NEXT_PUBLIC_OTEL_EXPORTER_OTLP_")
            and browser_telemetry_disabled
        ):
            continue
        if _is_placeholder(value):
            errors.append(f"placeholder value is not allowed for config: {key}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config-file", type=Path, required=True)
    parser.add_argument(
        "--environment", choices=["staging", "production"], required=True
    )
    parser.add_argument("--project")
    args = parser.parse_args()

    try:
        errors = validate(
            args.config_file,
            environment=args.environment,
            project=args.project,
        )
    except (OSError, ValueError) as exc:
        print(f"Configuration validation failed: {exc}", file=sys.stderr)
        return 2

    if errors:
        print("Configuration validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 2

    print(f"Validated non-secret {args.environment} configuration.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
