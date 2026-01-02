"""
Tool service for managing platform tools and agent-specific tool configurations.
"""
import logging
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from opentelemetry import trace
from shared.config import supabase_config
from shared.common.security import encrypt_data, decrypt_data
from .tool_models import PlatformTool, PlatformToolCreate, AgentToolCreate, AgentToolUpdate, AgentToolResponse, AuthStatus

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


def validate_token_status(sensitive_config: Optional[str]) -> AuthStatus:
    """
    Validate authentication token status from encrypted sensitive config.

    Args:
        sensitive_config: Encrypted JSON string containing OAuth tokens

    Returns:
        AuthStatus enum indicating the authentication state
    """
    if not sensitive_config:
        return AuthStatus.NOT_AUTHENTICATED

    try:
        decrypted_data = decrypt_data(sensitive_config)
        if not decrypted_data or not isinstance(decrypted_data, dict):
            return AuthStatus.NOT_AUTHENTICATED

        access_token = decrypted_data.get("access_token")
        expires_at = decrypted_data.get("expires_at")

        if not access_token or not expires_at:
            return AuthStatus.NOT_AUTHENTICATED

        # Check if token is still valid (with 5 min buffer)
        current_time = datetime.now().timestamp()
        if current_time >= (expires_at - 300):  # 5 minutes buffer
            return AuthStatus.EXPIRED

        return AuthStatus.AUTHENTICATED
    except Exception as e:
        logger.error(f"Error validating token status: {e}")
        return AuthStatus.NOT_AUTHENTICATED


class ToolService:
    """Service for handling platform tools and agent tool configurations."""
    
    def __init__(self):
        self.supabase_config = supabase_config
    
    @property
    def supabase(self):
        """Get Supabase client."""
        return self.supabase_config.client
    
    # Platform Tools
    @tracer.start_as_current_span("tool.upsert_platform_tool")
    async def upsert_platform_tool(self, tool_data: PlatformToolCreate) -> tuple[Optional[PlatformTool], Optional[str]]:
        """Upsert a platform tool by name."""
        try:
            # Check if exists
            existing = self.supabase.table("platform_tools")\
                .select("*")\
                .eq("name", tool_data.name)\
                .execute()

            # Dump model and exclude fields not in DB (auth_type, auth_config)
            data_dict = tool_data.model_dump(exclude_none=True, exclude={'auth_type', 'auth_config'})

            if existing.data:
                response = self.supabase.table("platform_tools")\
                    .update(data_dict)\
                    .eq("id", existing.data[0]["id"])\
                    .execute()
            else:
                response = self.supabase.table("platform_tools")\
                    .insert(data_dict)\
                    .execute()

            if not response.data:
                return None, "Failed to upsert platform tool"
            return PlatformTool(**response.data[0]), None
        except Exception as e:
            logger.error(f"Error upserting platform tool: {e}")
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
    async def configure_agent_tool(self, agent_tool_data: AgentToolCreate) -> tuple[Optional[AgentToolResponse], Optional[str]]:
        """Configure a tool for an agent (upsert)."""
        try:
            # Prepare data for Supabase
            data = agent_tool_data.model_dump()

            # Convert UUID to string for JSON serialization
            data["agent_id"] = str(agent_tool_data.agent_id)
            data["tool_id"] = str(agent_tool_data.tool_id)

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

            # Build response model without sensitive config
            result_data = response.data[0]
            response_dict = {
                "id": result_data["id"],
                "agent_id": result_data["agent_id"],
                "tool_id": result_data["tool_id"],
                "config": result_data.get("config"),
                "unselected_functions": result_data.get("unselected_functions"),
                "is_enabled": result_data.get("is_enabled", True),
                "auth_status": validate_token_status(result_data.get("sensitive_config")),
                "created_at": result_data["created_at"],
                "updated_at": result_data["updated_at"]
            }

            return AgentToolResponse(**response_dict), None
        except Exception as e:
            logger.error(f"Error configuring agent tool: {e}")
            return None, str(e)

    @tracer.start_as_current_span("tool.get_agent_tools")
    async def get_agent_tools(self, agent_id: UUID) -> tuple[List[AgentToolResponse], Optional[str]]:
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

                # Extract token expiry from encrypted config for display
                token_expires_at = None
                try:
                    decrypted_config = decrypt_data(item.get("sensitive_config"))
                    if decrypted_config and isinstance(decrypted_config, dict):
                        token_expires_at = decrypted_config.get("expires_at")
                except Exception:
                    pass

                # Build response without sensitive config
                response_dict = {
                    "id": item["id"],
                    "agent_id": item["agent_id"],
                    "tool_id": item["tool_id"],
                    "config": item.get("config"),
                    "unselected_functions": item.get("unselected_functions"),
                    "is_enabled": item.get("is_enabled", True),
                    "auth_status": validate_token_status(item.get("sensitive_config")),
                    "token_expires_at": token_expires_at,
                    "created_at": item["created_at"],
                    "updated_at": item["updated_at"]
                }

                agent_tool = AgentToolResponse(**response_dict)
                if tool_data:
                    agent_tool.tool = PlatformTool(**tool_data)
                agent_tools.append(agent_tool)

            return agent_tools, None
        except Exception as e:
            logger.error(f"Error getting agent tools for agent {agent_id}: {e}")
            return [], str(e)

    @tracer.start_as_current_span("tool.update_agent_tool")
    async def update_agent_tool(self, agent_tool_id: UUID, update_data: AgentToolUpdate) -> tuple[Optional[AgentToolResponse], Optional[str]]:
        """Update an agent tool configuration."""
        try:
            # Get model dump to extract values
            data = update_data.model_dump(exclude_unset=True)

            # Handle empty lists explicitly - ensure they're included in update
            if update_data.unselected_functions is not None:
                data["unselected_functions"] = update_data.unselected_functions

            # Encrypt sensitive config if present in update
            if update_data.sensitive_config is not None:
                data["sensitive_config"] = encrypt_data(update_data.sensitive_config)

            response = self.supabase.table("agent_tools")\
                .update(data)\
                .eq("id", str(agent_tool_id))\
                .execute()

            if not response.data:
                return None, "Agent tool configuration not found"

            # Build response model without sensitive config
            result_data = response.data[0]
            response_dict = {
                "id": result_data["id"],
                "agent_id": result_data["agent_id"],
                "tool_id": result_data["tool_id"],
                "config": result_data.get("config"),
                "unselected_functions": result_data.get("unselected_functions"),
                "is_enabled": result_data.get("is_enabled", True),
                "auth_status": validate_token_status(result_data.get("sensitive_config")),
                "created_at": result_data["created_at"],
                "updated_at": result_data["updated_at"]
            }

            return AgentToolResponse(**response_dict), None
        except Exception as e:
            logger.error(f"Error updating agent tool {agent_tool_id}: {e}")
            return None, str(e)


tool_service = ToolService()
