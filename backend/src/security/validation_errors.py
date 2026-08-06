"""Sanitize validation error payloads before they are returned to clients."""

from __future__ import annotations

from typing import Any

SENSITIVE_FIELD_NAMES = frozenset(
    {
        "password",
        "password_confirm",
        "current_password",
        "new_password",
        "new_password_confirm",
        "token",
        "refresh_token",
        "access_token",
        "secret",
        "api_key",
    }
)


def sanitize_validation_errors(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove request input values from FastAPI/Pydantic validation errors.

    Validation handlers echo the rejected request body in an ``input`` field.
    That must never be returned to browsers or logs because it can contain
    passwords and other secrets.
    """
    sanitized: list[dict[str, Any]] = []
    for error in errors:
        clean = {key: value for key, value in error.items() if key != "input"}
        sanitized.append(clean)
    return sanitized
