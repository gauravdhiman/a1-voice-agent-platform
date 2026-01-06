import inspect
import logging
import os
from typing import Any

from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    RunContext,
    function_tool,
    cli,
)
from livekit.agents.voice import room_io
from livekit.plugins.google.realtime import RealtimeModel

from shared.voice_agents.service import voice_agent_service
from shared.voice_agents.tool_service import tool_service
from shared.voice_agents.tools.base.registry_livekit import livekit_tool_registry
from shared.voice_agents.livekit_service import livekit_service
from default_system_prompt import default_system_prompt

logger = logging.getLogger("voice-worker")

log_level = logging.DEBUG if os.getenv("DEBUG", "false").lower() == "true" else logging.INFO
logger.setLevel(log_level)

server = AgentServer()

# Register all tool implementations
livekit_tool_registry.register_tools_from_package("shared.voice_agents.tools.implementations")
logger.info(f"Registered tools: {list(livekit_tool_registry._tools.keys())}")


def _create_tool_wrapper(bound_method: Any, func_name: str, param_names: list[str], type_hints: dict) -> Any:
    """
    Create a wrapper function for a tool method.
    
    The wrapper has the same signature as the original method (excluding 'self').
    It accepts all parameters explicitly (no **kwargs), then delegates to the bound method.
    """
    # Get parameter definitions for the wrapper function
    params_def = ["context: RunContext"]
    for param_name in param_names[1:]:
        param_type = type_hints.get(param_name, Any)
        # Get string representation of type
        if hasattr(param_type, '__name__'):
            type_str = param_type.__name__
        elif hasattr(param_type, '_name'):
            type_str = param_type._name
        elif hasattr(param_type, '__origin__'):
            type_str = str(param_type).replace('typing.', '')
        else:
            type_str = 'Any'
        params_def.append(f"{param_name}: {type_str}")
    
    params_str = ", ".join(params_def)
    
    # Get the parameter names for the loop
    other_param_names = param_names[1:]
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
    return await bound_method(context=context, **kwargs)
"""
    
    # Execute the code to create the wrapper function
    namespace = {
        'Any': Any,
        'RunContext': RunContext,
        'bound_method': bound_method,
    }
    local_scope = {}
    exec(wrapper_code, namespace, local_scope)
    wrapper = local_scope[f'{func_name}']
    
    # Copy type hints from original function (excluding 'self')
    wrapper.__annotations__ = type_hints
    
    return wrapper


class DynamicAgent(Agent):
    def __init__(self, instructions: str):
        super().__init__(instructions=instructions)
    
    async def on_enter(self):
        logger.info(f"Agent entered: {self.session.userdata.get('agent_name')}")


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    logger.info(f"Connecting to room {ctx.room.name}")
    await ctx.connect()
    logger.info(f"Connected to room, remote participants: {list(ctx.room.remote_participants.keys())}")

    agent_session = None
    voice_agent = None
    agent_id = None
    room_name = ctx.room.name

    try:
        logger.info(f"Room name from job: {room_name}")

        phone_number = None
        try:
            # 1. Extract phone number from room name
            # Room name format: call_NUMBER_random
            parts = room_name.split("_")
            phone_number = parts[1]
            logger.info(f"Extracted phone number: {phone_number}")
        except (IndexError, AttributeError) as e:
            logger.error(f"Failed to extract phone number from room name '{room_name}': {e}")
            return

        # 2. Fetch agent by phone number
        voice_agent, error = await voice_agent_service.get_agent_by_phone(phone_number)
        if error or not voice_agent:
            logger.error(f"Failed to fetch agent for phone {phone_number}: {error}")
            return

        agent_id = voice_agent.id
        logger.info(f"Found agent ID: {agent_id} for phone: {phone_number}")

        logger.info(f"Starting Gemini S2S assistant for agent: {voice_agent.name}")

        # 3. Prepare tools for this agent
        logger.info("Fetching current tools from database")
        agent_tools, error = await tool_service.get_agent_tools_with_sensitive_config(voice_agent.id)
        if error:
            logger.error(f"Error fetching agent tools: {error}")
            agent_tools = []

        # Build tools programmatically using function_tool() with adapters
        livekit_tools = []

        for agent_tool in agent_tools:
            if not agent_tool.is_enabled or not agent_tool.tool:
                continue

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
            logger.debug(f"Config keys: {list(tool_config.keys()) if tool_config else []}")
            logger.debug(f"Sensitive config keys: {list(tool_sensitive_config.keys()) if tool_sensitive_config else []}")
            tool_instance = tool_class(config=tool_config, sensitive_config=tool_sensitive_config)

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
                    logger.debug(f"Function {func_name} is unselected for agent {agent_id}")
                    continue
                
                # Get the bound method
                bound_method = getattr(tool_instance, func_name)
                
                # Get the original function from the class (not the bound method)
                original_func = getattr(tool_class, func_name)
                sig = inspect.signature(original_func)
                
                # Get parameters excluding 'self'
                param_names = [name for name in sig.parameters.keys() if name != 'self']
                if not param_names:
                    logger.error(f"Function {func_name} has no parameters (excluding self)")
                    continue
                
                # Get type hints from original function
                type_hints = {}
                if hasattr(original_func, '__annotations__'):
                    type_hints = {k: v for k, v in original_func.__annotations__.items() if k != 'self'}
                
                logger.debug(f"Creating wrapper for {func_name}")
                logger.debug(f"  Parameters: {param_names}")
                logger.debug(f"  Type hints: {type_hints}")
                
                # Create wrapper function
                # The key insight: create a simple wrapper with explicit parameters
                # that match the original function (excluding 'self')
                wrapper = _create_tool_wrapper(bound_method, func_name, param_names, type_hints)
                
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

        livekit_agent = DynamicAgent(
            instructions=voice_agent.system_prompt or default_system_prompt,
        )

        await livekit_agent.update_tools(livekit_tools)
        logger.info(f"Updated agent with {len(livekit_tools)} tools")

        # 4. Create Gemini RealtimeModel
        model = RealtimeModel(
            model="gemini-2.5-flash-native-audio-preview-12-2025",
            api_key=os.getenv("GEMINI_API_KEY"),
            voice="Puck",
            temperature=0.8,
        )

        # 5. Create LiveKit Agent
        # 6. Start Session
        agent_session = AgentSession(
            llm=model,
            userdata={
                "agent_id": agent_id,
                "agent_name": voice_agent.name
            }
        )

        await agent_session.start(
            room=ctx.room,
            agent=livekit_agent,
            room_options=room_io.RoomOptions(
                delete_room_on_close=True,
            ),
        )
        logger.info("Agent session started")

        # Start conversation with greeting
        await agent_session.generate_reply(
            instructions="Greet the user warmly and ask how you can help."
        )

        # 7. Handle participant events
        @ctx.room.on("participant_connected")
        def on_participant_connected(participant):
            logger.info(f"Participant connected: {participant.identity}, kind: {participant.kind}")

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
                logger.error(f"Error shutting down agent session: {cleanup_error}", exc_info=True)

        # Cleanup only on error: Close LiveKit room if exists
        if room_name:
            try:
                logger.info(f"Closing LiveKit room (error cleanup): {room_name}")
                await livekit_service.delete_room(room_name)
            except Exception as cleanup_error:
                logger.error(f"Error closing LiveKit room {room_name}: {cleanup_error}", exc_info=True)


if __name__ == "__main__":
    cli.run_app(server)
