"""
Tests for shared security utilities.
"""

import os

import pytest

from shared.common.security import decrypt_data, encrypt_data, get_fernet


class TestEncryptDecrypt:
    """Test encryption and decryption functions."""

    def test_encrypt_data_dict(self):
        """Encrypts dictionary to string."""
        data = {"key": "value", "number": 42, "nested": {"foo": "bar"}}
        result = encrypt_data(data)

        assert isinstance(result, str)
        assert len(result) > 0
        assert result != str(data)

    def test_encrypt_data_empty_dict(self):
        """Returns empty string for empty dict."""
        result = encrypt_data({})

        assert result == ""

    def test_encrypt_data_none(self):
        """Returns empty string for None."""
        result = encrypt_data(None)

        assert result == ""

    def test_decrypt_data_valid(self, monkeypatch):
        """Decrypts back to dictionary."""
        monkeypatch.setenv("ENCRYPTION_KEY", "test_key_for_testing_purposes_32bytes!!")

        original_data = {"key": "value", "number": 42, "nested": {"foo": "bar"}}
        encrypted = encrypt_data(original_data)
        decrypted = decrypt_data(encrypted)

        assert decrypted == original_data

    def test_decrypt_data_empty(self):
        """Returns empty dict for empty string."""
        result = decrypt_data("")

        assert result == {}

    def test_decrypt_data_invalid(self):
        """Returns empty dict for invalid data."""
        result = decrypt_data("not-encrypted-data")

        assert result == {}

    def test_encrypt_decrypt_roundtrip(self, monkeypatch):
        """Data survives encryption roundtrip."""
        monkeypatch.setenv("ENCRYPTION_KEY", "test_key_for_testing_purposes_32bytes!!")

        original = {
            "user_id": "123",
            "api_key": "secret_token",
            "config": {"opt1": True},
        }
        encrypted = encrypt_data(original)
        decrypted = decrypt_data(encrypted)

        assert decrypted == original

    def test_encrypt_decrypt_complex_data(self, monkeypatch):
        """Handles nested dicts and lists."""
        monkeypatch.setenv("ENCRYPTION_KEY", "test_key_for_testing_purposes_32bytes!!")

        complex_data = {
            "users": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}],
            "metadata": {
                "created": "2024-01-01",
                "tags": ["tag1", "tag2"],
                "nested": {"deep": {"value": 123}},
            },
            "empty_list": [],
            "null_value": None,
        }

        encrypted = encrypt_data(complex_data)
        decrypted = decrypt_data(encrypted)

        assert decrypted == complex_data


class TestGetFernet:
    """Test get_fernet function."""

    def test_get_fernet_with_env_key(self, monkeypatch):
        """Uses ENCRYPTION_KEY environment variable when set."""
        monkeypatch.setenv("ENCRYPTION_KEY", "test_key_for_testing_purposes_32bytes!!")

        fernet = get_fernet()

        assert fernet is not None

    def test_get_fernet_without_env_key_in_staging_fails_closed(self, monkeypatch):
        """Staging never silently falls back to a known encryption key."""
        monkeypatch.delenv("ENCRYPTION_KEY", raising=False)
        monkeypatch.setenv("ENVIRONMENT", "staging")

        with pytest.raises(RuntimeError, match="ENCRYPTION_KEY"):
            get_fernet()

    def test_decrypt_failure_does_not_log_ciphertext(self, monkeypatch, caplog):
        """Invalid ciphertext is rejected without placing token material in logs."""
        monkeypatch.setenv("ENCRYPTION_KEY", "test_key_for_testing_purposes_32bytes!!")
        caplog.set_level("ERROR")
        ciphertext = "this-is-sensitive-ciphertext-that-must-not-be-logged"

        assert decrypt_data(ciphertext) == {}
        assert ciphertext not in caplog.text

    def test_key_rotation_accepts_previous_key_but_encrypts_with_current_key(
        self, monkeypatch
    ):
        """Fernet fallbacks support rotation without weakening authentication."""
        monkeypatch.setenv("ENCRYPTION_KEY", "old-key-for-testing-purposes")
        ciphertext = encrypt_data({"refresh_token": "old-token"})

        monkeypatch.setenv("ENCRYPTION_KEY", "new-key-for-testing-purposes")
        monkeypatch.setenv("ENCRYPTION_KEY_FALLBACKS", "old-key-for-testing-purposes")

        assert decrypt_data(ciphertext) == {"refresh_token": "old-token"}
        rotated = encrypt_data({"refresh_token": "new-token"})
        assert rotated != ciphertext
        assert decrypt_data(rotated) == {"refresh_token": "new-token"}
