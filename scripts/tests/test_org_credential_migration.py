"""Tests for the staged organization credential hardening migration."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from shared.common.security import decrypt_data, encrypt_data

MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "backend"
    / "alembic"
    / "versions"
    / "20260922000002_migrate_legacy_org_provider_credentials.py"
)
SPEC = importlib.util.spec_from_file_location(
    "org_credential_migration", MIGRATION_PATH
)
assert SPEC and SPEC.loader
migration = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(migration)


def test_migration_preserves_existing_providers_and_adds_legacy_google() -> None:
    """Existing encrypted providers survive the plaintext cleanup."""
    encrypted_payloads: list[dict[str, str]] = []

    def decrypt(_: str) -> dict[str, str]:
        return {"openai": "existing-test-key"}

    def encrypt(payload: dict[str, str] | None) -> str:
        assert payload is not None
        encrypted_payloads.append(payload)
        return "new-ciphertext"

    result = migration._migrate_credential_blob(
        "old-ciphertext", "legacy-test-key", decrypt, encrypt
    )

    assert result == "new-ciphertext"
    assert encrypted_payloads == [
        {"openai": "existing-test-key", "google": "legacy-test-key"}
    ]


def test_migration_does_not_replace_existing_google_credential() -> None:
    """An already-encrypted Google key remains the source of truth."""
    captured: list[dict[str, str]] = []

    result = migration._migrate_credential_blob(
        "old-ciphertext",
        "legacy-test-key",
        lambda _: {"google": "encrypted-test-key"},
        lambda payload: captured.append(payload or {}) or "ciphertext",
    )

    assert result == "ciphertext"
    assert captured == [{"google": "encrypted-test-key"}]


def test_migration_fails_closed_on_unreadable_existing_ciphertext() -> None:
    """A key mismatch must leave the legacy value untouched for investigation."""
    with pytest.raises(RuntimeError, match="refusing to clear"):
        migration._migrate_credential_blob(
            "unreadable-ciphertext",
            "legacy-test-key",
            lambda _: {},
            lambda _: "should-not-run",
        )


def test_migration_clears_empty_legacy_value_without_creating_blob() -> None:
    """Empty legacy values do not create meaningless encrypted payloads."""
    encrypted = False

    def encrypt(_: dict[str, str] | None) -> str:
        nonlocal encrypted
        encrypted = True
        return "should-not-run"

    result = migration._migrate_credential_blob(None, "", lambda _: {}, encrypt)

    assert result is None
    assert encrypted is False


def test_migration_reencrypts_with_current_key_and_preserves_fallback_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Existing ciphertext written by the rotation fallback remains readable."""
    current_key = Fernet.generate_key().decode()
    previous_key = Fernet.generate_key().decode()

    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("ENCRYPTION_KEY", previous_key)
    monkeypatch.delenv("ENCRYPTION_KEY_FALLBACKS", raising=False)
    old_blob = encrypt_data({"openai": "existing-test-key"})

    monkeypatch.setenv("ENCRYPTION_KEY", current_key)
    monkeypatch.setenv("ENCRYPTION_KEY_FALLBACKS", previous_key)
    migrated = migration._migrate_credential_blob(
        old_blob,
        "legacy-test-key",
        decrypt_data,
        encrypt_data,
    )

    assert migrated
    assert decrypt_data(migrated) == {
        "openai": "existing-test-key",
        "google": "legacy-test-key",
    }
    assert os.environ["ENCRYPTION_KEY"] == current_key
