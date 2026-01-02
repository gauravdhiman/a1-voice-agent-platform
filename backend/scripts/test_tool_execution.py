import asyncio
import os
import sys
from uuid import UUID

# Add backend to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# DEPRECATED: AgentExecutor has been removed in favor of LiveKit's native @function_tool pattern
# This test script is no longer functional with the new architecture.
# Tool execution is now handled by the worker using LiveKit's function calling.
from src.voice_agents.agent_executor import AgentExecutor
from src.voice_agents.session_service import session_manager
from src.voice_agents.tool_service import tool_service
from src.voice_agents.tool_models import AgentToolCreate, AgentToolUpdate

async def test_flow():
    # 1. Get an existing agent (or create one if needed, but assuming one exists for test)
    # For demo, we'll just try to find the first agent in DB
    from src.voice_agents.service import voice_agent_service
    agents, _ = await voice_agent_service.get_all_agents()
    if not agents:
        print("No agents found. Please create one in the UI first.")
        return
    
    agent = agents[0]
    agent_id = agent.id
    print(f"Testing with Agent: {agent.name} ({agent_id})")

    # 2. Find Google Calendar tool
    tools, _ = await tool_service.get_platform_tools()
    gcal_tool = next((t for t in tools if "Calendar" in t.name), None)
    if not gcal_tool:
        print("Google Calendar tool not found in platform_tools.")
        return

    # 3. Enable it for the agent
    print(f"Enabling {gcal_tool.name} for agent...")
    await tool_service.configure_agent_tool(AgentToolCreate(
        agent_id=agent_id,
        tool_id=gcal_tool.id,
        is_enabled=True,
        config={"calendar_id": "primary"}
    ))

    # 4. Execute tool WITHOUT session (direct DB fetch)
    print("\n--- Execution 1: Direct (No Session) ---")
    executor = AgentExecutor(agent_id)
    try:
        result = await executor.run_tool(gcal_tool.name, action="list_events")
        print(f"Success: {result}")
    except Exception as e:
        print(f"Error: {e}")

    # 5. Start a session (Snapshots tools)
    print("\n--- Starting Session (Snapshotting) ---")
    session = await session_manager.start_session(agent_id)
    print(f"Session started: {session.session_id}")
    print(f"Tools in snapshot: {[t.tool.name for t in session.tools if t.tool]}")

    # 6. Disable tool in DB
    print("\n--- Disabling Tool in DB ---")
    agent_tools, _ = await tool_service.get_agent_tools(agent_id)
    at = next((at for at in agent_tools if at.tool_id == gcal_tool.id), None)
    if at:
        await tool_service.update_agent_tool(at.id, AgentToolUpdate(is_enabled=False))
        print("Tool disabled in database.")

    # 7. Execute WITH session (should still work because of snapshot)
    print("\n--- Execution 2: With Session Snapshot (Should Succeed) ---")
    executor_with_session = AgentExecutor(agent_id, session=session)
    try:
        result = await executor_with_session.run_tool(gcal_tool.name, action="list_events")
        print(f"Success (from snapshot): {result}")
    except Exception as e:
        print(f"Error: {e}")

    # 8. Execute WITHOUT session (should fail)
    print("\n--- Execution 3: Without Session (Should Fail) ---")
    executor_no_session = AgentExecutor(agent_id)
    try:
        result = await executor_no_session.run_tool(gcal_tool.name, action="list_events")
        print(f"Success: {result}")
    except Exception as e:
        print(f"Expected Failure: {e}")

if __name__ == "__main__":
    asyncio.run(test_flow())
