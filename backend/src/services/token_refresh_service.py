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
import base64
import logging
import math
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

import httpx
from src.notifications.oauth_attention_notifier import (
    OAuthAttentionNotificationPhase,
    OAuthAttentionNotifier,
)

from shared.common.security import decrypt_data
from shared.config import settings
from shared.voice_agents.tool_models import AgentTool, ToolSource
from shared.voice_agents.tool_service import ToolService
from shared.voice_agents.tools.base.oauth_provider_utils import get_oauth_manager
from shared.voice_agents.tools.base.oauth_support import (
    OAuthRefreshMode,
    get_oauth_client_auth_method,
    get_oauth_refresh_metadata,
    validate_oauth_endpoint_url,
)

logger = logging.getLogger(__name__)

DEFAULT_ACCESS_TOKEN_LIFETIME_SECONDS = 3600
TOKEN_REFRESH_HTTP_MAX_RETRIES = 3


class OAuthRefreshOutcome(str, Enum):
    """Outcome used to decide whether a connection needs administrator action."""

    NOT_DUE = "not_due"
    REFRESHED = "refreshed"
    MANUAL_REAUTH_REQUIRED = "manual_reauth_required"
    LOCK_UNAVAILABLE = "lock_unavailable"
    AUTOMATIC_REFRESH_FAILED = "automatic_refresh_failed"


class OAuthPerformOutcome(str, Enum):
    """Outcome of the lock/HTTP/persistence portion of one refresh attempt."""

    SUCCEEDED = "succeeded"
    LOCK_UNAVAILABLE = "lock_unavailable"
    FAILED = "failed"


