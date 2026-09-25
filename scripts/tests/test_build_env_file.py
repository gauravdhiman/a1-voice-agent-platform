"""Tests for the versioned-config plus private-overlay environment builder."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "deploy" / "build-env-file.py"
SPEC = importlib.util.spec_from_file_location("build_env_file", SCRIPT)
assert SPEC and SPEC.loader
build_env_file = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build_env_file)


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def test_build_merges_only_secret_overlay_values(tmp_path: Path) -> None:
    config = tmp_path / "production.env"
    secrets = tmp_path / ".env.prod.secrets"
    output = tmp_path / ".env.prod"
    _write(config, "APP_NAME=24x7 AI\nENCRYPTION_KEY=\nJWT_SECRET_KEY=\n")
    _write(secrets, "ENCRYPTION_KEY=key-one\nJWT_SECRET_KEY=jwt-one\n")

    count = build_env_file.build(config, secrets, output)

    assert count == 3
    assert output.read_text(encoding="utf-8") == (
        "APP_NAME=24x7 AI\nENCRYPTION_KEY=key-one\nJWT_SECRET_KEY=jwt-one\n"
    )
    assert os.stat(output).st_mode & 0o777 == 0o600


def test_build_rejects_secret_in_versioned_config(tmp_path: Path) -> None:
    config = tmp_path / "production.env"
    secrets = tmp_path / ".env.prod.secrets"
    output = tmp_path / ".env.prod"
    _write(config, "ENCRYPTION_KEY=do-not-commit\n")
    _write(secrets, "ENCRYPTION_KEY=key-one\n")

    with pytest.raises(ValueError, match="versioned config contains secret values"):
        build_env_file.build(config, secrets, output)


def test_build_rejects_non_secret_overlay_values(tmp_path: Path) -> None:
    config = tmp_path / "production.env"
    secrets = tmp_path / ".env.prod.secrets"
    output = tmp_path / ".env.prod"
    _write(config, "APP_NAME=24x7 AI\nENCRYPTION_KEY=\n")
    _write(secrets, "APP_NAME=wrong-place\nENCRYPTION_KEY=key-one\n")

    with pytest.raises(ValueError, match="non-secret values belong"):
        build_env_file.build(config, secrets, output)


def test_build_rejects_undeclared_overlay_key(tmp_path: Path) -> None:
    config = tmp_path / "production.env"
    secrets = tmp_path / ".env.prod.secrets"
    output = tmp_path / ".env.prod"
    _write(config, "ENCRYPTION_KEY=\n")
    _write(secrets, "JWT_SECRET_KEY=jwt-one\n")

    with pytest.raises(ValueError, match="not declared"):
        build_env_file.build(config, secrets, output)
