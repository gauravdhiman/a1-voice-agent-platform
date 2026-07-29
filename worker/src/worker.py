import inspect
import logging
import os
from typing import Any, Dict, List, Optional, Union

from default_system_prompt import default_system_prompt
from livekit.agents import (
    Agent,
    AgentServer,
    JobContext,
    RunContext,
    cli,
    function_tool,
)
from livekit.agents.voice import room_io

from session_builder import build_agent_session

from shared.common.security import decrypt_data
from shared.voice_agents.livekit_service import livekit_service
from shared.voice_agents.service import voice_agent_service
from shared.voice_agents.speech_config import default_realtime_config
from shared.voice_agents.tool_service import tool_service
from shared.voice_agents.tools.base.registry_livekit import livekit_tool_registry
from shared.voice_agents.prompt_builder import PromptBuilder, build_current_datetime_section
from shared.organization.service import BaseOrganizationService

# MCP integration (Phase 3a) — the parallel tool path. Only used for
# platform_tools rows marked tool_source='mcp'; the legacy BaseTool path below
# is unchanged. See docs/03_implementation/mcp_integration_rfc.md §1.1.
from shared.voice_agents.tool_models import ToolSource
from shared.voice_agents.tools.mcp import build_livekit_tools_for_agent_tool

logger = logging.getLogger("voice-worker")

organization_service = BaseOrganizationService()

log_level = (
    logging.DEBUG if os.getenv("DEBUG", "false").lower() == "true" else logging.INFO
)
logger.setLevel(log_level)

server = AgentServer()

# Register all tool implementations
livekit_tool_registry.register_tools_from_package(
    "shared.voice_agents.tools.implementations"
)
logger.info(f"Registered tools: {list(livekit_tool_registry._tools.keys())}")


def _create_tool_wrapper(
    bound_method: Any, func_name: str, sig: inspect.Signature, type_hints: dict
) -> Any:
    """
    Create a wrapper function for a tool method.

    The wrapper has the same signature as the original method (excluding 'self').
    It accepts all parameters explicitly (no **kwargs), then delegates to the bound method.
    """
    # Get parameter definitions for the wrapper function, preserving default values
    params_def = []
    other_param_names = []

    for param_name, param in sig.parameters.items():
        if param_name == "self":
            continue

        param_type = type_hints.get(param_name, Any)
        # Get string representation of type
        if hasattr(param_type, "__name__"):
            type_str = param_type.__name__
        elif hasattr(param_type, "_name"):
            type_str = param_type._name
        elif hasattr(param_type, "__origin__"):
            type_str = str(param_type).replace("typing.", "")
        else:
            type_str = "Any"

        # Build parameter definition with default value if present
        param_def = f"{param_name}: {type_str}"
        if param.default != inspect.Parameter.empty:
            # Use repr to handle strings, None, and other types correctly
            param_def += f" = {repr(param.default)}"

        params_def.append(param_def)
        if param_name != "context":
            other_param_names.append(param_name)

    params_str = ", ".join(params_def)
    other_param_names_repr = repr(other_param_names)

    # Create the wrapper function dynamically
    # Use exec() to create a function with the right signature
    # This is the only reliable way to create functions with dynamic signatures
    wrapper_code = f"""
async def {func_name}({params_str}) -> Any:
    '''Wrapper for {func_name}.'''
    # Build kwargs dict for all parameters except context
    kwargs = {{}}
    for pname in {other_param_names_repr}:
        kwargs[pname] = locals()[pname]
    result = await bound_method(context=context, **kwargs)
    import json
    try:
        result_str = json.dumps(result, default=str)
        logger.debug(f"Tool {func_name} result size: {{len(result_str)}} chars")
    except Exception as e:
        logger.error(f"Failed to serialize tool {func_name} result: {{e}}")
    return result
"""

    # Execute the code to create the wrapper function
    namespace = {
        "Any": Any,
        "Dict": Dict,
        "List": List,
        "Optional": Optional,
        "Union": Union,
        "RunContext": RunContext,
        "bound_method": bound_method,
        "logger": logger,
    }
    local_scope = {}
    exec(wrapper_code, namespace, local_scope)
    wrapper = local_scope[f"{func_name}"]

    # Copy type hints from original function (excluding 'self')
    wrapper.__annotations__ = type_hints

    return wrapper


