"""Gemini-compatible JSON Schema sanitizer for model tool arguments.

Transport-neutral — used by the Pipecat voice-ws native and MCP paths.
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
        schema: A JSON Schema fragment (dict, list, or scalar) from a native
            tool or an MCP server's ``inputSchema``.

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
            elif key == "enum" and isinstance(value, list):
                # Optional string parameters must be omitted when unset. An
                # empty-string sentinel is not a valid Gemini enum item and
                # causes the whole Live setup request to be rejected.
                non_empty_values = [item for item in value if item != ""]
                if non_empty_values:
                    sanitized[key] = non_empty_values
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


def build_gemini_function_declaration(tool_def: Any) -> dict[str, Any]:
    """Build a Gemini ``FunctionDeclaration`` dict from an MCP tool definition.

    Args:
        tool_def: ``McpToolDef`` (or compatible object with name, description,
            and ``input_schema``).

    Returns:
        Dict suitable for ``google.genai.types.FunctionDeclaration.model_validate``.
    """
    input_schema = sanitize_schema_for_gemini(
        getattr(tool_def, "input_schema", None)
        or {"type": "object", "properties": {}}
    )
    return {
        "name": tool_def.name,
        "description": getattr(tool_def, "description", None) or "",
        "parameters": input_schema,
    }
