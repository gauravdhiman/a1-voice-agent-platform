"""
Voice Agent service for managing agents in a multi-tenant SaaS platform.
"""

import logging
from typing import List, Optional
from uuid import UUID

from opentelemetry import metrics, trace
from supabase import Client

from shared.config import supabase_config

from .models import DeleteResponse, VoiceAgent, VoiceAgentCreate, VoiceAgentUpdate

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

agent_operations_counter = meter.create_counter(
    "voice_agent.operations", description="Number of voice agent operations"
)

agent_errors_counter = meter.create_counter(
    "voice_agent.errors", description="Number of voice agent operation errors"
)

TERMINAL_PHONE_NUMBER_STATUSES = frozenset({"cancelled", "disconnected"})
ACTIVE_PHONE_NUMBER_STATUSES = (
    "purchased",
    "active",
    "verification_required",
    "release_pending",
)


def merge_phone_number_mappings(
    agent_rows: List[dict], phone_number_rows: List[dict]
) -> List[dict]:
    """Replace legacy agent phone values with assignments from ``phone_numbers``.

    Args:
        agent_rows: Raw voice-agent rows returned from ``voice_agents``.
        phone_number_rows: Rows containing ``assigned_agent_id`` and the
            canonical ``phone_number`` from the source-of-truth table.

    Returns:
        Copies of the agent rows whose ``phone_number`` field is derived from
        the assigned table row. Agents without an assignment receive ``None``;
        the legacy column is intentionally not used as a fallback.

    Notes:
        The API keeps the existing response field for client compatibility,
        but its value is now table-backed. A partial unique index prevents
        multiple active assignments; ``setdefault`` also makes this helper
        deterministic if malformed historical data is encountered.
    """
    assigned_numbers: dict[str, str] = {}
    for row in phone_number_rows:
        agent_id = row.get("assigned_agent_id")
        phone_number = row.get("phone_number")
        if row.get("status") in TERMINAL_PHONE_NUMBER_STATUSES:
            continue
        if agent_id and phone_number:
            assigned_numbers.setdefault(str(agent_id), str(phone_number))

    return [
        {
            **agent,
            "phone_number": assigned_numbers.get(str(agent.get("id"))),
        }
        for agent in agent_rows
    ]


