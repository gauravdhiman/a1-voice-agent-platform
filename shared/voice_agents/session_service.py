import logging
from uuid import UUID, uuid4
from typing import Dict, List, Optional
from datetime import datetime
from .tool_models import AgentTool
from .tool_service import tool_service

logger = logging.getLogger(__name__)

class CallSession:
    def __init__(self, session_id: str, agent_id: UUID, tools: List[AgentTool]):
        self.session_id = session_id
        self.agent_id = agent_id
        self.tools = tools  # Snapshot of tools at session start
        self.start_time = datetime.now()

class SessionManager:
    def __init__(self):
        self._sessions: Dict[str, CallSession] = {}

    async def start_session(self, agent_id: UUID) -> CallSession:
        """
        Start a new call session and snapshot the agent's tools.
        """
        session_id = str(uuid4())
        
        # Snapshot current enabled tools
        agent_tools, error = await tool_service.get_agent_tools(agent_id)
        if error:
            logger.error(f"Failed to snapshot tools for agent {agent_id}: {error}")
            enabled_tools = []
        else:
            enabled_tools = [at for at in agent_tools if at.is_enabled]
        
        session = CallSession(session_id, agent_id, enabled_tools)
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[CallSession]:
        return self._sessions.get(session_id)

    def end_session(self, session_id: str):
        if session_id in self._sessions:
            del self._sessions[session_id]

# Global session manager
session_manager = SessionManager()
