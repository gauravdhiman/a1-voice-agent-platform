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


class SupabaseConfig:
    """Supabase client configuration and management."""

    def __init__(self):
        self._client: Optional[Client] = None
        self._last_error_time: Optional[float] = None

    @property
    def client(self) -> Optional[Client]:
        """Get or create Supabase client instance if configured.

        Recreates the client if it was recently reset due to an SSL error.
        """
        if self._client is None:
            if settings.supabase_url and settings.supabase_service_key:
                self._client = create_client(
                    supabase_url=settings.supabase_url,
                    supabase_key=settings.supabase_service_key,
                )
                logger.debug("Created new Supabase client")
            else:
                # Return None if not configured (development mode)
                return None

        return self._client

    def reset_client(self) -> None:
        """Reset the client to force recreation on next access.

        Call this when encountering SSL/connection errors to get a fresh connection.
        """
        if self._client is not None:
            try:
                # Close existing connection if possible
                self._client.postgrest.session.close()
            except Exception:
                pass
            self._client = None
            self._last_error_time = time.time()
            logger.debug("Reset Supabase client due to connection error")

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
