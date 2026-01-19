"""
Security utilities for encryption and sensitive data handling.
"""

import base64
import json
import logging
import os
from typing import Any, Dict

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

# In a real production app, this should be a 32-byte base64 encoded string
# from a secure environment variable.
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")


def get_fernet() -> Fernet:
    """Get Fernet instance for encryption/decryption."""
    if not ENCRYPTION_KEY:
        # Fallback for development ONLY - in production this must be set
        # Using a deterministic key based on a fixed salt for dev convenience
        salt = b"ai-voice-agent-platform-salt"
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(b"dev-secret-key"))
        return Fernet(key)

    return Fernet(ENCRYPTION_KEY.encode())


def encrypt_data(data: Dict[str, Any]) -> str:
    """Encrypt a dictionary into an encrypted string."""
    if not data:
        return ""

    f = get_fernet()
    json_data = json.dumps(data).encode()
    return f.encrypt(json_data).decode()


def decrypt_data(encrypted_str: str) -> Dict[str, Any]:
    """Decrypt an encrypted string back into a dictionary."""
    if not encrypted_str:
        logger.warning("decrypt_data called with empty string")
        return {}

    try:
        f = get_fernet()
        decrypted_data = f.decrypt(encrypted_str.encode())
        result = json.loads(decrypted_data.decode())
        logger.info(f"Successfully decrypted data, keys: {list(result.keys())}")
        return result
    except Exception as e:
        # If decryption fails (e.g. wrong key), return empty dict
        # In production, we might want to log this error
        preview = encrypted_str[:100] if encrypted_str and len(encrypted_str) > 100 else encrypted_str
        logger.error(
            f"Decryption failed: {type(e).__name__}: {str(e)}. "
            f"Encrypted data preview: {preview}"
        )
        return {}