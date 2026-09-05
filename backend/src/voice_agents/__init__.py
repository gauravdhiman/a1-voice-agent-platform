from src.voice_agents.demo_public_routes import demo_public_router
from src.voice_agents.embed_routes import embed_router
from src.voice_agents.platform_skill_routes import platform_skill_router
from src.voice_agents.preset_routes import preset_router
from src.voice_agents.routes import agent_router
from src.voice_agents.skill_routes import skill_router
from src.voice_agents.tool_routes import organization_tool_router, tool_router
from src.voice_agents.voice_routes import voice_router

__all__ = [
    agent_router,
    tool_router,
    organization_tool_router,
    voice_router,
    embed_router,
    skill_router,
    platform_skill_router,
    preset_router,
    demo_public_router,
]
