from src.voice_agents.routes import agent_router
from src.voice_agents.tool_routes import tool_router
from src.voice_agents.voice_routes import voice_router
from src.voice_agents.embed_routes import embed_router
from src.voice_agents.skill_routes import skill_router

__all__ = [agent_router, tool_router, voice_router, embed_router, skill_router]
