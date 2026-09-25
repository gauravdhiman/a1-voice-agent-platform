#!/usr/bin/env python3
"""Preview or upload voice-ws secrets to OCI Vault.

Preview is the default. ``--apply`` is required for writes and creates a new
OCI secret version rather than deleting or overwriting history. Secret values
are base64-encoded into a short-lived mode-0600 request JSON file because OCI's
base64 commands do not safely accept a ``file://`` URI for the content field.
Values are never placed in command-line arguments or printed.

The command is intended to run from an operator workstation with OCI user
credentials. The voice-ws VM reads the resulting versions with instance
principals through ``oci-fetch-vault-env.sh``.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

_DEPLOY_DIR = str(Path(__file__).resolve().parent)
if _DEPLOY_DIR not in sys.path:  # pragma: no cover - direct test imports
    sys.path.insert(0, _DEPLOY_DIR)

import secret_config  # noqa: E402

SUPPORTED_AUTH_METHODS = (
    "api_key",
    "instance_principal",
    "resource_principal",
    "security_token",
    "oke_workload_identity",
)


class OciSecretSyncError(RuntimeError):
    """Raised when OCI secret synchronization cannot continue safely."""


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    """Run OCI without echoing stdout/stderr, which could contain payloads."""

    return subprocess.run(
        command,
        text=True,
        capture_output=True,
        check=False,
    )


def _oci_prefix(
    *,
    auth: str,
    config_file: Path | None,
    profile: str | None,
) -> list[str]:
    """Build global OCI CLI options without embedding secret material."""

    command = ["oci"]
    if config_file is not None:
        command.extend(["--config-file", str(config_file)])
    if profile:
        command.extend(["--profile", profile])
    command.extend(["--auth", auth])
    return command


def _failure(
    operation: str, result: subprocess.CompletedProcess[str]
) -> OciSecretSyncError:
    """Return a safe operator-facing error without copying CLI output."""

    return OciSecretSyncError(
        f"OCI Vault {operation} failed with exit code {result.returncode}; "
        "rerun with OCI CLI diagnostics outside this tool"
    )


def _find_secret(
    *,
    prefix: list[str],
    compartment_id: str,
    vault_id: str,
    secret_name: str,
) -> str | None:
    """Return the active OCI secret OCID for an exact secret name, if present."""

    result = _run(
        [
            *prefix,
            "vault",
            "secret",
            "list",
            "--compartment-id",
            compartment_id,
            "--vault-id",
            vault_id,
            "--name",
            secret_name,
            "--lifecycle-state",
            "ACTIVE",
            "--all",
            "--query",
            "data[0].id",
            "--raw-output",
        ]
    )
    if result.returncode != 0:
        raise _failure(f"lookup for {secret_name}", result)

    secret_id = result.stdout.strip()
    if not secret_id or secret_id.lower() in {"null", "none"}:
        return None
    if not secret_id.startswith("ocid1.secret."):
        raise OciSecretSyncError(
            f"OCI Vault lookup for {secret_name} returned an invalid secret id"
        )
    return secret_id


def _write_request_file(payload: dict[str, object]) -> Path:
    """Write an OCI request document to a mode-0600 temporary file."""

    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        prefix="247ai-oci-secret-",
        suffix=".json",
        delete=False,
    )
    try:
        path = Path(handle.name)
        json.dump(payload, handle, ensure_ascii=True)
        handle.write("\n")
        handle.flush()
        os.fchmod(handle.fileno(), 0o600)
    finally:
        handle.close()
    return path


def _write_version(
    *,
    prefix: list[str],
    secret_id: str | None,
    compartment_id: str,
    vault_id: str,
    key_id: str,
    secret_name: str,
    value: str,
    version_name: str,
) -> None:
    """Create or update one OCI secret version without exposing its value."""

    if "\n" in value or "\r" in value:
        raise OciSecretSyncError(
            "secret values cannot contain newlines because voice-ws consumes them as env values"
        )
    encoded = base64.b64encode(value.encode("utf-8")).decode("ascii")
    request_payload: dict[str, object] = {
        "secretContentContent": encoded,
        "secretContentName": version_name,
        "secretContentStage": "CURRENT",
    }
    request_path: Path | None = None
    try:
        if secret_id is None:
            request_payload.update(
                {
                    "compartmentId": compartment_id,
                    "keyId": key_id,
                    "secretName": secret_name,
                    "vaultId": vault_id,
                }
            )
            operation = f"create {secret_name}"
            command_name = "create-base64"
        else:
            request_payload["secretId"] = secret_id
            operation = f"update {secret_name}"
            command_name = "update-base64"

        request_path = _write_request_file(request_payload)
        command = [
            *prefix,
            "vault",
            "secret",
            command_name,
            "--from-json",
            f"file://{request_path}",
        ]

        result = _run(command)
        if result.returncode != 0:
            raise _failure(operation, result)
    finally:
        try:
            if request_path is not None:
                request_path.unlink()
        except FileNotFoundError:
            pass


def _selected_keys(env: dict[str, str], only: list[str] | None) -> list[str]:
    """Return worker secret keys to sync, rejecting arbitrary env names."""

    worker_keys = secret_config.service_secret_keys("voice-ws")
    if only:
        unsupported = sorted(set(only) - worker_keys)
        if unsupported:
            raise OciSecretSyncError(
                "unsupported --only key(s): " + ", ".join(unsupported)
            )
        selected = sorted(set(only))
    else:
        selected = secret_config.configured_secret_keys(env, "voice-ws")

    required = secret_config.SERVICE_REQUIRED_SECRET_KEYS["voice-ws"]
    missing = sorted(key for key in required if not env.get(key, "").strip())
    if missing:
        raise OciSecretSyncError(
            "required voice-ws deployment secrets are missing or empty: "
            + ", ".join(missing)
        )
    if not selected:
        raise OciSecretSyncError("no configured voice-ws deployment secrets found")
    return selected


def sync(
    env_file: Path,
    compartment_id: str,
    vault_id: str,
    key_id: str,
    secret_prefix: str,
    *,
    apply: bool,
    auth: str,
    config_file: Path | None = None,
    profile: str | None = None,
    only: list[str] | None = None,
) -> int:
    """Preview or synchronize configured voice-ws secrets and return a count."""

    env = secret_config.parse_env_file(env_file)
    keys = _selected_keys(env, only)
    prefix = _oci_prefix(
        auth=auth,
        config_file=config_file,
        profile=profile,
    )
    version_stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

    for key in keys:
        secret_name = secret_config.normalize_secret_id(secret_prefix, key)
        if not apply:
            print(secret_name)
            continue

        secret_id = _find_secret(
            prefix=prefix,
            compartment_id=compartment_id,
            vault_id=vault_id,
            secret_name=secret_name,
        )
        version_name = f"sync-{version_stamp}-{key.lower().replace('_', '-') }"
        try:
            _write_version(
                prefix=prefix,
                secret_id=secret_id,
                compartment_id=compartment_id,
                vault_id=vault_id,
                key_id=key_id,
                secret_name=secret_name,
                value=env[key],
                version_name=version_name,
            )
        except OciSecretSyncError:
            if secret_id is not None:
                raise
            # A second operator may have created this secret after our lookup.
            # Re-read and update its current version rather than failing with a
            # duplicate-create race.
            secret_id = _find_secret(
                prefix=prefix,
                compartment_id=compartment_id,
                vault_id=vault_id,
                secret_name=secret_name,
            )
            if secret_id is None:
                raise
            _write_version(
                prefix=prefix,
                secret_id=secret_id,
                compartment_id=compartment_id,
                vault_id=vault_id,
                key_id=key_id,
                secret_name=secret_name,
                value=env[key],
                version_name=version_name,
            )
        print(f"updated {secret_name}")
    return len(keys)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--compartment-id", required=True)
    parser.add_argument("--vault-id", required=True)
    parser.add_argument(
        "--key-id",
        required=True,
        help="OCID of the OCI Vault master encryption key used for new secrets",
    )
    parser.add_argument("--secret-prefix", required=True)
    parser.add_argument(
        "--only",
        action="append",
        help="Sync only this voice-ws secret key; repeat for multiple keys",
    )
    parser.add_argument(
        "--auth",
        choices=SUPPORTED_AUTH_METHODS,
        default="api_key",
        help="OCI authentication method (default: api_key)",
    )
    parser.add_argument("--config-file", type=Path)
    parser.add_argument("--profile")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Create missing secrets and add new versions; preview otherwise",
    )
    args = parser.parse_args()

    try:
        count = sync(
            args.env_file,
            args.compartment_id,
            args.vault_id,
            args.key_id,
            args.secret_prefix,
            apply=args.apply,
            auth=args.auth,
            config_file=args.config_file,
            profile=args.profile,
            only=args.only,
        )
    except (OSError, OciSecretSyncError, ValueError) as exc:
        print(f"OCI secret synchronization failed: {exc}", file=sys.stderr)
        return 2

    action = "Synchronized" if args.apply else "Previewed"
    print(f"{action} {count} secret names.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
