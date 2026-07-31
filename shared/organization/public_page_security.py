"""Passphrase hashing and verification for org public pages.

Uses PBKDF2-HMAC-SHA256 from the standard library (no extra dependencies).
Stored format: ``pbkdf2_sha256$<iterations>$<salt_b64>$<hash_b64>``.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

DEFAULT_ITERATIONS = 390_000


def hash_public_page_passphrase(passphrase: str) -> str:
    """Hash a public-page passphrase for storage.

    Args:
        passphrase: Plaintext passphrase from the org admin.

    Returns:
        Encoded hash string suitable for ``public_page_passphrase_hash``.
    """
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        passphrase.encode("utf-8"),
        salt,
        DEFAULT_ITERATIONS,
    )
    salt_b64 = base64.urlsafe_b64encode(salt).decode("ascii")
    digest_b64 = base64.urlsafe_b64encode(digest).decode("ascii")
    return f"pbkdf2_sha256${DEFAULT_ITERATIONS}${salt_b64}${digest_b64}"


def verify_public_page_passphrase(passphrase: str, stored_hash: str | None) -> bool:
    """Verify a visitor passphrase against the stored hash.

    Args:
        passphrase: Candidate passphrase from the visitor.
        stored_hash: Value from ``organizations.public_page_passphrase_hash``.

    Returns:
        True when the passphrase matches; False otherwise.
    """
    if not stored_hash or not passphrase:
        return False
    try:
        scheme, iterations_raw, salt_b64, digest_b64 = stored_hash.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        iterations = int(iterations_raw)
        salt = base64.urlsafe_b64decode(salt_b64.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_b64.encode("ascii"))
    except (ValueError, TypeError):
        return False

    actual = hashlib.pbkdf2_hmac(
        "sha256",
        passphrase.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(actual, expected)


__all__ = ["hash_public_page_passphrase", "verify_public_page_passphrase"]
