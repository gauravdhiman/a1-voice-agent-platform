"""Token Refresh Service

This service automatically refreshes OAuth tokens before they expire.
It runs as a background task using APScheduler.

TODO: Future Enhancement
------------------------
When scaling to multiple backend instances, this approach will cause race conditions
as each instance will attempt to refresh tokens independently. Migrate to Celery + Redis
for distributed task queue with proper locking.

Current approach works for single-instance deployments.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from uuid import UUID

import httpx

from shared.voice_agents.tool_service import ToolService
from shared.voice_agents.tool_models import AgentTool
from shared.voice_agents.tools.base.oauth_provider_utils import (
    get_oauth_manager,
)
from shared.config import settings

logger = logging.getLogger(__name__)


class TokenRefreshService:
    """Service for automatically refreshing OAuth tokens before they expire.

    This service runs as a background task using APScheduler to check and
    refresh OAuth tokens that are approaching expiration. It ensures that users
    don't experience authentication failures during their sessions.

    Provider-Agnostic Design:
        This service works with ANY OAuth 2.0 provider (Google, Microsoft, GitHub, etc.)
        by reading OAuth configuration dynamically from the database. No provider-specific
        logic is hardcoded - the service uses standard OAuth 2.0 refresh flow with
        parameters (token_url, client_id, client_secret) that are defined in each
        tool's AuthConfig class.

    Configuration:
        Refresh timing is configurable via environment variables:
        - TOKEN_REFRESH_CHECK_INTERVAL_MINUTES: How often to check for expiring tokens (default: 5)
        - TOKEN_REFRESH_EXPIRY_WINDOW_MINUTES: Refresh tokens expiring within this window (default: 15)

    Key Features:
        - Runs every TOKEN_REFRESH_CHECK_INTERVAL_MINUTES as a background task
        - Checks all tools with OAuth authentication
        - Refreshes tokens expiring within TOKEN_REFRESH_EXPIRY_WINDOW_MINUTES
        - Works with any OAuth 2.0 provider (provider-agnostic)
        - Updates database with new encrypted tokens
        - Logs all refresh activities for observability

    Lifecycle:
        - Call start() to begin background refresh loop
        - Call stop() to gracefully shutdown and cancel pending refreshes

    Example:
        ```python
        service = TokenRefreshService(tool_service)
        await service.start()
        # ... service runs in background ...
        await service.stop()
        ```

    Attributes:
        tool_service: Instance of ToolService for database operations
        running: Boolean flag indicating if service is active
        task: Asyncio task running the refresh loop

    Notes:
        - Timing configured via environment variables with good defaults
        - No hardcoded refresh intervals or expiry windows
        - Flexible for different OAuth providers and deployment scenarios
    """

    def __init__(self, tool_service: ToolService) -> None:
        """Initialize token refresh service with tool service dependency.

        Args:
            tool_service: ToolService instance for database operations
        """
        self.tool_service = tool_service
        self.running = False
        self.task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the background token refresh task."""
        if self.running:
            logger.warning("Token refresh service is already running")
            return

        self.running = True
        self.task = asyncio.create_task(self._refresh_loop())
        logger.info("Token refresh service started")

    async def stop(self) -> None:
        """Stop the background token refresh task."""
        if not self.running:
            return

        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Token refresh service stopped")

    async def _refresh_loop(self) -> None:
        """Main loop that checks and refreshes tokens periodically.

        Check interval and expiry window are configurable via environment variables:
        - TOKEN_REFRESH_CHECK_INTERVAL_MINUTES (default: 5)
        - TOKEN_REFRESH_EXPIRY_WINDOW_MINUTES (default: 15)
        """
        check_interval = settings.token_refresh_check_interval_minutes
        expiry_window = settings.token_refresh_expiry_window_minutes

        logger.info(
            f"Token refresh loop: checking every {check_interval} minutes, "
            f"refreshing tokens expiring within {expiry_window} minutes"
        )

        while self.running:
            try:
                await self._refresh_expired_tokens()
                # Check at configured interval
                await asyncio.sleep(check_interval * 60)
            except asyncio.CancelledError:
                logger.info("Token refresh loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in token refresh loop: {e}", exc_info=True)
                # Wait 1 minute before retrying on error
                await asyncio.sleep(60)

    async def _refresh_expired_tokens(self) -> None:
        """Find and refresh tokens that are about to expire.

        This queries all agent_tools that require OAuth and have tokens
        expiring within the next 15 minutes, then refreshes them.
        """
        # Get all agent tools with auth
        # TODO: Create a method in tool_service to get tools requiring auth
        # For now, we'll implement the query here
        agent_tools = await self._get_tools_requiring_auth()

        if not agent_tools:
            logger.debug("No agent tools requiring authentication found")
            return

        logger.info(f"Checking {len(agent_tools)} tools for token refresh")

        refresh_count = 0
        for agent_tool in agent_tools:
            logger.info(f"Processing tool: {agent_tool.tool.name}, enabled: {agent_tool.is_enabled}")
            try:
                refreshed = await self._check_and_refresh_token(agent_tool)
                if refreshed:
                    refresh_count += 1
            except Exception as e:
                logger.error(
                    f"Error checking token for tool {agent_tool.tool.name}: {e}",
                    exc_info=True,
                )

        if refresh_count > 0:
            logger.info(f"Successfully refreshed {refresh_count} token(s)")

    async def _get_tools_requiring_auth(self) -> List[AgentTool]:
        """Get all agent tools that require OAuth authentication.

        Returns:
            List of AgentTool objects with authentication requirements
        """
        tools, error = await self.tool_service.get_all_agent_tools_with_auth()
        if error:
            logger.error(f"Error getting tools requiring auth: {error}")
            return []
        return tools

    async def _check_and_refresh_token(self, agent_tool: AgentTool) -> bool:
        """Check if a token needs refresh and refresh it.

        Args:
            agent_tool: AgentTool instance to check and potentially refresh

        Returns:
            True if token was refreshed, False otherwise

        Notes:
            - Expiry window is configurable via TOKEN_REFRESH_EXPIRY_WINDOW_MINUTES
            - Default: 15 minutes before token expiry
        """
        try:
            now = datetime.now(timezone.utc)
            expiry_window_minutes = settings.token_refresh_expiry_window_minutes
            expiry_threshold = now + timedelta(minutes=expiry_window_minutes)

            # sensitive_config is already decrypted by tool_service.get_all_agent_tools_with_auth()
            sensitive_config = agent_tool.sensitive_config

            if not sensitive_config:
                logger.warning(f"No sensitive_config for tool {agent_tool.tool.name}")
                return False

            # Check if token exists and is expiring
            expires_at = sensitive_config.get("expires_at")
            if not expires_at:
                logger.warning(f"No expires_at info found for tool {agent_tool.tool.name}")
                return False

            expires_datetime = datetime.fromtimestamp(expires_at, timezone.utc)

            # Check if token has already expired
            if expires_datetime < now:
                minutes_expired = (now - expires_datetime).total_seconds() / 60
                logger.warning(
                    f"Token for tool {agent_tool.tool.name} EXPIRED "
                    f"({minutes_expired:.1f} minutes ago)"
                )
                return False

            # Calculate time until expiry
            minutes_until_expiry = (expires_datetime - now).total_seconds() / 60

            # Refresh if expiring within configured window (expires before or at threshold)
            if expires_datetime > expiry_threshold:
                # Token is still valid for more than expiry window, so no refresh needed
                logger.debug(f"Tool {agent_tool.tool.name} token valid for {minutes_until_expiry:.1f} minutes (expires at {expires_datetime.strftime('%H:%M:%S')}), skipping refresh")
                return False

            logger.info(
                f"Token for {agent_tool.tool.name} expires in {minutes_until_expiry:.1f} minutes "
                f"(at {expires_datetime.strftime('%H:%M:%S')} UTC), refreshing..."
            )

            # Check if refresh_token exists
            refresh_token = sensitive_config.get("refresh_token")
            if not refresh_token:
                logger.warning(
                    f"No refresh_token available for tool {agent_tool.tool.name}. "
                    "User will need to re-authenticate."
                )
                return False

            # Get OAuth config using centralized utility
            tool = agent_tool.tool
            auth_config = tool.auth_config

            if not auth_config:
                logger.error(f"No auth_config for tool {tool.name}")
                return False

            # Get OAuth provider manager singleton
            oauth_manager = get_oauth_manager()

            # Extract provider and token_url using singleton manager
            provider, token_url = oauth_manager.extract_oauth_config(auth_config)

            if not token_url:
                logger.error(f"No token_url in auth_config for tool {tool.name}")
                return False

            # Get OAuth credentials using singleton manager
            try:
                credentials = oauth_manager.get_credentials(provider)
            except ValueError as e:
                logger.error(f"Error getting OAuth credentials: {e}")
                return False

            # Get OAuth data for refresh using singleton manager
            oauth_data = oauth_manager.get_auth_data(
                provider=provider,
                flow="refresh",
                refresh_token=refresh_token,
            )

            new_tokens = await self._refresh_oauth_token(
                token_url=token_url,
                oauth_data=oauth_data,
            )

            if not new_tokens:
                logger.error(f"Failed to refresh token for tool {tool.name}")
                return False

            # Update sensitive config with new tokens
            sensitive_config["access_token"] = new_tokens["access_token"]
            if "expires_in" in new_tokens:
                expires_in = new_tokens["expires_in"]
                sensitive_config["expires_at"] = (
                    datetime.now(timezone.utc) + timedelta(seconds=expires_in)
                ).timestamp()
            if "refresh_token" in new_tokens:
                sensitive_config["refresh_token"] = new_tokens["refresh_token"]
                logger.info(f"Received new refresh_token for tool {tool.name}")

            # Update agent_tools table with refreshed tokens
            await self._update_agent_tool(
                agent_tool_id=agent_tool.id,
                sensitive_config=sensitive_config,
                tool_name=agent_tool.tool.name,
            )

            # Database update triggers Supabase Realtime, which auto-updates UI

            return True

        except Exception as e:
            logger.error(
                f"Error refreshing token for tool {agent_tool.tool.name}: {e}",
                exc_info=True,
            )
            return False

    async def _refresh_oauth_token(
        self,
        token_url: str,
        oauth_data: Dict[str, str],
    ) -> Optional[Dict[str, str]]:
        """Refresh OAuth token using refresh_token (provider-agnostic).

        This method implements standard OAuth 2.0 token refresh flow and works
        with any OAuth 2.0 provider (Google, Microsoft, GitHub, etc.)
        as long as the provider follows the OAuth 2.0 specification.

        Args:
            token_url: OAuth provider's token endpoint (from tool's AuthConfig)
            oauth_data: OAuth data dictionary for token refresh (created by centralized utility)

        Returns:
            Dictionary with new tokens if successful, None otherwise.
            Typically includes: access_token, expires_in, optional refresh_token

        Notes:
            - Uses standard OAuth 2.0 grant_type="refresh_token"
            - Works with any provider implementing OAuth 2.0 refresh flow
            - Provider-specific differences handled via centralized OAuth utilities
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=oauth_data)

            if response.status_code != 200:
                logger.error(
                    f"OAuth refresh failed with status {response.status_code}: "
                    f"{response.text}"
                )
                return None

            return response.json()

    async def _update_agent_tool(
        self, agent_tool_id: UUID, sensitive_config: dict[str, str | float], tool_name: str
    ) -> None:
        """Update agent tool with new tokens.

        Args:
            agent_tool_id: ID of the agent_tool to update (UUID)
            sensitive_config: Decrypted dict with new tokens (will be encrypted by tool_service)
            tool_name: Tool name for logging (passed from caller)
        """
        from shared.voice_agents.tool_models import AgentToolUpdate

        update_data = AgentToolUpdate(
            sensitive_config=sensitive_config,
            last_refreshed_at=datetime.now(timezone.utc),
        )

        result, error = await self.tool_service.update_agent_tool(
            agent_tool_id=agent_tool_id, update_data=update_data
        )

        if error:
            logger.error(f"Failed to update {tool_name}: {error}")
        else:
            logger.info(f"Successfully refreshed {tool_name} token")


# Global instance
token_refresh_service: Optional[TokenRefreshService] = None


async def start_token_refresh_service(tool_service: ToolService) -> None:
    """Start the global token refresh service.

    Args:
        tool_service: Instance of ToolService for database operations
    """
    global token_refresh_service
    token_refresh_service = TokenRefreshService(tool_service)
    await token_refresh_service.start()


async def stop_token_refresh_service() -> None:
    """Stop the global token refresh service."""
    global token_refresh_service
    if token_refresh_service:
        await token_refresh_service.stop()