@dataclass(frozen=True)
class OAuthRefreshRequest:
    """Resolved OAuth token-endpoint request for one agent tool.

    Attributes:
        data: Form fields sent to the OAuth token endpoint.
        token_url: OAuth token endpoint URL.
        headers: Optional endpoint headers, such as HTTP Basic client auth.
    """

    data: Dict[str, str]
    token_url: str
    headers: Dict[str, str] = field(default_factory=dict)


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
        - TOKEN_REFRESH_ATTENTION_WINDOW_MINUTES: Notify admins when an
          unrenewable connection is inside this window (default: 30)

    Key Features:
        - Runs every TOKEN_REFRESH_CHECK_INTERVAL_MINUTES as a background task
        - Checks all tools with OAuth authentication
        - Refreshes tokens expiring within TOKEN_REFRESH_EXPIRY_WINDOW_MINUTES
        - Notifies organization admins about manual, unresolved, or failed
          connections inside TOKEN_REFRESH_ATTENTION_WINDOW_MINUTES
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

    def __init__(
        self,
        tool_service: ToolService,
        oauth_attention_notifier: Optional[OAuthAttentionNotifier] = None,
    ) -> None:
        """Initialize token refresh service with tool service dependency.

        Args:
            tool_service: ToolService instance for database operations
        """
        self.tool_service = tool_service
        self.oauth_attention_notifier = (
            oauth_attention_notifier or OAuthAttentionNotifier()
        )
        self.running = False
        self.task: Optional[asyncio.Task] = None
        self._refresh_outcomes: Dict[UUID, OAuthRefreshOutcome] = {}
        self._perform_outcomes: Dict[UUID, OAuthPerformOutcome] = {}

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
                logger.error("Error in token refresh loop (%s)", type(e).__name__)
                # Wait 1 minute before retrying on error
                await asyncio.sleep(60)

    async def _refresh_expired_tokens(self) -> None:
        """Find and refresh tokens that are about to expire.

        Queries all enabled agent_tools that require OAuth and refreshes tokens
        expiring within the configured window.  Refreshes run concurrently with
        a configurable concurrency limit (``TOKEN_REFRESH_MAX_CONCURRENT_REFRESHES``).
        The same pass also checks connections in the wider administrator
        attention window and hands manual/failed-renewal notices to the durable
        notification service.
        """
        agent_tools = await self._get_tools_requiring_auth()

        if not agent_tools:
            logger.debug("No agent tools requiring authentication found")
            return

        logger.info(f"Checking {len(agent_tools)} tools for token refresh")

        # Outcomes are per connection so a failed automatic refresh can be
        # distinguished from a lease held by another backend instance. They
        # also make the notification decision deterministic for this pass.
        self._refresh_outcomes.clear()
        self._perform_outcomes.clear()

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
                    "Error checking token for tool %s (%s)",
                    at.tool.name,
                    type(result).__name__,
                )
            elif result is True:
                refresh_count += 1

        if refresh_count > 0:
            logger.info(f"Successfully refreshed {refresh_count} token(s)")

        notification_semaphore = asyncio.Semaphore(max_concurrent)

        async def _limited_attention(at: AgentTool, result: Any) -> None:
            # Tests and custom callers may replace the refresh worker. Only the
            # real worker records an outcome, so a replacement cannot trigger
            # accidental production notifications.
            if at.id not in self._refresh_outcomes or isinstance(result, Exception):
                return
            async with notification_semaphore:
                await self._notify_if_oauth_attention_required(
                    at, self._refresh_outcomes[at.id]
                )

        await asyncio.gather(
            *(
                _limited_attention(at, result)
                for at, result in zip(agent_tools, results)
            ),
            return_exceptions=True,
        )

    async def _get_tools_requiring_auth(self) -> List[AgentTool]:
        """Get all agent tools that require OAuth authentication.

        Returns:
            List of AgentTool objects with authentication requirements
        """
        tools, error = await self.tool_service.get_all_agent_tools_with_auth()
        if error:
            logger.error("Error getting tools requiring auth")
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
        outcome = OAuthRefreshOutcome.AUTOMATIC_REFRESH_FAILED
        try:
            needs_refresh, _minutes_until_expiry = self._is_token_expiring(agent_tool)
            if not needs_refresh:
                outcome = OAuthRefreshOutcome.NOT_DUE
                return False

            request = self._resolve_oauth_config(agent_tool)
            if request is None:
                outcome = OAuthRefreshOutcome.MANUAL_REAUTH_REQUIRED
                return False

            refreshed = await self._perform_token_refresh(
                agent_tool,
                request.data,
                request.token_url,
                headers=request.headers,
            )
            if refreshed:
                outcome = OAuthRefreshOutcome.REFRESHED
            elif self._perform_outcomes.get(agent_tool.id) == (
                OAuthPerformOutcome.LOCK_UNAVAILABLE
            ):
                outcome = OAuthRefreshOutcome.LOCK_UNAVAILABLE
            else:
                outcome = OAuthRefreshOutcome.AUTOMATIC_REFRESH_FAILED
            return refreshed
        except Exception as e:
            logger.error(
                "Error refreshing token for %s (%s)",
                agent_tool.tool.name,
                type(e).__name__,
            )
            return False
        finally:
            self._refresh_outcomes[agent_tool.id] = outcome

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
        if expires_at in (None, ""):
            if sensitive_config.get("refresh_token"):
                logger.warning(
                    "No expires_at metadata for tool %s; attempting one recovery "
                    "refresh using its refresh token",
                    agent_tool.tool.name,
                )
                return True, None
            logger.warning(f"No expires_at info found for tool {agent_tool.tool.name}")
            return False, None
        try:
            expires_at_value = float(expires_at)
            if not math.isfinite(expires_at_value):
                raise ValueError("expires_at must be finite")
            expires_datetime = datetime.fromtimestamp(expires_at_value, timezone.utc)
        except (TypeError, ValueError, OverflowError, OSError):
            if sensitive_config.get("refresh_token"):
                logger.warning(
                    "Invalid expires_at metadata for tool %s; attempting recovery "
                    "refresh using its refresh token",
                    agent_tool.tool.name,
                )
                return True, None
            logger.warning(
                "Invalid expires_at metadata for tool %s; skipping refresh",
                agent_tool.tool.name,
            )
            return False, None

        if expires_datetime < now:
            minutes_expired = (now - expires_datetime).total_seconds() / 60
            if sensitive_config.get("refresh_token"):
                logger.warning(
                    f"Token for tool {agent_tool.tool.name} EXPIRED "
                    f"({minutes_expired:.1f} minutes ago); attempting refresh"
                )
                return True, -minutes_expired
            logger.warning(
                f"Token for tool {agent_tool.tool.name} EXPIRED "
                f"({minutes_expired:.1f} minutes ago) and has no refresh token"
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

    def _oauth_attention_window(
        self, agent_tool: AgentTool
    ) -> Optional[tuple[OAuthAttentionNotificationPhase, Optional[float]]]:
        """Return the administrator-notification phase for a connection.

        The notification window is intentionally wider than the automatic
        refresh window. A connection that can be renewed automatically is not
        notified merely because it is inside this window; the caller combines
        this timing result with the refresh outcome and OAuth capability.

        Args:
            agent_tool: Internal connection whose decrypted expiry metadata is
                being inspected.

        Returns:
            ``(phase, minutes_until_expiry)`` when the token is expired or will
            expire within the configured attention window; otherwise ``None``.
            A non-empty connection with invalid or missing expiry metadata is
            returned as an expiring attention state with ``None`` minutes so an
            administrator knows the platform cannot verify its lifetime.
        """
        sensitive_config = agent_tool.sensitive_config or {}
        if not sensitive_config:
            return None
        raw_expires_at = sensitive_config.get("expires_at")
        if raw_expires_at in (None, ""):
            return OAuthAttentionNotificationPhase.EXPIRING, None
        try:
            expires_at = float(raw_expires_at)
            if not math.isfinite(expires_at):
                return OAuthAttentionNotificationPhase.EXPIRING, None
            expires_datetime = datetime.fromtimestamp(expires_at, timezone.utc)
        except (TypeError, ValueError, OverflowError, OSError):
            return OAuthAttentionNotificationPhase.EXPIRING, None

        now = datetime.now(timezone.utc)
        minutes_until_expiry = (expires_datetime - now).total_seconds() / 60
        if expires_datetime <= now:
            return OAuthAttentionNotificationPhase.EXPIRED, minutes_until_expiry

        attention_threshold = now + timedelta(
            minutes=settings.token_refresh_attention_window_minutes
        )
        if expires_datetime <= attention_threshold:
            return OAuthAttentionNotificationPhase.EXPIRING, minutes_until_expiry
        return None

    async def _notify_if_oauth_attention_required(
        self,
        agent_tool: AgentTool,
        outcome: OAuthRefreshOutcome,
    ) -> None:
        """Send one deduplicated notice when automatic renewal is unavailable.

        Args:
            agent_tool: Connection being evaluated.
            outcome: Result recorded by the refresh worker for this pass.

        Notes:
            An unknown provider label is not enough to trigger a notice. The
            provider-neutral resolver is consulted first, so an MCP or future
            native tool with a refresh grant and standard token endpoint is
            treated as automatic. A notice is sent only for manual/unresolved
            connections or an automatic attempt that actually failed. A lease
            held by another backend instance is not treated as a failure.
        """
        attention = self._oauth_attention_window(agent_tool)
        if attention is None:
            return

        phase, minutes_until_expiry = attention
        if outcome in {
            OAuthRefreshOutcome.REFRESHED,
            OAuthRefreshOutcome.LOCK_UNAVAILABLE,
        }:
            return

        request = None
        try:
            request = self._resolve_oauth_config(agent_tool)
        except Exception as e:
            logger.error(
                "Unable to determine OAuth renewal capability for %s (%s)",
                agent_tool.tool.name,
                type(e).__name__,
            )

        if (
            request is not None
            and outcome != OAuthRefreshOutcome.AUTOMATIC_REFRESH_FAILED
        ):
            # This includes unknown metadata that resolved to a standard OAuth
            # request. It is a healthy automatic connection, not a manual one.
            return

        if (
            request is not None
            and outcome == OAuthRefreshOutcome.AUTOMATIC_REFRESH_FAILED
        ):
            reason = (
                "The platform could not renew this connection automatically. "
                "Reconnect it to restore the renewal permission."
            )
        else:
            reason = self._oauth_attention_reason(agent_tool)

        try:
            await self.oauth_attention_notifier.notify(
                agent_tool,
                phase=phase,
                minutes_until_expiry=minutes_until_expiry,
                reason=reason,
            )
        except Exception as e:
            # Notification failure must never stop refresh checks for other
            # tools. The notification service records delivery failures and its
            # existing retry scheduler will handle them where possible.
            logger.error(
                "OAuth attention notification failed for %s (%s)",
                agent_tool.tool.name,
                type(e).__name__,
            )

    def _oauth_attention_reason(self, agent_tool: AgentTool) -> str:
        """Explain a manual/unresolved renewal state without provider details."""
        sensitive_config = agent_tool.sensitive_config or {}
        if not sensitive_config.get("refresh_token"):
            return (
                "This connection has no automatic renewal permission. "
                "Reconnect the tool to grant a new permission."
            )

        auth_config = agent_tool.tool.auth_config
        if not auth_config:
            return (
                "The tool does not have the information required for automatic "
                "renewal. Reconnect the tool or contact a platform administrator."
            )

        if self._auth_config_value(auth_config, "auto_refresh_supported") is False:
            return (
                "This provider requires manual reconnection when its permission "
                "expires."
            )

        refresh_mode = str(
            self._auth_config_value(auth_config, "oauth_refresh_mode", "") or ""
        ).lower()
        if refresh_mode in {"manual", "none"}:
            return "This provider requires manual reconnection when its permission expires."

        if not (
            self._auth_config_value(auth_config, "token_url")
            or sensitive_config.get("oauth_token_url")
        ):
            return (
                "The provider has not supplied a usable renewal address. "
                "Reconnect the tool or contact a platform administrator."
            )

        return (
            "Automatic renewal is unavailable for this connection. "
            "Reconnect the tool to restore access."
        )

    def _resolve_oauth_config(
        self,
        agent_tool: AgentTool,
    ) -> Optional[OAuthRefreshRequest]:
        """Resolve the complete OAuth refresh request for an agent tool.

        Native tools may use the centralized provider registry, while MCP and
        other dynamically registered tools may provide their own OAuth client
        metadata. The distinction is made from the stored tool metadata, not
        from a hardcoded vendor allow-list. This lets a new OAuth integration
        work without a code deployment as long as its authorization metadata
        contains the standard OAuth token endpoint and client credentials.

        Args:
            agent_tool: The agent tool whose OAuth config to resolve.

        Returns:
            An OAuthRefreshRequest, or ``None`` when the tool cannot be
            refreshed because required metadata or credentials are missing.

        Notes:
            - Registered native providers retain their existing provider
              manager behavior, including provider-specific parameters.
            - Unknown providers fall back to standard OAuth metadata when the
              tool stores ``client_id`` and a token endpoint.
            - MCP clients support public clients, ``client_secret_post``, and
              ``client_secret_basic`` token endpoint authentication.
        """
        sensitive_config = agent_tool.sensitive_config or {}
        refresh_token = sensitive_config.get("refresh_token")
        if not refresh_token:
            logger.warning(
                f"No refresh_token available for tool {agent_tool.tool.name}. "
                "User will need to re-authenticate."
            )
            return None

        auth_config = agent_tool.tool.auth_config
        if not auth_config:
            logger.error(f"No auth_config for tool {agent_tool.tool.name}")
            return None

        oauth_manager = get_oauth_manager()
        provider, token_url = oauth_manager.extract_oauth_config(auth_config)
        # A discovered MCP authorization server may not have been present in
        # the authored platform metadata. The callback stores the resolved
        # endpoint in the encrypted connection state as a defense-in-depth
        # fallback; new flows also persist it to auth_config.
        token_url = token_url or sensitive_config.get("oauth_token_url")
        if not token_url:
            logger.error(f"No token_url in auth_config for tool {agent_tool.tool.name}")
            return None
        valid_token_url, token_url_reason = validate_oauth_endpoint_url(str(token_url))
        if not valid_token_url:
            logger.error(
                "Invalid OAuth token endpoint for tool %s: %s",
                agent_tool.tool.name,
                token_url_reason,
            )
            return None

        if isinstance(auth_config, dict):
            refresh_metadata_config = dict(auth_config)
        elif hasattr(auth_config, "model_dump"):
            refresh_metadata_config = auth_config.model_dump()
        else:
            refresh_metadata_config = {}
        refresh_metadata_config.setdefault("token_url", str(token_url))
        if sensitive_config.get("oauth_token_endpoint_auth_method"):
            refresh_metadata_config.setdefault(
                "token_endpoint_auth_method",
                sensitive_config["oauth_token_endpoint_auth_method"],
            )
        refresh_metadata = get_oauth_refresh_metadata(refresh_metadata_config)
        if refresh_metadata.mode is OAuthRefreshMode.MANUAL:
            logger.info(
                "Skipping refresh for %s because OAuth metadata declares manual "
                "reauthorization",
                agent_tool.tool.name,
            )
            return None

        tool_source = getattr(agent_tool.tool, "tool_source", None)
        is_mcp_tool = getattr(tool_source, "value", tool_source) == ToolSource.MCP.value
        configured_provider = self._auth_config_value(auth_config, "provider")
        provider_name = str(provider or "").lower()
        oauth_mode = str(
            self._auth_config_value(auth_config, "oauth_mode", "") or ""
        ).lower()
        explicit_generic_mode = bool(
            self._auth_config_value(auth_config, "mcp_oauth", False)
        )
        use_generic_refresh = (
            provider_name
            in {
                "mcp",
                "mcp_oauth",
                "mcp-oauth",
            }
            or explicit_generic_mode
            or oauth_mode
            in {
                "generic",
                "mcp",
                "mcp_oauth",
                "mcp-oauth",
            }
        )

        # A missing provider is common in MCP authorization-server metadata.
        # In that case extract_oauth_config may return its legacy default
        # provider, but the source and endpoint metadata still identify this
        # as a generic MCP OAuth flow.
        use_generic_refresh = use_generic_refresh or (
            is_mcp_tool and not configured_provider
        )

        provider_credentials = None
        try:
            provider_credentials = oauth_manager.get_credentials(provider_name)
        except ValueError:
            # The provider registry is intentionally limited to native
            # integrations. An unknown provider is still refreshable when its
            # OAuth metadata contains a client_id; this is the key path for
            # vendor-labeled MCP servers and future native integrations.
            logger.info(
                "Provider %s is not in the native OAuth registry for tool %s; "
                "using tool metadata when available",
                provider_name or "<missing>",
                agent_tool.tool.name,
            )
            use_generic_refresh = True

        # A registered provider can still be missing deployment credentials
        # (for example, a newly enabled tenant environment). If the tool row
        # has a complete client_id, prefer that metadata over constructing a
        # request containing a null environment-backed client.
        if (
            not use_generic_refresh
            and not getattr(provider_credentials, "client_id", None)
            and self._auth_config_value(auth_config, "client_id")
        ):
            use_generic_refresh = True

        stored_client_secret = getattr(
            agent_tool.tool, "oauth_client_secret_encrypted", None
        )
        explicit_client_metadata = bool(
            self._auth_config_value(auth_config, "token_endpoint_auth_method")
            or self._auth_config_value(auth_config, "client_auth_method")
        )
        if not use_generic_refresh and (
            isinstance(stored_client_secret, str)
            and bool(stored_client_secret)
            or explicit_client_metadata
        ):
            # A platform row can override the deployment-wide native client.
            # Use the standards-based builder so the encrypted per-tool secret
            # is actually selected instead of silently using an environment
            # secret for the wrong OAuth client.
            use_generic_refresh = True

        if not use_generic_refresh and not getattr(
            provider_credentials, "client_id", None
        ):
            logger.error(
                "Native OAuth client_id is not configured for tool %s",
                agent_tool.tool.name,
            )
            return None

        if use_generic_refresh:
            return self._build_generic_refresh_request(
                agent_tool=agent_tool,
                auth_config=auth_config,
                sensitive_config=sensitive_config,
                refresh_token=refresh_token,
                token_url=token_url,
                provider_credentials=provider_credentials,
            )

        try:
            oauth_data = oauth_manager.get_auth_data(
                provider=provider_name,
                flow="refresh",
                refresh_token=refresh_token,
            )
        except (TypeError, ValueError) as e:
            logger.error(
                "Unable to build native OAuth refresh request for tool %s (%s)",
                agent_tool.tool.name,
                type(e).__name__,
            )
            return None

        return OAuthRefreshRequest(data=oauth_data, token_url=token_url)

    @staticmethod
    def _auth_config_value(auth_config: Any, key: str, default: Any = None) -> Any:
        """Read one OAuth metadata value from a dict or Pydantic config.

        Args:
            auth_config: OAuth metadata represented as a mapping or model.
            key: Canonical field name to read.
            default: Value returned when the field is absent.

        Returns:
            The configured value, or ``default`` if it is not present.
        """
        if isinstance(auth_config, dict):
            return auth_config.get(key, default)
        return getattr(auth_config, key, default)

    def _build_generic_refresh_request(
        self,
        agent_tool: AgentTool,
        auth_config: Any,
        sensitive_config: Dict[str, Any],
        refresh_token: str,
        token_url: str,
        provider_credentials: Any = None,
    ) -> Optional[OAuthRefreshRequest]:
        """Build a standard OAuth refresh request from persisted metadata.

        Args:
            agent_tool: Tool whose persisted OAuth state is being refreshed.
            auth_config: Tool OAuth metadata, as a mapping or model.
            sensitive_config: Decrypted per-connection OAuth state.
            refresh_token: Current refresh token.
            token_url: OAuth token endpoint.
            provider_credentials: Optional credentials from the native
                provider registry, used as a fallback for explicit generic
                flows that still use a registered client.

        Returns:
            An OAuthRefreshRequest, or ``None`` when no client identifier is
            available or the requested token endpoint auth method is unknown.

        Notes:
            ``client_secret_basic`` is sent in the Authorization header;
            ``client_secret_post`` is sent as form data. Public clients send
            only ``client_id``. The refresh token and client credentials are
            never logged.
        """
        tool_source = getattr(agent_tool.tool, "tool_source", None)
        source_value = getattr(tool_source, "value", tool_source)
        is_mcp_tool = source_value == ToolSource.MCP.value

        client_id = (
            sensitive_config.get("oauth_client_id")
            or self._auth_config_value(auth_config, "client_id")
            or getattr(provider_credentials, "client_id", None)
            or (os.getenv("MCP_OAUTH_CLIENT_ID") if is_mcp_tool else None)
        )
        encrypted_client_secret = getattr(
            agent_tool.tool, "oauth_client_secret_encrypted", None
        )
        stored_client_secret = None
        if isinstance(encrypted_client_secret, str) and encrypted_client_secret:
            decrypted_secret = decrypt_data(encrypted_client_secret)
            if isinstance(decrypted_secret, dict):
                stored_client_secret = decrypted_secret.get("client_secret")
        client_secret = (
            sensitive_config.get("oauth_client_secret")
            or stored_client_secret
            or getattr(provider_credentials, "client_secret", None)
            or (os.getenv("MCP_OAUTH_CLIENT_SECRET") if is_mcp_tool else None)
            # Backward compatibility for rows created before encrypted client
            # secret storage. New writes strip this field from auth_config.
            or self._auth_config_value(auth_config, "client_secret")
        )
        if not client_id:
            logger.error(
                "No OAuth client_id available for tool %s; cannot refresh",
                agent_tool.tool.name,
            )
            return None

        oauth_data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        resource = (
            sensitive_config.get("resource")
            or self._auth_config_value(auth_config, "resource")
            or (
                getattr(agent_tool.tool, "mcp_server_url", None)
                if is_mcp_tool
                else None
            )
        )
        if resource:
            oauth_data["resource"] = str(resource)

        auth_method = (
            get_oauth_client_auth_method(auth_config)
            or str(
                sensitive_config.get("oauth_token_endpoint_auth_method", "") or ""
            ).lower()
        )
        headers: Dict[str, str] = {}
        if auth_method in {"client_secret_basic", "basic"}:
            if not client_secret:
                logger.error(
                    "OAuth token endpoint requires client_secret_basic for tool %s",
                    agent_tool.tool.name,
                )
                return None
            encoded_credentials = base64.b64encode(
                f"{client_id}:{client_secret}".encode()
            ).decode()
            headers["Authorization"] = f"Basic {encoded_credentials}"
        elif auth_method in {"none", "public"}:
            oauth_data["client_id"] = str(client_id)
        elif auth_method in {"client_secret_post", "post", ""}:
            oauth_data["client_id"] = str(client_id)
            if client_secret:
                oauth_data["client_secret"] = str(client_secret)
        else:
            logger.error(
                "Unsupported OAuth token endpoint auth method %s for tool %s",
                auth_method,
                agent_tool.tool.name,
            )
            return None

        return OAuthRefreshRequest(
            data=oauth_data,
            token_url=token_url,
            headers=headers,
        )

    async def _perform_token_refresh(
        self,
        agent_tool: AgentTool,
        oauth_data: Dict[str, str],
        token_url: str,
        headers: Optional[Dict[str, str]] = None,
    ) -> bool:
        """Acquire the lease, refresh the token, persist it, and release the lease.

        This is the core "do the work" method — everything that follows the
        expiry check and config resolution.

        Args:
            agent_tool: The agent tool to refresh.
            oauth_data: OAuth refresh request payload.
            token_url: The OAuth provider's token endpoint.
            headers: Optional token endpoint headers, such as HTTP Basic
                client authentication.

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
            self._perform_outcomes[agent_tool.id] = OAuthPerformOutcome.LOCK_UNAVAILABLE
            return False

        try:
            new_tokens = await self._refresh_oauth_token(
                token_url=token_url,
                oauth_data=oauth_data,
                headers=headers,
            )
            if not new_tokens or not new_tokens.get("access_token"):
                logger.error(f"Failed to refresh token for tool {tool_name}")
                self._perform_outcomes[agent_tool.id] = OAuthPerformOutcome.FAILED
                return False

            sensitive_config = dict(agent_tool.sensitive_config or {})
            sensitive_config["access_token"] = new_tokens["access_token"]
            expires_in = new_tokens.get("expires_in")
            try:
                expires_in_seconds = float(expires_in)
                if expires_in_seconds <= 0 or not math.isfinite(expires_in_seconds):
                    raise ValueError("expires_in must be positive")
            except (TypeError, ValueError):
                # OAuth 2.0 makes expires_in optional. Keep the connection
                # refreshable when a provider omits it by using a conservative
                # default rather than leaving the old expiry in the past.
                expires_in_seconds = DEFAULT_ACCESS_TOKEN_LIFETIME_SECONDS
                logger.warning(
                    "OAuth provider omitted a usable expires_in for tool %s; "
                    "defaulting to %s seconds",
                    tool_name,
                    DEFAULT_ACCESS_TOKEN_LIFETIME_SECONDS,
                )
            sensitive_config["expires_at"] = (
                datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)
            ).timestamp()
            new_refresh_token = new_tokens.get("refresh_token")
            if isinstance(new_refresh_token, str) and new_refresh_token.strip():
                sensitive_config["refresh_token"] = new_refresh_token
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
                self._perform_outcomes[agent_tool.id] = OAuthPerformOutcome.FAILED
                return False

            self._perform_outcomes[agent_tool.id] = OAuthPerformOutcome.SUCCEEDED
            return True
        finally:
            await self.tool_service.release_refresh_lock(agent_tool.id, claim_id)

    async def _refresh_oauth_token(
        self,
        token_url: str,
        oauth_data: Dict[str, str],
        headers: Optional[Dict[str, str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Refresh OAuth token using refresh_token (provider-agnostic).

        This method implements standard OAuth 2.0 token refresh flow and works
        with any OAuth 2.0 provider (Google, Microsoft, GitHub, etc.)
        as long as the provider follows the OAuth 2.0 specification.

        Args:
            token_url: OAuth provider's token endpoint (from tool's AuthConfig)
            oauth_data: OAuth data dictionary for token refresh (created by centralized utility)
            headers: Optional token endpoint headers, such as HTTP Basic client
                authentication.

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
        request_kwargs: Dict[str, Any] = {"data": oauth_data}
        if headers:
            request_kwargs["headers"] = headers

        valid, reason = validate_oauth_endpoint_url(token_url, resolve_dns=True)
        if not valid:
            logger.error("Refusing OAuth refresh to invalid endpoint: %s", reason)
            return None

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(30.0), follow_redirects=False
        ) as client:
            for attempt in range(TOKEN_REFRESH_HTTP_MAX_RETRIES):
                try:
                    response = await client.post(token_url, **request_kwargs)
                except httpx.HTTPError as e:
                    if attempt < TOKEN_REFRESH_HTTP_MAX_RETRIES - 1:
                        delay = 2**attempt
                        logger.warning(
                            "Transient OAuth refresh transport failure; retrying "
                            "in %s seconds (%s)",
                            delay,
                            type(e).__name__,
                        )
                        await asyncio.sleep(delay)
                        continue
                    logger.error(
                        "OAuth refresh transport failed (%s)", type(e).__name__
                    )
                    return None

                if response.status_code == 200:
                    try:
                        payload = response.json()
                    except ValueError as e:
                        logger.error(
                            "OAuth refresh returned invalid JSON (%s)",
                            type(e).__name__,
                        )
                        return None
                    if not isinstance(payload, dict):
                        logger.error("OAuth refresh returned a non-object response")
                        return None
                    return payload

                is_transient = (
                    response.status_code == 429 or response.status_code >= 500
                )
                if is_transient and attempt < TOKEN_REFRESH_HTTP_MAX_RETRIES - 1:
                    delay = 2**attempt
                    logger.warning(
                        "Transient OAuth refresh failure (status %s); retrying "
                        "in %s seconds",
                        response.status_code,
                        delay,
                    )
                    await asyncio.sleep(delay)
                    continue

                logger.error(
                    "OAuth refresh failed with provider status %s",
                    response.status_code,
                )
                return None

        return None

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
            logger.error("Failed to persist refreshed token for %s", tool_name)
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
