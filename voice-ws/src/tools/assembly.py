"""Assemble transport-neutral agent tools into Pipecat schemas and handlers.

This module keeps the shared ``BaseTool`` implementations reusable and converts their
signatures into Pipecat schemas for the WebSocket voice worker.
"""

from __future__ import annotations

import inspect
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from types import UnionType
from typing import Any, Union, get_args, get_origin, get_type_hints

from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.services.llm_service import FunctionCallParams
from src.tools.mcp_pipecat import build_mcp_pipecat_tools
from src.tools.skill_tools import (
    create_load_skill_function,
    create_load_skill_reference_function,
)

from shared.voice_agents.skill_service import skill_service
from shared.voice_agents.tool_models import ToolSource
from shared.voice_agents.tool_service import tool_service
from shared.voice_agents.tools.base.platform_tool_registry import PlatformToolRegistry
from shared.voice_agents.tools.base.tool_context import ToolContext

logger = logging.getLogger(__name__)


@dataclass
class AssembledTools:
    """All model schemas and runtime resources needed by a voice session.

    Attributes:
        schemas: Schemas supplied to the Pipecat LLM service.
        handlers: Function handlers registered on the LLM by schema name.
        enabled_tool_names: Platform tool names for prompt construction.
        mcp_clients: Open clients that must stay alive for the session.
        skill_summaries: Prompt-safe skill metadata for progressive disclosure.
        unavailable_tools: Human-readable reasons for tools that failed to load
            so the model is told not to invent outcomes for them.
    """

    schemas: list[FunctionSchema] = field(default_factory=list)
    handlers: dict[str, Callable[..., Any]] = field(default_factory=dict)
    enabled_tool_names: list[str] = field(default_factory=list)
    mcp_clients: list[Any] = field(default_factory=list)
    skill_summaries: list[Any] = field(default_factory=list)
    unavailable_tools: list[str] = field(default_factory=list)


def _json_schema_for_annotation(annotation: Any) -> dict[str, Any]:
    """Map a Python annotation to a JSON Schema fragment for Gemini tools.

    Gemini Live rejects function declarations when ``array`` properties omit
    the required ``items`` field (e.g. Google Sheets ``values: List[Any]``).
    """
    if annotation is inspect.Parameter.empty:
        annotation = Any

    origin = get_origin(annotation)
    if origin in (Union, UnionType):
        choices = [
            choice for choice in get_args(annotation) if choice is not type(None)
        ]
        if len(choices) == 1:
            return _json_schema_for_annotation(choices[0])
        return {"type": "string"}

    if origin in (list, tuple, set):
        args = get_args(annotation)
        item_annotation = args[0] if args else Any
        return {
            "type": "array",
            "items": _json_schema_for_annotation(item_annotation),
        }

    if origin is dict:
        args = get_args(annotation)
        value_annotation = args[1] if len(args) > 1 else Any
        return {
            "type": "object",
            "additionalProperties": _json_schema_for_annotation(value_annotation),
        }

    primitive = {
        int: "integer",
        float: "number",
        bool: "boolean",
        str: "string",
        dict: "object",
        list: "array",
    }.get(annotation)
    if primitive == "array":
        return {"type": "array", "items": {"type": "string"}}
    if primitive == "object":
        return {"type": "object"}
    if primitive:
        return {"type": primitive}
    return {"type": "string"}


def build_function_schema(function: Callable[..., Any]) -> FunctionSchema:
    """Build a Pipecat schema from a shared legacy tool function signature.

    Args:
        function: Decorated shared tool method. ``self`` and ``context`` are
            excluded because neither is LLM-supplied.

    Returns:
        A Pipecat ``FunctionSchema`` matching the public function arguments.
    """
    signature = inspect.signature(function)
    try:
        hints = get_type_hints(function)
    except Exception:  # noqa: BLE001 - unresolved optional hints must not block calls
        hints = getattr(function, "__annotations__", {})

    properties: dict[str, Any] = {}
    required: list[str] = []
    for name, parameter in signature.parameters.items():
        if name in {"self", "context"}:
            continue
        if parameter.kind in {
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        }:
            continue
        properties[name] = _json_schema_for_annotation(
            hints.get(name, parameter.annotation)
        )
        if parameter.default is inspect.Parameter.empty:
            required.append(name)
    return FunctionSchema(
        name=function.__name__,
        description=inspect.getdoc(function) or "",
        properties=properties,
        required=required,
    )


