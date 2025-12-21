"""
Voice Agent service for managing agents in a multi-tenant SaaS platform.
"""
import logging
from typing import Optional, List
from uuid import UUID
from opentelemetry import trace, metrics
from config import supabase_config
from src.voice_agents.models import VoiceAgent, VoiceAgentCreate, VoiceAgentUpdate

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

agent_operations_counter = meter.create_counter(
    "voice_agent.operations",
    description="Number of voice agent operations"
)

agent_errors_counter = meter.create_counter(
    "voice_agent.errors",
    description="Number of voice agent operation errors"
)


class VoiceAgentService:
    """Service for handling voice agent operations."""
    
    def __init__(self):
        self.supabase_config = supabase_config
    
    @property
    def supabase(self):
        """Get Supabase client."""
        return self.supabase_config.client
    
    @tracer.start_as_current_span("voice_agent.create_agent")
    async def create_agent(self, agent_data: VoiceAgentCreate) -> tuple[Optional[VoiceAgent], Optional[str]]:
        """Create a new voice agent."""
        agent_operations_counter.add(1, {"operation": "create_agent"})
        try:
            response = self.supabase.table("voice_agents").insert({
                "organization_id": str(agent_data.organization_id),
                "name": agent_data.name,
                "phone_number": agent_data.phone_number,
                "system_prompt": agent_data.system_prompt,
                "is_active": agent_data.is_active
            }).execute()
            
            if not response.data:
                return None, "Failed to create agent"
            
            agent_dict = response.data[0]
            return VoiceAgent(**agent_dict), None
        except Exception as e:
            logger.error(f"Error creating agent: {e}", exc_info=True)
            agent_errors_counter.add(1, {"operation": "create_agent", "error": str(e)})
            return None, str(e)

    @tracer.start_as_current_span("voice_agent.get_agent_by_id")
    async def get_agent_by_id(self, agent_id: UUID) -> tuple[Optional[VoiceAgent], Optional[str]]:
        """Get an agent by its ID."""
        try:
            response = self.supabase.table("voice_agents").select("*").eq("id", str(agent_id)).execute()
            if not response.data:
                return None, "Agent not found"
            return VoiceAgent(**response.data[0]), None
        except Exception as e:
            logger.error(f"Error getting agent {agent_id}: {e}")
            return None, str(e)

    @tracer.start_as_current_span("voice_agent.get_agents_by_organization")
    async def get_agents_by_organization(self, org_id: UUID) -> tuple[List[VoiceAgent], Optional[str]]:
        """Get all agents for an organization."""
        try:
            response = self.supabase.table("voice_agents").select("*").eq("organization_id", str(org_id)).execute()
            agents = [VoiceAgent(**item) for item in response.data]
            return agents, None
        except Exception as e:
            logger.error(f"Error getting agents for org {org_id}: {e}")
            return [], str(e)

    @tracer.start_as_current_span("voice_agent.update_agent")
    async def update_agent(self, agent_id: UUID, agent_data: VoiceAgentUpdate) -> tuple[Optional[VoiceAgent], Optional[str]]:
        """Update a voice agent."""
        try:
            update_data = agent_data.model_dump(exclude_unset=True)
            if not update_data:
                return await self.get_agent_by_id(agent_id)
            
            response = self.supabase.table("voice_agents").update(update_data).eq("id", str(agent_id)).execute()
            if not response.data:
                return None, "Agent not found or update failed"
            return VoiceAgent(**response.data[0]), None
        except Exception as e:
            logger.error(f"Error updating agent {agent_id}: {e}")
            return None, str(e)

    @tracer.start_as_current_span("voice_agent.delete_agent")
    async def delete_agent(self, agent_id: UUID) -> tuple[bool, Optional[str]]:
        """Delete a voice agent."""
        try:
            response = self.supabase.table("voice_agents").delete().eq("id", str(agent_id)).execute()
            if not response.data:
                return False, "Agent not found or delete failed"
            return True, None
        except Exception as e:
            logger.error(f"Error deleting agent {agent_id}: {e}")
            return False, str(e)


voice_agent_service = VoiceAgentService()
