"""Tests for public organization page security helpers."""

from shared.organization.public_page_security import (
    hash_public_page_passphrase,
    verify_public_page_passphrase,
)


class TestPublicPagePassphraseSecurity:
    def test_hash_and_verify_round_trip(self):
        stored = hash_public_page_passphrase("secret-door")
        assert verify_public_page_passphrase("secret-door", stored) is True
        assert verify_public_page_passphrase("wrong", stored) is False

    def test_verify_rejects_empty_inputs(self):
        stored = hash_public_page_passphrase("abc")
        assert verify_public_page_passphrase("", stored) is False
        assert verify_public_page_passphrase("abc", None) is False
