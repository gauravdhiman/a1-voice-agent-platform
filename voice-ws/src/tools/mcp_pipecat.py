"""Adapt remote MCP server tools to Pipecat ``FunctionSchema`` definitions."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any

from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.services.llm_service import FunctionCallParams

from shared.voice_agents.tools.mcp.client import McpClient
from shared.voice_agents.tools.mcp.dispatch import mcp_server_config_from_agent_tool
from shared.voice_agents.tools.mcp.schema_sanitize import sanitize_schema_for_gemini

logger = logging.getLogger(__name__)


def _mcp_result_text(result: Any) -> str:
    """Convert an MCP response into a model-readable string.

    Args:
        result: ``McpToolResult`` returned by the shared MCP client.

    Returns:
        Text content when available; otherwise a JSON representation of the
        server content. Error results are made explicit for model recovery.
    """
    text = result.text
    if result.is_error:
        return f"MCP tool error: {text or json.dumps(result.content, default=str)}"
    return text or json.dumps(result.content, default=str)


def _create_mcp_handler(client: McpClient, tool_name: str) -> Callable[..., Any]:
    """Create a Pipecat handler forwarding a function call to one MCP tool."""

    async def handler(params: FunctionCallParams) -> None:
        """Forward validated model arguments and return the MCP result."""
        arguments = dict(params.arguments)
        logger.info("Invoking MCP tool %s with args=%s", tool_name, arguments)
        try:
            result = await client.call_tool(tool_name, arguments)
        except Exception as exc:  # noqa: BLE001 - always return a model-visible error
            logger.exception("MCP tool %s failed: %s", tool_name, exc)
            await params.result_callback(f"MCP tool error: {tool_name} failed: {exc}")
            return
        text = _mcp_result_text(result)
        logger.info(
            "MCP tool %s completed error=%s",
            tool_name,
            getattr(result, "is_error", False),
        )
        await params.result_callback(text)

    return handler


async def build_mcp_pipecat_tools(
    agent_tool: Any,
) -> tuple[list[FunctionSchema], list[tuple[str, Callable[..., Any]]], McpClient]:
    """Open an MCP client and synthesize Pipecat schemas and handlers.

    Args:
        agent_tool: Enabled MCP-sourced agent tool including its platform tool,
            sensitive configuration, and optional unselected function names.

    Returns:
        A tuple containing tool schemas, separately registerable name/handler
        pairs, and the open client. The caller owns the client and must close it
        after the voice session.

    Raises:
        Exception: When server discovery fails. The partially created client is
            closed before the error propagates.
    """
    client = McpClient(mcp_server_config_from_agent_tool(agent_tool))
    try:
        tool_defs = await client.list_tools()
    except Exception:
        await client.close()
        raise

    skipped = set(agent_tool.unselected_functions or [])
    schemas: list[FunctionSchema] = []
    handlers: list[tuple[str, Callable[..., Any]]] = []
    for tool_def in tool_defs:
        if tool_def.name in skipped:
            continue
        input_schema = sanitize_schema_for_gemini(
            tool_def.input_schema or {"type": "object", "properties": {}}
        )
        properties = input_schema.get("properties", {})
        required = input_schema.get("required", [])
        handler = _create_mcp_handler(client, tool_def.name)
        schemas.append(
            FunctionSchema(
                name=tool_def.name,
                description=tool_def.description or "",
                properties=properties if isinstance(properties, dict) else {},
                required=required if isinstance(required, list) else [],
            )
        )
        handlers.append((tool_def.name, handler))

    logger.info(
        "Built %d Pipecat MCP tool(s) from %s",
        len(schemas),
        client.config.name or client.config.url,
    )
    return schemas, handlers, client
