"""
Tool service for managing platform tools and agent-specific tool configurations.
"""
import logging
from typing import Optional, List
from uuid import UUID
from opentelemetry import trace
from config import supabase_config
from src.common.security import encrypt_data, decrypt_data
from src.voice_agents.tool_models import PlatformTool, PlatformToolCreate, PlatformToolUpdate, AgentTool, AgentToolCreate, AgentToolUpdate

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class ToolService:
    """Service for handling platform tools and agent tool configurations."""
    
    def __init__(self):
        self.supabase_config = supabase_config
    
    @property
    def supabase(self):
        """Get Supabase client."""
        return self.supabase_config.client
    
    # Platform Tools
    @tracer.start_as_current_span("tool.create_platform_tool")
    async def create_platform_tool(self, tool_data: PlatformToolCreate) -> tuple[Optional[PlatformTool], Optional[str]]:
        """Create a new platform tool (Admin only)."""
        try:
            response = self.supabase.table("platform_tools").insert(tool_data.model_dump()).execute()
            if not response.data:
                return None, "Failed to create platform tool"
            return PlatformTool(**response.data[0]), None
        except Exception as e:
            logger.error(f"Error creating platform tool: {e}")
            return None, str(e)

    @tracer.start_as_current_span("tool.get_platform_tools")
    async def get_platform_tools(self, only_active: bool = True) -> tuple[List[PlatformTool], Optional[str]]:
        """Get all platform tools."""
        try:
            query = self.supabase.table("platform_tools").select("*")
            if only_active:
                query = query.eq("is_active", True)
            response = query.execute()
            tools = [PlatformTool(**item) for item in response.data]
            return tools, None
        except Exception as e:
            logger.error(f"Error getting platform tools: {e}")
            return [], str(e)

    # Agent Tools
    @tracer.start_as_current_span("tool.configure_agent_tool")
    async def configure_agent_tool(self, agent_tool_data: AgentToolCreate) -> tuple[Optional[AgentTool], Optional[str]]:
        """Configure a tool for an agent (upsert)."""
        try:
            # Prepare data for Supabase
            data = agent_tool_data.model_dump()
            
            # Encrypt sensitive config if present
            if agent_tool_data.sensitive_config:
                data["sensitive_config"] = encrypt_data(agent_tool_data.sensitive_config)
            
            # Check if configuration already exists
            existing = self.supabase.table("agent_tools")\
                .select("*")\
                .eq("agent_id", str(agent_tool_data.agent_id))\
                .eq("tool_id", str(agent_tool_data.tool_id))\
                .execute()
            
            if existing.data:
                # Update
                update_payload = agent_tool_data.model_dump(exclude={"agent_id", "tool_id"})
                if agent_tool_data.sensitive_config:
                    update_payload["sensitive_config"] = data["sensitive_config"]
                
                response = self.supabase.table("agent_tools")\
                    .update(update_payload)\
                    .eq("id", existing.data[0]["id"])\
                    .execute()
            else:
                # Insert
                response = self.supabase.table("agent_tools").insert(data).execute()
            
            if not response.data:
                return None, "Failed to configure agent tool"
            
            # Decrypt sensitive config for the return model
            result_data = response.data[0]
            if result_data.get("sensitive_config"):
                result_data["sensitive_config"] = decrypt_data(result_data["sensitive_config"])
                
            return AgentTool(**result_data), None
        except Exception as e:
            logger.error(f"Error configuring agent tool: {e}")
            return None, str(e)

    @tracer.start_as_current_span("tool.get_agent_tools")
    async def get_agent_tools(self, agent_id: UUID) -> tuple[List[AgentTool], Optional[str]]:
        """Get all tools configured for an agent, including platform tool details."""
        try:
            # Get agent tool configurations
            response = self.supabase.table("agent_tools")\
                .select("*, tool:platform_tools(*)")\
                .eq("agent_id", str(agent_id))\
                .execute()
            
            agent_tools = []
            for item in response.data:
                # Extract tool details from the joined query
                tool_data = item.pop("tool")
                
                # Decrypt sensitive config if present
                if item.get("sensitive_config"):
                    item["sensitive_config"] = decrypt_data(item["sensitive_config"])
                
                agent_tool = AgentTool(**item)
                if tool_data:
                    agent_tool.tool = PlatformTool(**tool_data)
                agent_tools.append(agent_tool)
                
            return agent_tools, None
        except Exception as e:
            logger.error(f"Error getting agent tools for agent {agent_id}: {e}")
            return [], str(e)

    @tracer.start_as_current_span("tool.update_agent_tool")
    async def update_agent_tool(self, agent_tool_id: UUID, update_data: AgentToolUpdate) -> tuple[Optional[AgentTool], Optional[str]]:
        """Update an agent tool configuration."""
        try:
            data = update_data.model_dump(exclude_unset=True)
            
            # Encrypt sensitive config if present in update
            if update_data.sensitive_config is not None:
                data["sensitive_config"] = encrypt_data(update_data.sensitive_config)
                
            response = self.supabase.table("agent_tools")\
                .update(data)\
                .eq("id", str(agent_tool_id))\
                .execute()
                
            if not response.data:
                return None, "Agent tool configuration not found"
            
            # Decrypt sensitive config for the return model
            result_data = response.data[0]
            if result_data.get("sensitive_config"):
                result_data["sensitive_config"] = decrypt_data(result_data["sensitive_config"])
                
            return AgentTool(**result_data), None
        except Exception as e:
            logger.error(f"Error updating agent tool {agent_tool_id}: {e}")
            return None, str(e)


tool_service = ToolService()
