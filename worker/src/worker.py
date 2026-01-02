import logging
import os
import json
from typing import Annotated, Optional
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    WorkerOptions,
    WorkerType,
    cli,
    function_tool,
    RunContext,
    AgentSession,
)
from livekit.plugins.google.realtime import RealtimeModel

from shared.voice_agents.service import voice_agent_service
from shared.voice_agents.tool_service import tool_service
from shared.voice_agents.tools.base.registry_livekit import livekit_tool_registry
from shared.voice_agents.session_service import session_manager

logger = logging.getLogger("voice-worker")
logger.setLevel(logging.INFO)

async def entrypoint(ctx: JobContext):
    logger.info(f"Connecting to room {ctx.room.name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    # 1. Identify the agent from room metadata
    metadata_str = ctx.room.metadata
    if not metadata_str:
        logger.warning("No room metadata found, waiting for participant...")
        # Sometimes metadata is on the job or room might take a second
        metadata_str = ctx.job.metadata

    if not metadata_str:
        logger.error("Could not find agent_id in metadata")
        return

    metadata = json.loads(metadata_str)
    agent_id = metadata.get("agent_id")
    if not agent_id:
        logger.error("agent_id missing in metadata")
        return

    agent, error = await voice_agent_service.get_agent_by_id(agent_id)
    if error or not agent:
        logger.error(f"Failed to fetch agent {agent_id}: {error}")
        return
    
    logger.info(f"Starting Gemini S2S assistant for agent: {agent.name}")

    # 2. Prepare tools for this agent
    # Get session snapshot if available
    session_id = metadata.get("session_id")
    call_session = session_manager.get_session(session_id) if session_id else None
    
    if call_session:
        logger.info(f"Using session snapshot for session: {session_id}")
        agent_tools = call_session.tools
    else:
        logger.info("No session snapshot found, fetching current tools")
        agent_tools, error = await tool_service.get_agent_tools(agent.id)
        if error:
            agent_tools = []

    # Build wrapped function list for LiveKit
    wrapped_functions = []
    
    for agent_tool in agent_tools:
        if not agent_tool.is_enabled or not agent_tool.tool:
            continue
            
        tool_name = agent_tool.tool.name
        tool_config = agent_tool.config or {}
        tool_sensitive_config = agent_tool.sensitive_config or {}

        # Get tool class and @function_tool methods
        tool_class = livekit_tool_registry.get_tool_class(tool_name)
        if not tool_class:
            logger.warning(f"Tool {tool_name} not found in registry, skipping")
            continue

        # Get @function_tool decorated methods
        functions = livekit_tool_registry.get_tool_functions(tool_name)

        # Filter out unselected functions (with safety checks for stale function names)
        unselected_func_names = agent_tool.unselected_functions or []
        actual_func_names = {func.__name__ for func in functions}

        # Check for stale unselected functions and log warnings
        stale_functions = set(unselected_func_names) - actual_func_names
        if stale_functions:
            logger.warning(
                f"Found stale unselected functions for tool {tool_name}: {stale_functions}. "
                f"These functions no longer exist in code and will be ignored."
            )

        # Create wrapper for each function
        for func in functions:
            func_name = func.__name__

            # Skip if unselected (only check if function still exists)
            if func_name in unselected_func_names and func_name in actual_func_names:
                logger.debug(f"Function {func_name} is unselected for agent {agent_id}")
                continue

            # Create wrapper function that injects config into RunContext
            async def wrapped_function(context: RunContext, **kwargs):
                # Inject config into RunContext.userdata
                context.userdata.update({
                    "tool_config": tool_config,
                    "sensitive_config": tool_sensitive_config,
                    "agent_id": agent_id,
                    "agent_name": agent.name
                })
                # Call the original function
                return await func(context, **kwargs)

            # Set name and docstring on wrapper for LiveKit's schema extraction
            wrapped_function.__name__ = func_name
            wrapped_function.__doc__ = func.__doc__

            # Decorate with @function_tool for LiveKit
            decorated_function = function_tool()(wrapped_function)
            wrapped_functions.append(decorated_function)
            logger.info(f"Registered function: {func_name} for tool {tool_name}")

    # 3. Create Gemini RealtimeModel
    # Note: Using the model name from the example
    model = RealtimeModel(
        model="gemini-2.5-flash-preview-native-audio-dialog",
        api_key=os.getenv("GEMINI_API_KEY"),
        voice="Puck",
        temperature=0.8,
        instructions=agent.system_prompt or "You are a professional AI assistant.",
        tools=wrapped_functions,
    )

    # 4. Start the Session
    session = AgentSession(
        llm=model,
    )

    await session.start(room=ctx.room)
    logger.info("Agent session started")
    
    # 5. Handle cleanup when participant leaves
    @ctx.room.on("participant_disconnected")
    def on_participant_disconnected(participant):
        logger.info(f"Participant {participant.identity} disconnected, ending session")
        if session_id:
            session_manager.end_session(session_id)
        # We can also shutdown the job here if needed
        # ctx.shutdown()

if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            worker_type=WorkerType.ROOM,
        )
    )
