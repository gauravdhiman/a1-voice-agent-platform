"""Security utilities for encryption and sensitive data handling.

Sensitive tool credentials are encrypted before they enter the database. The
application uses Fernet (authenticated encryption) with a deployment-managed
key and optional fallbacks for controlled key rotation. Production and
staging fail closed when the key is missing or malformed; they never use a
well-known development key.
"""

import base64
import json
import logging
import os
from typing import Any, Dict, Optional

from cryptography.fernet import Fernet, MultiFernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)


def _environment_name() -> str:
    """Return the normalized deployment environment."""
    return (
        (os.getenv("ENVIRONMENT") or os.getenv("APP_ENV") or "development")
        .strip()
        .lower()
    )


def _derive_test_key(seed: str) -> bytes:
    """Derive a deterministic test-only Fernet key from a test seed."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"24x7-ai-test-encryption-salt",
        iterations=100_000,
    )
    return base64.urlsafe_b64encode(kdf.derive(seed.encode("utf-8")))


def _fernet_key(raw_key: str, *, allow_test_derivation: bool) -> bytes:
    """Validate a Fernet key, with a test-only raw-secret compatibility path."""
    key = raw_key.encode("utf-8")
    try:
        Fernet(key)
        return key
    except ValueError:
        if allow_test_derivation:
            return _derive_test_key(raw_key)
        raise RuntimeError(
            "ENCRYPTION_KEY must be a valid URL-safe base64 Fernet key"
        ) from None


def get_fernet() -> MultiFernet:
    """Get an authenticated-encryption keyring for sensitive application data.

    ``ENCRYPTION_KEY`` is read at call time so tests and controlled key
    rotation do not use a stale import-time value. ``ENCRYPTION_KEY_FALLBACKS``
    is a comma-separated list of previous Fernet keys; encryption always uses
    the current key while decryption accepts the old keys during rotation.

    Raises:
        RuntimeError: If a staging/production key is missing or malformed.
    """
    environment = _environment_name()
    is_secure_environment = environment in {"production", "prod", "staging", "stage"}
    is_test_process = bool(os.getenv("PYTEST_CURRENT_TEST")) or environment in {
        "test",
        "testing",
    }
    raw_key = os.getenv("ENCRYPTION_KEY", "").strip()
    if not raw_key:
        if is_secure_environment:
            raise RuntimeError(
                "ENCRYPTION_KEY must be configured in staging and production"
            )
        if is_test_process:
            raw_key = "24x7-ai-test-only-key"
        else:
            raise RuntimeError(
                "ENCRYPTION_KEY must be configured; insecure development fallback "
                "has been removed"
            )

    current_key = _fernet_key(
        raw_key,
        allow_test_derivation=is_test_process and not is_secure_environment,
    )
    fallback_keys = []
    for raw_fallback in os.getenv("ENCRYPTION_KEY_FALLBACKS", "").split(","):
        fallback = raw_fallback.strip()
        if not fallback:
            continue
        fallback_keys.append(
            _fernet_key(
                fallback,
                allow_test_derivation=is_test_process and not is_secure_environment,
            )
        )
    return MultiFernet([Fernet(current_key), *(Fernet(key) for key in fallback_keys)])


def encrypt_data(data: Optional[Dict[str, Any]]) -> str:
    """Encrypt a dictionary into an authenticated ciphertext string."""
    if not data:
        return ""

    f = get_fernet()
    json_data = json.dumps(data).encode()
    return f.encrypt(json_data).decode()


def decrypt_data(encrypted_str: str) -> Dict[str, Any]:
    """Decrypt an encrypted string without logging credential material.

    Invalid, empty, or non-object ciphertext returns an empty dictionary so
    callers fail closed as unauthenticated. The ciphertext itself is never
    included in logs; it may be an encrypted token or secret header.
    """
    if not encrypted_str:
        return {}

    try:
        f = get_fernet()
        decrypted_data = f.decrypt(encrypted_str.encode())
        result = json.loads(decrypted_data.decode())
        if not isinstance(result, dict):
            logger.error("Decryption failed: payload is not a JSON object")
            return {}
        return result
    except Exception as exc:
        # Do not log ciphertext, plaintext, exception messages, or request
        # payloads. The exception class is enough to diagnose key mismatch or
        # malformed data without creating a token-bearing log line.
        logger.error("Decryption failed (%s)", type(exc).__name__)
        return {}