async def _integrate_mcp_agent_tool(
    agent_tool,
    livekit_tools: list,
    mcp_clients: list,
    enabled_tool_names: list,
) -> None:
    """Route one MCP-sourced agent_tool through the remote MCP server path.

    This is the Phase 3a branch extracted for testability. On success it
    extends ``livekit_tools`` with the synthesized LiveKit tools, appends the
    open :class:`McpClient` to ``mcp_clients`` (the caller closes these on
    session end), and records the tool name in ``enabled_tool_names`` for the
    prompt builder. On failure it logs and returns without raising, so a broken
    MCP server never prevents the rest of the agent's tools (legacy or MCP)
    from loading.

    Coexists with the legacy ``BaseTool`` path — the caller only invokes this
    for rows where ``tool.tool_source == ToolSource.MCP``. See RFC §1.1.

    Args:
        agent_tool: An enabled :class:`AgentTool` whose ``tool.tool_source`` is
            ``MCP``.
        livekit_tools: The per-agent LiveKit tool list to extend (in place).
        mcp_clients: The per-agent MCP client list to append the open client to
            (in place); the caller owns the clients' lifecycle.
        enabled_tool_names: The per-agent enabled-tool-name list to append the
            tool name to (for prompt building).
    """
    try:
        mcp_tools, mcp_client = await build_livekit_tools_for_agent_tool(agent_tool)
    except Exception as mcp_err:
        logger.error(
            f"Failed to build MCP tools for '{agent_tool.tool.name}': {mcp_err}",
            exc_info=True,
        )
        return
    livekit_tools.extend(mcp_tools)
    mcp_clients.append(mcp_client)
    enabled_tool_names.append(agent_tool.tool.name)
    logger.info(f"Built {len(mcp_tools)} MCP tool(s) for: {agent_tool.tool.name}")


def _hand_off_mcp_clients_to_session(ctx, mcp_clients: list) -> None:
    """Hand ownership of MCP clients from the entrypoint to the live session.

    The worker entrypoint returns right after ``agent_session.start()`` while the
    LiveKit session keeps running autonomously (conversation, tool calls happen
    after the entrypoint has returned). Each synthesized MCP tool holds a
    reference to its :class:`McpClient`, so the clients must outlive the
    entrypoint and be closed when the **job** ends — NOT in the entrypoint's
    ``finally`` (which fires at return time, before any tool call). This
    registers a shutdown callback on the ``JobContext`` to close the clients at
    job shutdown (participant disconnect / session end), which is the real
    session lifetime.

    Args:
        ctx: The LiveKit ``JobContext`` for this room/job.
        mcp_clients: The per-agent MCP clients whose handlers are wired into the
            live session's tools.

    Notes:
        - No-op when there are no MCP clients (legacy-only agents register no
          callback).
        - ``McpClient.close`` is idempotent, so this is safe even if cleanup also
          runs elsewhere.
    """
    if not mcp_clients:
        return

    async def _close_on_shutdown(_reason: str = "") -> None:
        for client in mcp_clients:
            try:
                await client.close()
            except Exception as close_err:
                logger.error(
                    f"Error closing MCP client on shutdown: {close_err}",
                    exc_info=True,
                )

    ctx.add_shutdown_callback(_close_on_shutdown)


