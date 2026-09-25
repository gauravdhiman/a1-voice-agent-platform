"""Tests for guarded OCI Vault secret synchronization."""

from __future__ import annotations

import base64
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "deploy" / "sync-oci-secrets.py"
SPEC = importlib.util.spec_from_file_location("oci_secret_sync", SCRIPT_PATH)
assert SPEC and SPEC.loader
oci_sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(oci_sync)


REQUIRED_ENV = {
    "ENCRYPTION_KEY": "super-secret-fernet-value",
    "JWT_SECRET_KEY": "super-secret-jwt-value",
    "SUPABASE_SERVICE_KEY": "super-secret-supabase-value",
    "GEMINI_API_KEY": "super-secret-gemini-value",
    "OPENAI_API_KEY": "super-secret-openai-value",
}


def _write_env(path: Path, values: dict[str, str] | None = None) -> None:
    source = values or REQUIRED_ENV
    path.write_text(
        "\n".join(f"{key}={value}" for key, value in source.items()) + "\n",
        encoding="utf-8",
    )


def test_preview_never_calls_oci_or_prints_secret_values(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The default mode is a names-only plan."""
    env_file = tmp_path / "prod.env"
    _write_env(env_file)
    calls: list[list[str]] = []
    monkeypatch.setattr(oci_sync, "_run", lambda command: calls.append(command))

    count = oci_sync.sync(
        env_file,
        "ocid1.compartment.example",
        "ocid1.vault.example",
        "ocid1.key.example",
        "247ai-production",
        apply=False,
        auth="api_key",
    )

    output = capsys.readouterr().out
    assert count == 5
    assert "247ai-production-gemini-api-key" in output
    assert "super-secret-gemini-value" not in output
    assert calls == []


def test_apply_uses_file_input_and_creates_or_updates_versions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Apply mode never puts a value in an OCI command argument."""
    env_file = tmp_path / "prod.env"
    _write_env(env_file)
    calls: list[list[str]] = []
    encoded_payloads: list[str] = []

    def fake_run(command: list[str]) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        if "list" in command:
            secret_name = command[command.index("--name") + 1]
            if secret_name.endswith("gemini-api-key"):
                return subprocess.CompletedProcess(
                    command, 0, "ocid1.secret.existing\n", ""
                )
            return subprocess.CompletedProcess(command, 0, "\n", "")

        request_arg = command[command.index("--from-json") + 1]
        assert request_arg.startswith("file://")
        request_path = Path(request_arg.removeprefix("file://"))
        request = json.loads(request_path.read_text(encoding="utf-8"))
        encoded_payloads.append(request["secretContentContent"])
        assert all(value not in command for value in REQUIRED_ENV.values())
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(oci_sync, "_run", fake_run)

    count = oci_sync.sync(
        env_file,
        "ocid1.compartment.example",
        "ocid1.vault.example",
        "ocid1.key.example",
        "247ai-production",
        apply=True,
        auth="api_key",
        profile="DEFAULT",
    )

    assert count == 5
    assert any("create-base64" in command for command in calls)
    assert any("update-base64" in command for command in calls)
    assert all(
        base64.b64decode(payload).decode("utf-8") in REQUIRED_ENV.values()
        for payload in encoded_payloads
    )
    assert all(
        command[:4] == ["oci", "--profile", "DEFAULT", "--auth"] for command in calls
    )


def test_missing_required_secret_fails_before_oci_call(tmp_path: Path) -> None:
    """A partially configured env file cannot create an incomplete worker vault."""
    env_file = tmp_path / "prod.env"
    _write_env(env_file, {"ENCRYPTION_KEY": "super-secret-fernet-value"})

    with pytest.raises(oci_sync.OciSecretSyncError, match="required voice-ws"):
        oci_sync.sync(
            env_file,
            "ocid1.compartment.example",
            "ocid1.vault.example",
            "ocid1.key.example",
            "247ai-production",
            apply=False,
            auth="api_key",
        )


def test_only_rejects_non_worker_key(tmp_path: Path) -> None:
    """The scoped selector cannot be used to upload arbitrary env values."""
    env_file = tmp_path / "prod.env"
    _write_env(env_file)

    with pytest.raises(oci_sync.OciSecretSyncError, match="unsupported --only"):
        oci_sync.sync(
            env_file,
            "ocid1.compartment.example",
            "ocid1.vault.example",
            "ocid1.key.example",
            "247ai-production",
            apply=False,
            auth="api_key",
            only=["DATABASE_URL"],
        )
