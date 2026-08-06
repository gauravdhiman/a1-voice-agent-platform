"""
Supabase configuration and client setup.
Handles authentication, database, and other Supabase services.
"""

import logging
import time
from typing import Optional

from supabase import Client, create_client

from shared.config.settings import settings

logger = logging.getLogger(__name__)


def create_isolated_supabase_client() -> Client:
    """Return a throwaway Supabase client for auth-only operations.

    Auth responses from ``sign_up``, ``sign_in_with_password``, and
    ``verify_otp`` attach the end-user JWT to the client. Those calls must
    never run on the shared service-role clients used for database writes,
    or PostgREST will enforce RLS with the user token instead of bypassing
    it with the service role key.
    """
    if not settings.supabase_url or not settings.supabase_service_key:
        raise ValueError(
            "Supabase is not configured. Set SUPABASE_URL and SUPABASE_SERVICE_KEY."
        )
    return create_client(settings.supabase_url, settings.supabase_service_key)


class SupabaseConfig:
    """Supabase client configuration and management."""

    def __init__(self):
        self._client: Optional[Client] = None
        self._service_client: Optional[Client] = None
        self._last_error_time: Optional[float] = None

    def _build_client(self) -> Optional[Client]:
        if settings.supabase_url and settings.supabase_service_key:
            return create_client(
                supabase_url=settings.supabase_url,
                supabase_key=settings.supabase_service_key,
            )
        return None

    @property
    def client(self) -> Optional[Client]:
        """Get or create Supabase client for auth and legacy callers.

        Prefer ``service_client`` for database writes so auth session state
        on this client cannot break service-role RLS bypass.
        """
        if self._client is None:
            self._client = self._build_client()
            if self._client is not None:
                logger.debug("Created new Supabase client")

        return self._client

    @property
    def service_client(self) -> Optional[Client]:
        """Get Supabase client dedicated to service-role database operations.

        This client must never be used for end-user auth flows (sign-up,
        sign-in, verify_otp) so PostgREST always uses the service role key.
        """
        if self._service_client is None:
            self._service_client = self._build_client()
            if self._service_client is not None:
                logger.debug("Created new Supabase service client")

        return self._service_client

    def reset_client(self) -> None:
        """Reset the client to force recreation on next access.

        Call this when encountering SSL/connection errors to get a fresh connection.
        """
        for attr in ("_client", "_service_client"):
            client = getattr(self, attr)
            if client is not None:
                try:
                    client.postgrest.session.close()
                except Exception:
                    pass
                setattr(self, attr, None)
        self._last_error_time = time.time()
        logger.debug("Reset Supabase clients due to connection error")

    def is_configured(self) -> bool:
        """Check if Supabase is properly configured."""
        return bool(settings.supabase_url and settings.supabase_service_key)

    def health_check(self) -> bool:
        """Check if Supabase connection is healthy."""
        try:
            if not self.is_configured() or not self.client:
                return False

            # Simple health check by trying to access the auth service
            # This will test if the client can actually connect to Supabase
            _ = self.client.auth.get_session()
            return True
        except Exception as e:
            print(f"Supabase health check failed: {e}")
            return False


# Global Supabase instance
supabase_config = SupabaseConfig()
