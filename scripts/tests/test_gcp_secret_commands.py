"""Regression tests for GCP Secret Manager CLI argument contracts."""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest


def _load_module(name: str, filename: str):
    path = Path(__file__).resolve().parents[1] / "deploy" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gcp_secret_refs = _load_module("gcp_secret_refs", "gcp-secret-refs.py")
render_gcp_env = _load_module("render_gcp_env_commands", "render-gcp-env.py")


def test_current_version_passes_secret_id_positionally(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The current gcloud CLI takes the secret resource as a positional arg."""

    calls: list[list[str]] = []

    def fake_run(
        command: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "7\n", "")

    monkeypatch.setattr(gcp_secret_refs.subprocess, "run", fake_run)

    assert gcp_secret_refs._current_version("project-id", "secret-id") == "7"
    command = calls[0]
    assert command[:5] == ["gcloud", "secrets", "versions", "list", "secret-id"]
    assert "--secret=secret-id" not in command


def test_fetch_secret_passes_secret_id_with_required_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Secret value access uses the access command's required named flag."""

    calls: list[list[str]] = []

    def fake_run(
        command: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "value\n", "")

    monkeypatch.setattr(render_gcp_env.subprocess, "run", fake_run)

    assert render_gcp_env._fetch_secret("project-id", "secret-id") == ("value", True)
    command = calls[0]
    assert command[:6] == [
        "gcloud",
        "secrets",
        "versions",
        "access",
        "latest",
        "--secret=secret-id",
    ]
    assert command[5] == "--secret=secret-id"


def test_render_rejects_test_stripe_secret_for_production(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = tmp_path / "production.env"
    output = tmp_path / ".env.prod"
    config.write_text(
        "ENVIRONMENT=production\nSTRIPE_SECRET_KEY=\n",
        encoding="utf-8",
    )

    def fake_fetch(project: str, secret_id: str) -> tuple[str | None, bool]:
        del project
        if secret_id.endswith("stripe-secret-key"):
            return "sk_test_example", True
        return None, False

    monkeypatch.setattr(render_gcp_env, "_fetch_secret", fake_fetch)

    with pytest.raises(ValueError, match="test Stripe credential"):
        render_gcp_env.render(
            config,
            output,
            project="project-id",
            prefix="247ai-production",
            required_keys=set(),
        )

    assert not output.exists()
