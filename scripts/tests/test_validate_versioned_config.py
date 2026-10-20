"""Tests for version-controlled deployment configuration validation."""

from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "deploy" / "validate-versioned-config.py"
SPEC = importlib.util.spec_from_file_location("validate_versioned_config", SCRIPT)
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)

ROOT = Path(__file__).resolve().parents[2]


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _valid_config() -> str:
    return """\
APP_NAME=24x7 AI
APP_BASE_URL=https://www.247ai.live
ENVIRONMENT=production
API_BASE_URL=https://api.247ai.live
CORS_ORIGINS=[\"https://www.247ai.live\"]
NEXT_PUBLIC_API_URL=https://api.247ai.live
NEXT_PUBLIC_APP_NAME=24x7 AI
SECRET_MANAGER_MODE=gcp
GCP_SECRET_MANAGER_PROJECT_ID=project-id
GCP_SECRET_NAME_PREFIX=247ai-production
GCP_BACKEND_RUNTIME_SERVICE_ACCOUNT=backend@project-id.iam.gserviceaccount.com
OCI_VAULT_ID=ocid1.vault.oc1.abc123
OCI_SECRET_NAME_PREFIX=247ai-production
STRIPE_MODE=live
ENCRYPTION_KEY=
OTEL_ENABLED=false
OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=https://example.invalid/traces
"""


def test_valid_production_config_has_no_errors(tmp_path: Path) -> None:
    path = tmp_path / "production.env"
    _write(path, _valid_config())

    assert (
        validator.validate(path, environment="production", project="project-id") == []
    )


def test_production_config_rejects_secret_values(tmp_path: Path) -> None:
    path = tmp_path / "production.env"
    _write(path, _valid_config().replace("ENCRYPTION_KEY=", "ENCRYPTION_KEY=secret"))

    errors = validator.validate(path, environment="production", project="project-id")

    assert any("secret values" in error for error in errors)


def test_production_config_rejects_placeholders(tmp_path: Path) -> None:
    path = tmp_path / "production.env"
    _write(
        path,
        _valid_config().replace(
            "OCI_VAULT_ID=ocid1.vault.oc1.abc123", "OCI_VAULT_ID=replace-with-vault"
        ),
    )

    errors = validator.validate(path, environment="production", project="project-id")

    assert any("placeholder" in error and "OCI_VAULT_ID" in error for error in errors)


def test_production_config_rejects_test_stripe_publishable_key(tmp_path: Path) -> None:
    path = tmp_path / "production.env"
    _write(
        path,
        _valid_config() + "NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_example\n",
    )

    errors = validator.validate(path, environment="production", project="project-id")

    assert any("NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY" in error for error in errors)


def test_production_config_accepts_test_stripe_in_explicit_soft_mode(
    tmp_path: Path,
) -> None:
    path = tmp_path / "production.env"
    _write(
        path,
        _valid_config().replace("STRIPE_MODE=live", "STRIPE_MODE=test")
        + "NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_abc123\n",
    )

    assert (
        validator.validate(path, environment="production", project="project-id") == []
    )


def test_production_config_rejects_live_stripe_in_test_mode(tmp_path: Path) -> None:
    path = tmp_path / "production.env"
    _write(
        path,
        _valid_config().replace("STRIPE_MODE=live", "STRIPE_MODE=test")
        + "STRIPE_SECRET_KEY=sk_live_example\n",
    )

    errors = validator.validate(path, environment="production", project="project-id")

    assert any(
        "STRIPE_SECRET_KEY" in error and "STRIPE_MODE=test" in error for error in errors
    )


def test_checked_in_environment_configs_contain_no_secret_values() -> None:
    for path in (
        ROOT / "deploy/config/local.env",
        ROOT / "deploy/config/staging.env",
        ROOT / "deploy/config/production.env",
    ):
        values = validator.parse_env_file(path)
        # Optional managed secrets may be absent or blank in public config.
        # Their absence must not force copying private values into this file.
        assert {"DATABASE_URL", "ENCRYPTION_KEY", "JWT_SECRET_KEY"} <= set(values)
        leaked = [key for key in validator.SECRET_KEYS if values.get(key, "").strip()]
        assert leaked == [], f"secret values found in {path}: {leaked}"
