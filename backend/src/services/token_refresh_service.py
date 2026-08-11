"""Token Refresh Service

This service automatically refreshes OAuth tokens before they expire.
It runs as a background task using APScheduler.

Concurrency: per-agent_tool refresh is guarded by a Postgres-backed lease lock
(:meth:`shared.voice_agents.tool_service.ToolService.claim_refresh_lock` /
``release_refresh_lock``, backed by the ``claim_token_refresh`` /
``release_token_refresh`` SQL functions — see Alembic migration 20260623000001).
Only one backend instance refreshes a given token at a time, even across
multiple instances; a crashed holder's lease auto-expires (TTL) so refresh is
not blocked. Fail-closed: if the lock cannot be acquired/verified, the refresh
is skipped rather than racing.

Parallelism: tokens are refreshed concurrently using ``asyncio.gather`` with a
semaphore to limit the number of simultaneous OAuth round-trips. Concurrency
is configurable via ``TOKEN_REFRESH_MAX_CONCURRENT_REFRESHES`` (default: 5).
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from uuid import UUID

import httpx

from shared.config import settings
from shared.voice_agents.tool_models import AgentTool
from shared.voice_agents.tool_service import ToolService
from shared.voice_agents.tools.base.oauth_provider_utils import get_oauth_manager

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

        Queries all enabled agent_tools that require OAuth and refreshes tokens
        expiring within the configured window.  Refreshes run concurrently with
        a configurable concurrency limit (``TOKEN_REFRESH_MAX_CONCURRENT_REFRESHES``).
        """
        agent_tools = await self._get_tools_requiring_auth()

        if not agent_tools:
            logger.debug("No agent tools requiring authentication found")
            return

        logger.info(f"Checking {len(agent_tools)} tools for token refresh")

        max_concurrent = settings.token_refresh_max_concurrent_refreshes
        semaphore = asyncio.Semaphore(max_concurrent)

        async def _limited_refresh(at: AgentTool) -> bool:
            async with semaphore:
                return await self._check_and_refresh_token(at)

        results = await asyncio.gather(
            *(_limited_refresh(at) for at in agent_tools),
            return_exceptions=True,
        )

        refresh_count = 0
        for at, result in zip(agent_tools, results):
            if isinstance(result, Exception):
                logger.error(
                    f"Error checking token for tool {at.tool.name}: {result}",
                    exc_info=result,
                )
            elif result is True:
                refresh_count += 1

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

        Orchestrates the full lifecycle: expiry check → OAuth config resolution
        → lease acquisition → HTTP refresh → DB update → lease release.

        Args:
            agent_tool: AgentTool instance to check and potentially refresh

        Returns:
            True if token was refreshed, False otherwise
        """
        try:
            needs_refresh, _minutes_until_expiry = self._is_token_expiring(agent_tool)
            if not needs_refresh:
                return False

            oauth_data, token_url = self._resolve_oauth_config(agent_tool)
            if oauth_data is None:
                return False

            return await self._perform_token_refresh(agent_tool, oauth_data, token_url)
        except Exception as e:
            logger.error(
                f"Error refreshing token for {agent_tool.tool.name}: {e}",
                exc_info=True,
            )
            return False

    def _is_token_expiring(self, agent_tool: AgentTool) -> tuple[bool, Optional[float]]:
        """Check whether the token for *agent_tool* needs refresh.

        Args:
            agent_tool: The agent tool whose token to inspect.

        Returns:
            A tuple of ``(needs_refresh, minutes_until_expiry)``.
            ``needs_refresh`` is ``True`` when the token is within the expiry
            window and should be refreshed. ``minutes_until_expiry`` is the
            number of minutes until the token expires (``None`` when
            ``needs_refresh`` is ``False`` for reasons other than "still valid
            for a long time" — e.g. missing config or already expired).
        """
        now = datetime.now(timezone.utc)
        expiry_threshold = now + timedelta(
            minutes=settings.token_refresh_expiry_window_minutes,
        )

        sensitive_config = agent_tool.sensitive_config
        if not sensitive_config:
            logger.warning(f"No sensitive_config for tool {agent_tool.tool.name}")
            return False, None

        expires_at = sensitive_config.get("expires_at")
        if not expires_at:
            logger.warning(f"No expires_at info found for tool {agent_tool.tool.name}")
            return False, None

        expires_datetime = datetime.fromtimestamp(expires_at, timezone.utc)

        if expires_datetime < now:
            minutes_expired = (now - expires_datetime).total_seconds() / 60
            logger.warning(
                f"Token for tool {agent_tool.tool.name} EXPIRED "
                f"({minutes_expired:.1f} minutes ago)"
            )
            return False, None

        minutes_until_expiry = (expires_datetime - now).total_seconds() / 60

        if expires_datetime > expiry_threshold:
            logger.debug(
                f"Tool {agent_tool.tool.name} token valid for "
                f"{minutes_until_expiry:.1f} minutes, skipping refresh"
            )
            return False, None

        logger.info(
            f"Token for {agent_tool.tool.name} expires in "
            f"{minutes_until_expiry:.1f} minutes "
            f"(at {expires_datetime.strftime('%H:%M:%S')} UTC), refreshing..."
        )
        return True, minutes_until_expiry

    def _resolve_oauth_config(
        self,
        agent_tool: AgentTool,
    ) -> tuple[Optional[Dict[str, str]], Optional[str]]:
        """Resolve OAuth provider, token URL and build the refresh request payload.

        Args:
            agent_tool: The agent tool whose OAuth config to resolve.

        Returns:
            A tuple of ``(oauth_data, token_url)``. Both are ``None`` when the
            config is missing or incomplete (errors are logged inside).
        """
        sensitive_config = agent_tool.sensitive_config or {}
        refresh_token = sensitive_config.get("refresh_token")
        if not refresh_token:
            logger.warning(
                f"No refresh_token available for tool {agent_tool.tool.name}. "
                "User will need to re-authenticate."
            )
            return None, None

        auth_config = agent_tool.tool.auth_config
        if not auth_config:
            logger.error(f"No auth_config for tool {agent_tool.tool.name}")
            return None, None

        oauth_manager = get_oauth_manager()
        provider, token_url = oauth_manager.extract_oauth_config(auth_config)

        if not token_url:
            logger.error(f"No token_url in auth_config for tool {agent_tool.tool.name}")
            return None, None

        try:
            oauth_manager.get_credentials(provider)
        except ValueError as e:
            if provider.lower() != "mcp":
                logger.error(f"Error getting OAuth credentials: {e}")
                return None, None

        if provider.lower() == "mcp":
            client_id = (
                sensitive_config.get("oauth_client_id")
                or auth_config.get("client_id")
                or os.getenv("MCP_OAUTH_CLIENT_ID")
            )
            if not client_id:
                logger.error(
                    "No MCP OAuth client_id available for tool %s",
                    agent_tool.tool.name,
                )
                return None, None
            oauth_data = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": client_id,
                "resource": sensitive_config.get("resource")
                or auth_config.get("resource")
                or agent_tool.tool.mcp_server_url
                or "",
            }
            if os.getenv("MCP_OAUTH_CLIENT_SECRET"):
                oauth_data["client_secret"] = os.getenv("MCP_OAUTH_CLIENT_SECRET", "")
            return oauth_data, token_url

        oauth_data = oauth_manager.get_auth_data(
            provider=provider,
            flow="refresh",
            refresh_token=refresh_token,
        )
        return oauth_data, token_url

    async def _perform_token_refresh(
        self,
        agent_tool: AgentTool,
        oauth_data: Dict[str, str],
        token_url: str,
    ) -> bool:
        """Acquire the lease, refresh the token, persist it, and release the lease.

        This is the core "do the work" method — everything that follows the
        expiry check and config resolution.

        Args:
            agent_tool: The agent tool to refresh.
            oauth_data: OAuth refresh request payload.
            token_url: The OAuth provider's token endpoint.

        Returns:
            True on success, False on any failure.
        """
        tool_name = agent_tool.tool.name

        claim_id = await self.tool_service.claim_refresh_lock(
            agent_tool.id,
            lease_seconds=settings.token_refresh_lock_lease_seconds,
        )
        if not claim_id:
            logger.info(
                f"Skipping refresh for {tool_name}: another instance holds the lock"
            )
            return False

        try:
            new_tokens = await self._refresh_oauth_token(
                token_url=token_url,
                oauth_data=oauth_data,
            )
            if not new_tokens:
                logger.error(f"Failed to refresh token for tool {tool_name}")
                return False

            sensitive_config = agent_tool.sensitive_config
            sensitive_config["access_token"] = new_tokens["access_token"]
            if "expires_in" in new_tokens:
                sensitive_config["expires_at"] = (
                    datetime.now(timezone.utc)
                    + timedelta(seconds=new_tokens["expires_in"])
                ).timestamp()
            if "refresh_token" in new_tokens:
                sensitive_config["refresh_token"] = new_tokens["refresh_token"]
                logger.info(f"Received new refresh_token for tool {tool_name}")

            updated = await self._update_agent_tool(
                agent_tool_id=agent_tool.id,
                sensitive_config=sensitive_config,
                tool_name=tool_name,
            )

            if not updated:
                logger.critical(
                    f"Refreshed token for {tool_name} could not be persisted to the "
                    f"DB (provider likely rotated the refresh_token). The stored "
                    f"token is now invalid; the user must re-authenticate this tool."
                )
                return False

            return True
        finally:
            await self.tool_service.release_refresh_lock(agent_tool.id, claim_id)

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
        # Bound the provider round-trip so a hung connection cannot stall the
        # refresh loop (and outlive the lease TTL). 30s is generous for token
        # endpoints; tune via settings if a provider needs more.
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            response = await client.post(token_url, data=oauth_data)

            if response.status_code != 200:
                logger.error(
                    f"OAuth refresh failed with status {response.status_code}: "
                    f"{response.text}"
                )
                return None

            return response.json()

    async def _update_agent_tool(
        self,
        agent_tool_id: UUID,
        sensitive_config: dict[str, str | float],
        tool_name: str,
    ) -> bool:
        """Update agent tool with new tokens.

        Args:
            agent_tool_id: ID of the agent_tool to update (UUID)
            sensitive_config: Decrypted dict with new tokens (will be encrypted by tool_service)
            tool_name: Tool name for logging (passed from caller)

        Returns:
            True if the DB update succeeded, False otherwise. A False return after a
            successful OAuth refresh is critical: the provider likely rotated the
            refresh_token, so the unpersisted new token is lost and the stored one is
            now invalid (the caller logs CRITICAL and the user must re-authenticate).
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
            return False
        logger.info(f"Successfully refreshed {tool_name} token")
        return True


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