def create_legacy_tool_handler(
    bound_method: Callable[..., Any],
    runtime_context: ToolContext | None = None,
) -> Callable[[FunctionCallParams], Any]:
    """Create a Pipecat handler that safely calls a shared ``BaseTool`` method.

    ``context`` is deliberately removed from model arguments and injected as a
    trusted per-session ``ToolContext``. Results are JSON encoded so Pipecat always returns a
    string to the LLM, even when a legacy tool returns a mapping or list.
    Exceptions are caught and returned as ``{"error": ...}`` so the model can
    recover instead of inventing a successful booking.
    """

    tool_name = getattr(bound_method, "__name__", "unknown_tool")

    async def handler(params: FunctionCallParams) -> None:
        """Run the bound method with trusted context and return serialized output."""
        arguments = {
            name: value
            for name, value in dict(params.arguments).items()
            if name != "context"
        }
        logger.info("Invoking legacy tool %s with args=%s", tool_name, arguments)
        try:
            result = await bound_method(
                context=runtime_context or ToolContext(), **arguments
            )
        except Exception as exc:  # noqa: BLE001 - always return a model-visible error
            logger.exception("Legacy tool %s failed: %s", tool_name, exc)
            await params.result_callback(
                json.dumps({"error": f"{tool_name} failed: {exc}"}, default=str)
            )
            return
        logger.info("Legacy tool %s completed", tool_name)
        await params.result_callback(json.dumps(result, default=str))

    return handler


def format_tool_runtime_instructions(assembled: AssembledTools) -> str:
    """Build prompt text that anchors the model to real tool call results.

    Args:
        assembled: Tools assembled for the current voice session.

    Returns:
        A markdown section listing callable function names and any tools that
        failed to load. Empty string when neither list has content.
    """
    sections: list[str] = []
    function_names = [schema.name for schema in assembled.schemas]
    if function_names:
        sections.append(
            "# AVAILABLE TOOL FUNCTIONS\n"
            "For scheduling, availability, and bookings you MUST call the "
            "appropriate function below and wait for its result before telling "
            "the caller the outcome.\n"
            f"Callable functions: {', '.join(function_names)}.\n"
            "Never invent availability or confirm a booking/cancel/reschedule "
            "without a successful tool result for that action."
        )
    if assembled.unavailable_tools:
        failure_lines = "\n".join(f"- {item}" for item in assembled.unavailable_tools)
        sections.append(
            "# UNAVAILABLE TOOLS\n"
            "These tools failed to load for this call. Tell the caller you "
            "cannot complete related actions right now — do not invent results.\n"
            f"{failure_lines}"
        )
    return "\n\n".join(sections)


def _add_handler(
    assembled: AssembledTools,
    name: str,
    handler: Callable[..., Any],
    schema: FunctionSchema,
) -> None:
    """Register a unique function or log a collision without replacing it."""
    if name in assembled.handlers:
        logger.warning("Skipping duplicate Pipecat tool function '%s'", name)
        return
    assembled.handlers[name] = handler
    assembled.schemas.append(schema)


