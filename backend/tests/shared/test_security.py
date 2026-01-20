"""
Tests for shared security utilities.
"""
import os
import pytest
from shared.common.security import encrypt_data, decrypt_data, get_fernet


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
        
        original = {"user_id": "123", "api_key": "secret_token", "config": {"opt1": True}}
        encrypted = encrypt_data(original)
        decrypted = decrypt_data(encrypted)
        
        assert decrypted == original

    def test_encrypt_decrypt_complex_data(self, monkeypatch):
        """Handles nested dicts and lists."""
        monkeypatch.setenv("ENCRYPTION_KEY", "test_key_for_testing_purposes_32bytes!!")
        
        complex_data = {
            "users": [
                {"id": 1, "name": "Alice"},
                {"id": 2, "name": "Bob"}
            ],
            "metadata": {
                "created": "2024-01-01",
                "tags": ["tag1", "tag2"],
                "nested": {"deep": {"value": 123}}
            },
            "empty_list": [],
            "null_value": None
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
        
    def test_get_fernet_without_env_key(self, monkeypatch):
        """Uses fallback when ENCRYPTION_KEY not set."""
        monkeypatch.delenv("ENCRYPTION_KEY", raising=False)
        
        fernet = get_fernet()
        
        assert fernet is not None
