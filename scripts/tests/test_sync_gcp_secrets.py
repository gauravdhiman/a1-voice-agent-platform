"""Regression tests for production secret synchronization guardrails."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "deploy" / "sync-gcp-secrets.py"
SPEC = importlib.util.spec_from_file_location("sync_gcp_secrets", SCRIPT)
assert SPEC and SPEC.loader
sync_gcp_secrets = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync_gcp_secrets)


def test_production_sync_rejects_test_stripe_secret_before_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / "production.env"
    env_file.write_text(
        "STRIPE_SECRET_KEY=sk_test_example\nGEMINI_API_KEY=provider-secret\n",
        encoding="utf-8",
    )

    def fail_if_called(*args: object, **kwargs: object) -> None:
        raise AssertionError("gcloud must not be called for rejected credentials")

    monkeypatch.setattr(sync_gcp_secrets, "_run", fail_if_called)

    with pytest.raises(ValueError, match="test Stripe credential"):
        sync_gcp_secrets.sync(
            env_file,
            project="project-id",
            prefix="247ai-production",
            apply=True,
        )


def test_nonproduction_sync_allows_test_stripe_secret(tmp_path: Path) -> None:
    env_file = tmp_path / "staging.env"
    env_file.write_text(
        "STRIPE_SECRET_KEY=sk_test_example\n",
        encoding="utf-8",
    )

    assert (
        sync_gcp_secrets.sync(
            env_file,
            project="project-id",
            prefix="247ai-staging",
            apply=False,
        )
        == 1
    )


def test_production_sync_allows_test_stripe_only_in_explicit_soft_mode(
    tmp_path: Path,
) -> None:
    env_file = tmp_path / "production.env"
    env_file.write_text(
        "STRIPE_MODE=test\nSTRIPE_SECRET_KEY=sk_test_example\n",
        encoding="utf-8",
    )

    assert (
        sync_gcp_secrets.sync(
            env_file,
            project="project-id",
            prefix="247ai-production",
            apply=False,
        )
        == 1
    )


def test_production_sync_rejects_test_stripe_publishable_key(
    tmp_path: Path,
) -> None:
    env_file = tmp_path / "production.env"
    env_file.write_text(
        "NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_example\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="test Stripe credential"):
        sync_gcp_secrets.sync(
            env_file,
            project="project-id",
            prefix="247ai-production",
            apply=False,
        )