class VoiceAgentService:
    """Service for handling voice agent operations."""

    def __init__(self) -> None:
        self.supabase_config = supabase_config

    @property
    def supabase(self) -> Optional[Client]:
        """Get Supabase client."""
        return self.supabase_config.client

    def _with_phone_number_mappings(self, agent_rows: List[dict]) -> List[dict]:
        """Attach current phone-number assignments to raw agent rows.

        Args:
            agent_rows: Raw rows returned by an agent query.

        Returns:
            Agent rows with ``phone_number`` sourced from ``phone_numbers``.
            If the assignment lookup fails during a rolling deployment, the
            legacy rows are returned so the agent list remains available while
            the deployment health check reports the underlying issue.
        """
        if not agent_rows:
            return []

        agent_ids = [str(row["id"]) for row in agent_rows if row.get("id")]
        if not agent_ids:
            return merge_phone_number_mappings(agent_rows, [])

        try:
            response = (
                self.supabase.table("phone_numbers")
                .select("assigned_agent_id, phone_number")
                .in_("assigned_agent_id", agent_ids)
                .in_("status", list(ACTIVE_PHONE_NUMBER_STATUSES))
                .execute()
            )
            return merge_phone_number_mappings(agent_rows, response.data or [])
        except Exception as e:
            logger.warning(
                "Unable to load phone-number assignments for agent list; "
                "using legacy response values during rollout: %s",
                e,
            )
            return agent_rows

    @tracer.start_as_current_span("voice_agent.create_agent")
    async def create_agent(
        self, agent_data: VoiceAgentCreate
    ) -> tuple[Optional[VoiceAgent], Optional[str]]:
        """Create a new voice agent."""
        agent_operations_counter.add(1, {"operation": "create_agent"})
        try:
            response = (
                self.supabase.table("voice_agents")
                .insert(
                    {
                        "organization_id": str(agent_data.organization_id),
                        "name": agent_data.name,
                        "phone_number": agent_data.phone_number,
                        "is_active": agent_data.is_active,
                        "persona": agent_data.persona,
                        "tone": agent_data.tone,
                        "mission": agent_data.mission,
                        "custom_instructions": agent_data.custom_instructions,
                        "instructions_markdown": agent_data.instructions_markdown,
                        "preset_id": (
                            str(agent_data.preset_id) if agent_data.preset_id else None
                        ),
                    }
                )
                .execute()
            )

            if not response.data:
                return None, "Failed to create agent"

            agent_dict = self._with_phone_number_mappings([response.data[0]])[0]
            return VoiceAgent(**agent_dict), None
        except Exception as e:
            logger.error(f"Error creating agent: {e}", exc_info=True)
            agent_errors_counter.add(1, {"operation": "create_agent", "error": str(e)})
            return None, str(e)

    @tracer.start_as_current_span("voice_agent.get_agent_by_id")
    async def get_agent_by_id(
        self, agent_id: UUID
    ) -> tuple[Optional[VoiceAgent], Optional[str]]:
        """Get an agent and its current phone assignment in one request."""
        try:
            response = (
                self.supabase.table("voice_agents")
                .select("*, phone_numbers(phone_number, assigned_agent_id, status)")
                .eq("id", str(agent_id))
                .execute()
            )
            if not response.data:
                return None, "Agent not found"
            agent_dict = dict(response.data[0])
            phone_number_rows = agent_dict.pop("phone_numbers", []) or []
            agent_dict = merge_phone_number_mappings([agent_dict], phone_number_rows)[0]
            return VoiceAgent(**agent_dict), None
        except Exception as e:
            logger.error(f"Error getting agent {agent_id}: {e}")
            return None, str(e)

    @tracer.start_as_current_span("voice_agent.get_agent_by_phone")
    async def get_agent_by_phone(
        self, phone_number: str
    ) -> tuple[Optional[VoiceAgent], Optional[str]]:
        """Get an agent mapping from the table-backed phone-number source.

        This compatibility method retains the historical service signature,
        but no longer searches ``voice_agents.phone_number``. Inbound routing
        should still use ``PhoneNumberService.get_routable_agent_id`` so it can
        enforce billing, configuration, and active-agent checks.
        """
        try:
            response = (
                self.supabase.table("phone_numbers")
                .select("assigned_agent_id")
                .eq("phone_number", phone_number)
                .eq("is_incoming_enabled", True)
                .in_("status", ["purchased", "active"])
                .limit(1)
                .execute()
            )
            if not response.data or not response.data[0].get("assigned_agent_id"):
                return None, f"Agent with phone number {phone_number} not found"
            return await self.get_agent_by_id(
                UUID(str(response.data[0]["assigned_agent_id"]))
            )
        except Exception as e:
            logger.error(f"Error getting agent by phone {phone_number}: {e}")
            return None, str(e)

    @tracer.start_as_current_span("voice_agent.get_agents_by_organization")
    async def get_agents_by_organization(
        self, org_id: UUID
    ) -> tuple[List[VoiceAgent], Optional[str]]:
        """Get all agents for an organization."""
        try:
            response = (
                self.supabase.table("voice_agents")
                .select("*")
                .eq("organization_id", str(org_id))
                .execute()
            )
            mapped_rows = self._with_phone_number_mappings(response.data)
            agents = [VoiceAgent(**item) for item in mapped_rows]
            return agents, None
        except Exception as e:
            logger.error(f"Error getting agents for org {org_id}: {e}")
            return [], str(e)

    @tracer.start_as_current_span("voice_agent.get_agents_for_user")
    async def get_agents_for_user(
        self, user_id: UUID
    ) -> tuple[List[VoiceAgent], Optional[str]]:
        """Get all agents for a user across all organizations they are a member of."""
        try:
            # Step 1: Get all organizations for user
            logger.info(f"Step 1: Fetching user_roles for user {user_id}")
            user_roles_response = (
                self.supabase.table("user_roles")
                .select("organization_id")
                .eq("user_id", str(user_id))
                .execute()
            )
            logger.info(
                f"Step 1: Data count: {len(user_roles_response.data) if user_roles_response.data else 0}"
            )

            if not user_roles_response.data:
                logger.warning(f"No user_roles found for user {user_id}")
                return [], None

            # Step 2: Extract organization IDs
            org_ids = [
                item["organization_id"]
                for item in user_roles_response.data
                if item.get("organization_id")
            ]
            logger.info(f"Step 2: Extracted org_ids: {org_ids}")

            if not org_ids:
                logger.warning(f"No organization_ids found for user {user_id}")
                return [], None

            # Step 3: Get all agents for those organizations
            logger.info(f"Step 3: Fetching voice_agents for org_ids: {org_ids}")
            response = (
                self.supabase.table("voice_agents")
                .select("*")
                .in_("organization_id", org_ids)
                .execute()
            )
            logger.info(
                f"Step 3: Data count: {len(response.data) if response.data else 0}"
            )

            mapped_rows = self._with_phone_number_mappings(response.data)
            agents = [VoiceAgent(**item) for item in mapped_rows]
            logger.info(f"Returning {len(agents)} agents for user {user_id}")
            return agents, None
        except Exception as e:
            logger.error(f"Error getting agents for user {user_id}: {e}", exc_info=True)
            return [], str(e)

    @tracer.start_as_current_span("voice_agent.get_public_page_agents")
    async def get_public_page_agents(
        self, organization_id: UUID
    ) -> tuple[list[VoiceAgent], Optional[str]]:
        """List agents published on the organization's public page."""
        try:
            response = (
                self.supabase.table("voice_agents")
                .select("*")
                .eq("organization_id", str(organization_id))
                .eq("is_published_on_public_page", True)
                .eq("is_active", True)
                .execute()
            )
            mapped_rows = self._with_phone_number_mappings(response.data)
            return [VoiceAgent(**item) for item in mapped_rows], None
        except Exception as e:
            logger.error(
                "Error getting public page agents for org %s: %s",
                organization_id,
                e,
                exc_info=True,
            )
            return [], str(e)

    @tracer.start_as_current_span("voice_agent.update_agent")
    async def update_agent(
        self, agent_id: UUID, agent_data: VoiceAgentUpdate
    ) -> tuple[Optional[VoiceAgent], Optional[str]]:
        """Update a voice agent."""
        try:
            # `mode="json"` coerces non-JSON-native fields (e.g. preset_id
            # UUID -> str) so the payload is serializable by Postgrest's stdlib
            # json encoder. Without it, a preset_id UUID raises
            # "Object of type UUID is not JSON serializable" on the Supabase
            # update (HTTP 400).
            update_data = agent_data.model_dump(exclude_unset=True, mode="json")
            if not update_data:
                return await self.get_agent_by_id(agent_id)

            # Inactive agents must not remain listed on the public org page.
            # Clearing publish here closes the activate→publish→deactivate loophole
            # where a deactivated agent would otherwise stay publicly callable.
            if update_data.get("is_active") is False:
                update_data["is_published_on_public_page"] = False

            response = (
                self.supabase.table("voice_agents")
                .update(update_data)
                .eq("id", str(agent_id))
                .execute()
            )
            if not response.data:
                return None, "Agent not found or update failed"
            agent_dict = self._with_phone_number_mappings([response.data[0]])[0]
            return VoiceAgent(**agent_dict), None
        except Exception as e:
            logger.error(f"Error updating agent {agent_id}: {e}")
            return None, str(e)

    @tracer.start_as_current_span("voice_agent.delete_agent")
    async def delete_agent(
        self, agent_id: UUID
    ) -> tuple[Optional[DeleteResponse], Optional[str]]:
        """Delete a voice agent."""
        try:
            response = (
                self.supabase.table("voice_agents")
                .delete()
                .eq("id", str(agent_id))
                .execute()
            )
            if not response.data:
                return None, "Agent not found or delete failed"
            return DeleteResponse(id=agent_id, success=True), None
        except Exception as e:
            logger.error(f"Error deleting agent {agent_id}: {e}")
            return None, str(e)


voice_agent_service = VoiceAgentService()
