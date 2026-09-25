"""
Shared Organization service for basic operations used by backend and worker.
"""

import logging
from typing import Optional
from uuid import UUID

from opentelemetry import trace

from shared.config import supabase_config
from shared.organization.models import OrganizationRuntime
from supabase import Client

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class BaseOrganizationService:
    """Base service for handling organization operations."""

    def __init__(self):
        self.supabase_config = supabase_config

    @property
    def supabase(self) -> Client:
        """Get Supabase client, raise error if not configured."""
        if not self.supabase_config.is_configured():
            logger.error(
                "Supabase is not configured. Please set SUPABASE_URL and SUPABASE_SERVICE_KEY."
            )
            raise ValueError(
                "Supabase is not configured. Please set SUPABASE_URL and SUPABASE_SERVICE_KEY."
            )
        client = self.supabase_config.service_client
        if client is None:
            raise ValueError(
                "Supabase is not configured. Please set SUPABASE_URL and SUPABASE_SERVICE_KEY."
            )
        return client

    @tracer.start_as_current_span("organization.get_organization_by_id")
    async def get_organization_by_id(
        self, org_id: UUID
    ) -> tuple[Optional[OrganizationRuntime], Optional[str]]:
        """Get an organization by its ID."""
        try:
            response = (
                self.supabase.table("organizations")
                .select("*")
                .eq("id", str(org_id))
                .execute()
            )

            if not response.data:
                logger.warning(f"Organization not found: {org_id}")
                return None, "Organization not found"

            org_dict = response.data[0]
            # The worker needs the opaque provider-credentials ciphertext at
            # runtime. OrganizationRuntime excludes it from serialization so
            # callers cannot accidentally return it from an API response.
            organization = OrganizationRuntime(**org_dict)
            return organization, None

        except Exception as e:
            logger.error(
                f"Exception while getting organization {org_id}: {e}", exc_info=True
            )
            return None, str(e)