async def assemble_agent_tools(
    agent_id: Any,
    organization_id: Any,
    runtime_context: ToolContext | None = None,
) -> AssembledTools:
    """Build every enabled legacy, MCP, and skill tool for one voice agent.

    Args:
        agent_id: Voice agent UUID.
        organization_id: Organization UUID used by progressive skill handlers.
        runtime_context: Trusted session metadata injected into native tools and
            translated into namespaced headers for in-process MCP connectors.

    Returns:
        The assembled schemas, handler map, open MCP clients, tool names, and
        skill summaries. Failed individual tools are logged and skipped so one
        provider outage does not prevent a call from starting.
    """
    assembled = AssembledTools()
    registry = PlatformToolRegistry()
    registry.register_tools_from_package("shared.voice_agents.tools.implementations")

    agent_tools, error = await tool_service.get_agent_tools_with_sensitive_config(
        agent_id
    )
    if error:
        logger.error("Unable to fetch agent tools for %s: %s", agent_id, error)
        agent_tools = []

    for agent_tool in agent_tools:
        platform_tool = agent_tool.tool
        if not agent_tool.is_enabled or platform_tool is None:
            continue
        tool_name = platform_tool.name
        if platform_tool.tool_source == ToolSource.MCP:
            try:
                schemas, handlers, client = await build_mcp_pipecat_tools(
                    agent_tool, runtime_context=runtime_context
                )
            except Exception as exc:  # noqa: BLE001 - preserve non-MCP tools
                logger.exception("Failed to assemble MCP tool '%s': %s", tool_name, exc)
                assembled.unavailable_tools.append(f"{tool_name}: {exc}")
                continue
            assembled.mcp_clients.append(client)
            assembled.enabled_tool_names.append(tool_name)
            for schema, (name, handler) in zip(schemas, handlers):
                _add_handler(assembled, name, handler, schema)
            continue

        tool_class = registry.get_tool_class(tool_name)
        if tool_class is None:
            logger.warning("Shared tool '%s' is not registered", tool_name)
            assembled.unavailable_tools.append(
                f"{tool_name}: shared implementation is not registered"
            )
            continue
        instance = tool_class(
            config=agent_tool.config or {},
            sensitive_config=agent_tool.sensitive_config or {},
        )
        assembled.enabled_tool_names.append(tool_name)
        skipped = set(agent_tool.unselected_functions or [])
        for function in registry.get_tool_functions(tool_name):
            if function.__name__ in skipped:
                continue
            schema = build_function_schema(function)
            handler = create_legacy_tool_handler(
                getattr(instance, function.__name__),
                runtime_context=runtime_context,
            )
            _add_handler(assembled, schema.name, handler, schema)

    summaries, skill_error = await skill_service.get_agent_skill_summaries(agent_id)
    if skill_error:
        logger.warning("Unable to fetch skills for %s: %s", agent_id, skill_error)
        logger.info(
            "Assembled tools for %s: functions=%s unavailable=%s",
            agent_id,
            [schema.name for schema in assembled.schemas],
            assembled.unavailable_tools,
        )
        return assembled
    assembled.skill_summaries = summaries
    if summaries:
        load_skill = create_load_skill_function(str(organization_id), skill_service)
        load_reference = create_load_skill_reference_function(
            str(organization_id), skill_service
        )
        _add_handler(
            assembled,
            "load_skill",
            _create_skill_handler(load_skill),
            FunctionSchema(
                name="load_skill",
                description="Load a skill's full procedures using its available skill slug.",
                properties={"skill_slug": {"type": "string"}},
                required=["skill_slug"],
            ),
        )
        _add_handler(
            assembled,
            "load_skill_reference",
            _create_skill_handler(load_reference),
            FunctionSchema(
                name="load_skill_reference",
                description="Load a reference file from a previously loaded skill.",
                properties={
                    "skill_slug": {"type": "string"},
                    "file_path": {"type": "string"},
                },
                required=["skill_slug", "file_path"],
            ),
        )
    logger.info(
        "Assembled tools for %s: functions=%s unavailable=%s",
        agent_id,
        [schema.name for schema in assembled.schemas],
        assembled.unavailable_tools,
    )
    return assembled


def _create_skill_handler(
    function: Callable[..., Any]
) -> Callable[[FunctionCallParams], Any]:
    """Adapt a keyword-based skill loader to Pipecat's function call contract."""

    async def handler(params: FunctionCallParams) -> None:
        """Call the skill loader and return its text to the model."""
        logger.info(
            "Invoking skill tool %s with args=%s",
            getattr(function, "__name__", "skill_tool"),
            dict(params.arguments),
        )
        try:
            result = await function(**dict(params.arguments))
        except Exception as exc:  # noqa: BLE001 - keep the call alive
            logger.exception("Skill tool failed: %s", exc)
            await params.result_callback(f"Skill tool error: {exc}")
            return
        await params.result_callback(result)

    return handler
