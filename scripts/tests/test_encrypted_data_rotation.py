"""Tests for guarded application-ciphertext key rotation."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

ROTATION_PATH = (
    Path(__file__).resolve().parents[1] / "deploy" / "rotate-encrypted-data.py"
)
SPEC = importlib.util.spec_from_file_location("encrypted_data_rotation", ROTATION_PATH)
assert SPEC and SPEC.loader
rotation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rotation)


def test_rotate_blob_reencrypts_with_current_key() -> None:
    """Fallback ciphertext is rewritten and remains the same JSON payload."""
    current_key = Fernet.generate_key().decode()
    previous_key = Fernet.generate_key().decode()
    current = Fernet(current_key.encode())
    keyring = rotation.MultiFernet([current, Fernet(previous_key.encode())])
    payload = {"provider": "opaque-test-value"}
    old_blob = (
        Fernet(previous_key.encode()).encrypt(json.dumps(payload).encode()).decode()
    )

    rotated, used_fallback = rotation.rotate_blob(
        old_blob, current=current, keyring=keyring
    )

    assert used_fallback is True
    assert rotated
    assert json.loads(current.decrypt(rotated.encode()).decode()) == payload


def test_rotate_blob_skips_current_key_ciphertext() -> None:
    """Already-rotated values are not rewritten on a repeat run."""
    current = Fernet(Fernet.generate_key())
    keyring = rotation.MultiFernet([current])
    blob = current.encrypt(json.dumps({"token": "value"}).encode()).decode()

    rotated, used_fallback = rotation.rotate_blob(
        blob, current=current, keyring=keyring
    )

    assert rotated is None
    assert used_fallback is False


def test_rotate_blob_fails_closed_on_unreadable_ciphertext() -> None:
    """Unknown ciphertext is never replaced with an empty or new payload."""
    current = Fernet(Fernet.generate_key())
    fallback = Fernet(Fernet.generate_key())
    keyring = rotation.MultiFernet([current, fallback])

    with pytest.raises(rotation.RotationError, match="could not be decrypted"):
        rotation.rotate_blob("not-valid-ciphertext", current=current, keyring=keyring)


def test_build_keyring_deduplicates_current_key_from_fallbacks() -> None:
    """Repeated key entries do not create duplicate keyring members."""
    current_key = Fernet.generate_key().decode()
    previous_key = Fernet.generate_key().decode()

    current, keyring = rotation.build_keyring(
        {
            "ENCRYPTION_KEY": current_key,
            "ENCRYPTION_KEY_FALLBACKS": f"{current_key},{previous_key},{previous_key}",
        }
    )

    assert current is keyring._fernets[0]
    assert len(keyring._fernets) == 2


def test_selected_columns_rejects_unlisted_target() -> None:
    """Operators cannot make the command update an arbitrary database column."""
    with pytest.raises(rotation.RotationError, match="unsupported --only target"):
        rotation._selected_columns(["organizations.unlisted_secret"])
