"""Gemini-compatible JSON Schema sanitizer for MCP tool arguments.

Transport-neutral — used by both the LiveKit worker adapter and the Pipecat
voice-ws MCP path. Keeping this out of ``livekit_adapter`` avoids importing
``livekit`` in the WebSocket worker.
"""

from __future__ import annotations

from typing import Any

#: JSON Schema keys Google's Gemini ``Schema`` model accepts.
_GEMINI_SCHEMA_KEYS: frozenset[str] = frozenset(
    {
        "additionalProperties",
        "defs",
        "ref",
        "anyOf",
        "default",
        "description",
        "enum",
        "example",
        "format",
        "items",
        "maxItems",
        "maxLength",
        "maxProperties",
        "maximum",
        "minItems",
        "minLength",
        "minProperties",
        "minimum",
        "nullable",
        "pattern",
        "properties",
        "propertyOrdering",
        "required",
        "title",
        "type",
    }
)

_PROPERTIES_KEYS = ("properties", "defs")


def sanitize_schema_for_gemini(schema: Any) -> Any:
    """Strip JSON Schema keys Gemini's ``Schema`` model rejects, recursively.

    Args:
        schema: A JSON Schema fragment (dict, list, or scalar) from an MCP
            server's ``inputSchema``.

    Returns:
        A schema fragment with only Gemini-accepted keys retained.

    Notes:
        ``oneOf`` / ``allOf`` are dropped (not in Gemini's allowlist).
        TODO: Future Enhancement — map ``oneOf``→``anyOf`` if a tool needs it.
    """
    if isinstance(schema, dict):
        sanitized: dict[str, Any] = {}
        for key, value in schema.items():
            if key not in _GEMINI_SCHEMA_KEYS:
                continue
            if key in _PROPERTIES_KEYS and isinstance(value, dict):
                sanitized[key] = {
                    name: sanitize_schema_for_gemini(sub)
                    for name, sub in value.items()
                    if isinstance(sub, (dict, list))
                }
            elif key == "items":
                if isinstance(value, list):
                    sanitized[key] = [
                        sanitize_schema_for_gemini(sub)
                        for sub in value
                        if isinstance(sub, (dict, list))
                    ]
                elif isinstance(value, dict):
                    sanitized[key] = sanitize_schema_for_gemini(value)
                else:
                    sanitized[key] = value
            elif key == "anyOf" and isinstance(value, list):
                sanitized[key] = [
                    sanitize_schema_for_gemini(sub)
                    for sub in value
                    if isinstance(sub, (dict, list))
                ]
            elif key == "additionalProperties":
                sanitized[key] = (
                    sanitize_schema_for_gemini(value)
                    if isinstance(value, dict)
                    else value
                )
            else:
                sanitized[key] = value
        return sanitized
    if isinstance(schema, list):
        return [
            sanitize_schema_for_gemini(item)
            for item in schema
            if isinstance(item, (dict, list))
        ]
    return schema


# Back-compat for LiveKit adapter private import sites.
_sanitize_schema_for_gemini = sanitize_schema_for_gemini