async def _cleanup_mcp_clients(mcp_clients: list, handed_off: bool) -> None:
    """Close MCP clients, but only when setup failed before session handoff.

    Called from the entrypoint's ``finally``. When the session successfully
    started, ownership of the clients was handed to the job lifecycle via
    :func:`_hand_off_mcp_clients_to_session` (``handed_off=True``); they are
    closed later by the shutdown callback and must NOT be closed here, or every
    synthesized tool would fail with ``RuntimeError: McpClient is closed`` at
    call time. When setup failed before the session took ownership
    (``handed_off=False``), the half-open clients are leaked unless we close
    them here.

    Args:
        mcp_clients: The per-agent MCP clients.
        handed_off: ``True`` once ``agent_session.start()`` succeeded and the
            shutdown callback was registered; ``False`` on the error path.
    """
    if handed_off:
        return
    for client in mcp_clients:
        try:
            await client.close()
        except Exception as close_err:
            logger.error(
                f"Error closing MCP client: {close_err}", exc_info=True
            )


class DynamicAgent(Agent):
    def __init__(self, instructions: str):
        # allow_interruptions=True is the LiveKit framework default, but we set
        # it explicitly so a future framework default change cannot silently
        # regress barge-in (the "agent repeats itself after the user already
        # responded" symptom). The Gemini server side is also set to
        # START_OF_ACTIVITY_INTERRUPTS in speech_providers.realtime.provider — both layers honor
        # interruption.
        super().__init__(instructions=instructions, allow_interruptions=True)

    async def on_enter(self):
        logger.info(f"Agent entered: {self.session.userdata.get('agent_name')}")


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    logger.info(f"Connecting to room {ctx.room.name}")
    await ctx.connect()
    logger.info(
        f"Connected to room, remote participants: {list(ctx.room.remote_participants.keys())}"
    )

    agent_session = None
    voice_agent = None
    agent_id = None
    room_name = ctx.room.name
    # MCP clients opened for this session (Phase 3a). Each MCP-sourced tool's
    # LiveKit handler holds a reference to its client, so the client must stay
    # open for the whole session. Because the entrypoint returns right after
    # ``agent_session.start()`` while the session runs on, the clients are handed
    # to the job lifecycle (closed via a shutdown callback) once the session
    # starts — NOT in the finally block, which would close them before any tool
    # call. ``mcp_clients_handed_off`` records whether that handoff happened; the
    # finally only closes clients when setup failed before the handoff.
    mcp_clients: list = []
    mcp_clients_handed_off = False

    try:
        logger.info(f"Room name from job: {room_name}")

        phone_number = None
        test_agent_id = None

        try:
            # Check room type:
            # Test room format: test_{agent_id}_{random}
            # Embed room format: embed_{agent_id}_{random}
            # Phone room format: call_{phone_number}_{random}
            if room_name.startswith("test_"):
                parts = room_name.split("_")
                test_agent_id = parts[1]
                logger.info(f"Test room detected, agent ID: {test_agent_id}")
            elif room_name.startswith("embed_"):
                parts = room_name.split("_")
                test_agent_id = parts[1]
                logger.info(f"Embed room detected, agent ID: {test_agent_id}")
            else:
                # 1. Extract phone number from room name
                # Room name format: call_NUMBER_random
                parts = room_name.split("_")
                phone_number = parts[1]
                logger.info(f"Extracted phone number: {phone_number}")
        except (IndexError, AttributeError) as e:
            logger.error(
                f"Failed to extract room metadata from '{room_name}': {e}"
            )
            return

        # 2. Fetch agent by ID (test room) or phone number (phone call)
        if test_agent_id:
            voice_agent, error = await voice_agent_service.get_agent_by_id(test_agent_id)
            if error or not voice_agent:
                logger.error(f"Failed to fetch agent for ID {test_agent_id}: {error}")
                return
            logger.info(f"Found agent: {voice_agent.name} (ID: {test_agent_id})")
        else:
            voice_agent, error = await voice_agent_service.get_agent_by_phone(phone_number)
            if error or not voice_agent:
                logger.error(f"Failed to fetch agent for phone {phone_number}: {error}")
                return
            logger.info(f"Found agent: {voice_agent.name} for phone: {phone_number}")

        agent_id = voice_agent.id

        logger.info(f"Starting Gemini S2S assistant for agent: {voice_agent.name}")

        # 3. Prepare tools for this agent
        logger.info("Fetching current tools from database")
        agent_tools, error = await tool_service.get_agent_tools_with_sensitive_config(
            voice_agent.id
        )
        if error:
            logger.error(f"Error fetching agent tools: {error}")
            agent_tools = []

        # Build tools programmatically using function_tool() with adapters
        livekit_tools = []
        enabled_tool_names = []

        for agent_tool in agent_tools:
            if not agent_tool.is_enabled or not agent_tool.tool:
                continue

            # --- MCP path (Phase 3a, coexists with legacy, RFC §1.1) --------
            # A platform_tools row marked tool_source='mcp' is routed through a
            # remote MCP server instead of the in-tree BaseTool registry. The
            # legacy path below is untouched and runs for every other row.
            if agent_tool.tool.tool_source == ToolSource.MCP:
                await _integrate_mcp_agent_tool(
                    agent_tool, livekit_tools, mcp_clients, enabled_tool_names
                )
                continue

            # --- legacy path (unchanged) ------------------------------------
            tool_name = agent_tool.tool.name
            tool_config = agent_tool.config or {}
            tool_sensitive_config = agent_tool.sensitive_config or {}

            # Get tool class
            tool_class = livekit_tool_registry.get_tool_class(tool_name)
            if not tool_class:
                logger.warning(f"Tool {tool_name} not found in registry, skipping")
                continue

            # Create tool instance with configuration
            logger.debug(f"Creating tool instance for {tool_name}")
            logger.debug(
                f"Config keys: {list(tool_config.keys()) if tool_config else []}"
            )
            logger.debug(
                f"Sensitive config keys: {list(tool_sensitive_config.keys()) if tool_sensitive_config else []}"
            )
            tool_instance = tool_class(
                config=tool_config, sensitive_config=tool_sensitive_config
            )

            # Track enabled tool names for prompt builder
            enabled_tool_names.append(tool_name)

            # Get all functions for this tool
            functions = livekit_tool_registry.get_tool_functions(tool_name)

            # Get unselected function names
            unselected_func_names = set(agent_tool.unselected_functions or [])
            actual_func_names = {func.__name__ for func in functions}

            # Check for stale unselected functions
            stale_functions = unselected_func_names - actual_func_names
            if stale_functions:
                logger.warning(
                    f"Found stale unselected functions for tool {tool_name}: {stale_functions}. "
                    f"These functions no longer exist in code and will be ignored."
                )

            # Build tool wrapper functions for each enabled function
            for func in functions:
                func_name = func.__name__

                if func_name in unselected_func_names:
                    logger.debug(
                        f"Function {func_name} is unselected for agent {agent_id}"
                    )
                    continue

                # Get the bound method
                bound_method = getattr(tool_instance, func_name)

                # Get the original function from the class (not the bound method)
                original_func = getattr(tool_class, func_name)
                sig = inspect.signature(original_func)

                # Get parameters excluding 'self'
                param_names = [name for name in sig.parameters.keys() if name != "self"]
                if not param_names:
                    logger.error(
                        f"Function {func_name} has no parameters (excluding self)"
                    )
                    continue

                # Get type hints from original function
                type_hints = {}
                if hasattr(original_func, "__annotations__"):
                    type_hints = {
                        k: v
                        for k, v in original_func.__annotations__.items()
                        if k != "self"
                    }

                logger.debug(f"Creating wrapper for {func_name}")
                logger.debug(f"  Parameters: {param_names}")
                logger.debug(f"  Type hints: {type_hints}")

                # Create wrapper function
                # The key insight: create a simple wrapper with explicit parameters
                # that match the original function (excluding 'self')
                wrapper = _create_tool_wrapper(
                    bound_method, func_name, sig, type_hints
                )

                # Set wrapper metadata
                wrapper.__name__ = func_name
                wrapper.__qualname__ = func_name
                wrapper.__doc__ = func.__doc__ or ""

                # Pass to function_tool
                tool = function_tool(
                    wrapper,
                    name=func_name,
                    description=func.__doc__ or "",
                )
                livekit_tools.append(tool)
                logger.info(f"Built function_tool for: {func_name}")

        # 3b. Fetch agent skills for progressive disclosure
        from shared.voice_agents.skill_service import skill_service
        from src.tools.skill_tool import create_load_skill_function, create_load_skill_reference_function

        skill_summaries, skill_error = await skill_service.get_agent_skill_summaries(
            voice_agent.id
        )
        if skill_error:
            logger.warning(f"Could not fetch agent skills: {skill_error}")
            skill_summaries = []
        else:
            logger.info(f"Fetched {len(skill_summaries)} skill summaries for agent {agent_id}")

        # Register load_skill tool if agent has skills
        if skill_summaries:
            load_skill_fn = create_load_skill_function(
                str(voice_agent.organization_id), skill_service
            )
            load_skill_tool = function_tool(
                load_skill_fn,
                name="load_skill",
                description="Load a skill's full procedures. Call with the skill slug from Available Skills.",
            )
            livekit_tools.append(load_skill_tool)
            logger.info("Registered load_skill tool")

            # Also register load_skill_reference for multi-level progressive disclosure
            load_skill_ref_fn = create_load_skill_reference_function(
                str(voice_agent.organization_id), skill_service
            )
            load_skill_ref_tool = function_tool(
                load_skill_ref_fn,
                name="load_skill_reference",
                description="Load a reference file from a skill. Call when a loaded skill mentions a file to read.",
            )
            livekit_tools.append(load_skill_ref_tool)
            logger.info("Registered load_skill_reference tool")

        # 3c. Build enhanced system prompt
        logger.info(f"Building enhanced system prompt for agent {agent_id}")
        # Inject a timezone-aware "now" once at session start so the model can
        # ground "today"/"tomorrow"/"now"/business-hours (Gemini realtime has no
        # inherent sense of the current date/time). The timezone is a platform
        # default (AGENT_DEFAULT_TIMEZONE env var, default UTC); the business
        # timezone itself is stated by the user in org details / skills and the
        # model reconciles against this anchor.
        # TODO: Future Enhancement — on long-lived sessions (>~15 min) this
        # injected "now" drifts. Refresh via livekit_agent.update_instructions(...)
        # on a timer or a per-turn chat_ctx system message so "now" stays accurate.
        current_dt_section = build_current_datetime_section(
            os.getenv("AGENT_DEFAULT_TIMEZONE", "UTC")
        )
        org, org_error = await organization_service.get_organization_by_id(voice_agent.organization_id)
        if org_error or not org:
            logger.warning(f"Could not fetch organization details: {org_error}. Using default prompt.")
            # Fallback to default prompt if org data unavailable; still prepend the
            # current-date/time anchor so the model has a temporal reference.
            instructions = current_dt_section + "\n\n" + default_system_prompt
            # Fallback to platform key if org not found
            org_google_api_key = None
        else:
            instructions = PromptBuilder.build(
                org=org,
                agent=voice_agent,
                default_rules=default_system_prompt,
                enabled_tools=enabled_tool_names,
                agent_skills=skill_summaries,
                current_datetime=current_dt_section,
            )
            # Get organization's Google API key
            org_google_api_key = getattr(org, 'google_api_key', None)
        
        logger.debug(f"Enhanced instructions built (length: {len(instructions)})")

        livekit_agent = DynamicAgent(
            instructions=instructions,
        )

        await livekit_agent.update_tools(livekit_tools)
        logger.info(f"Updated agent with {len(livekit_tools)} tools")

        # 4. Determine which API key to use
        # Priority: 
        # 1. If agent.use_platform_credits is True -> use platform key
        # 2. If org has google_api_key -> use org key
        # 3. Otherwise -> use platform key (fallback)
        use_platform_credits = getattr(voice_agent, 'use_platform_credits', False)
        
        if use_platform_credits:
            api_key = os.getenv("GEMINI_API_KEY")
            logger.info(f"Agent {agent_id} configured to use platform API key")
        elif org_google_api_key:
            api_key = org_google_api_key
            logger.info(f"Agent {agent_id} using organization API key")
        else:
            api_key = os.getenv("GEMINI_API_KEY")
            logger.info(f"Agent {agent_id} using platform API key (no org key configured)")

        # 5. Build the LiveKit AgentSession via the speech-engine seam.
        # session_builder dispatches on engine_mode (realtime today; the modular
        # STT->LLM->TTS pipeline arrives in Phase 2) and constructs the
        # AgentSession the right way for the engine. The realtime model tuning
        # (thinking off, barge-in on, endpointing tuned, temperature lowered)
        # lives in speech_providers.realtime.provider so it is unit-tested
        # independently of this live entrypoint — see that module's docstring for
        # the rationale and the model-options analysis for why the 2.5
        # native-audio model is kept (not the 3.1 "live" preview).
        #
        # TODO: Phase 3 — load speech_config from voice_agent.speech_config (the
        # new JSONB column) instead of the default realtime config, so each agent
        # can pick its engine and per-stage models. The api_keys map will be
        # assembled by a dedicated key_resolver that resolves per-provider
        # org-vs-platform keys (extending the Google-only resolution above).
        speech_config = default_realtime_config()
        api_keys = {"google": api_key}
        agent_session = build_agent_session(
            speech_config=speech_config,
            api_keys=api_keys,
            userdata={"agent_id": agent_id, "agent_name": voice_agent.name},
        )

        await agent_session.start(
            room=ctx.room,
            agent=livekit_agent,
            room_options=room_io.RoomOptions(
                delete_room_on_close=True,
            ),
        )
        logger.info("Agent session started")

        # The session is now live and will outlive this entrypoint (the
        # function returns below while LiveKit drives the conversation). Hand
        # ownership of the MCP clients to the job lifecycle so they are closed
        # on shutdown — NOT in the finally block, which would close them before
        # the model invokes any MCP tool (regression: "McpClient is closed").
        _hand_off_mcp_clients_to_session(ctx, mcp_clients)
        mcp_clients_handed_off = True

        # Start conversation with greeting
        await agent_session.generate_reply(
            instructions="Greet the user warmly and ask how you can help."
        )

        # 7. Handle participant events
        @ctx.room.on("participant_connected")
        def on_participant_connected(participant):
            logger.info(
                f"Participant connected: {participant.identity}, kind: {participant.kind}"
            )

        @ctx.room.on("participant_disconnected")
        def on_participant_disconnected(participant):
            logger.info(f"Participant disconnected: {participant.identity}")

    except Exception as e:
        logger.error(f"Worker entrypoint error: {e}", exc_info=True)

        # Cleanup only on error: Close agent session if exists
        if agent_session:
            try:
                logger.info("Shutting down agent session (error cleanup)")
                agent_session.shutdown(drain=True)
            except Exception as cleanup_error:
                logger.error(
                    f"Error shutting down agent session: {cleanup_error}", exc_info=True
                )

        # Cleanup only on error: Close LiveKit room if exists
        if room_name:
            try:
                logger.info(f"Closing LiveKit room (error cleanup): {room_name}")
                await livekit_service.delete_room(room_name)
            except Exception as cleanup_error:
                logger.error(
                    f"Error closing LiveKit room {room_name}: {cleanup_error}",
                    exc_info=True,
                )

    finally:
        # Close MCP clients ONLY when setup failed before the session took
        # ownership (``mcp_clients_handed_off`` is False). Once the session
        # started, the clients are closed by the shutdown callback registered in
        # :func:`_hand_off_mcp_clients_to_session`; closing them here would kill
        # every MCP tool for the rest of the session ("McpClient is closed").
        # The legacy BaseTool path has nothing to close (mcp_clients is empty).
        # (RFC §1.1 coexistence: MCP path owns its own lifecycle.)
        await _cleanup_mcp_clients(mcp_clients, mcp_clients_handed_off)


if __name__ == "__main__":
    cli.run_app(server)
