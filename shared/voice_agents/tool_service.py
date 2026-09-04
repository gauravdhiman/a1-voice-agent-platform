"""
Tool service for managing platform tools and agent-specific tool configurations.
"""

import logging
import time
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from opentelemetry import trace

from shared.common.security import decrypt_data, encrypt_data
from shared.config import supabase_config
from shared.voice_agents.tool_health import check_tool_configuration
from shared.voice_agents.tools.base.oauth_support import (
    extract_oauth_client_secret,
    get_oauth_refresh_metadata,
    sanitize_oauth_config,
)
from shared.voice_agents.tools.mcp.security import is_sensitive_mcp_header
from supabase import Client

from .tool_models import (
    AgentTool,
    AgentToolCreate,
    AgentToolResponse,
    AgentToolUpdate,
    AuthStatus,
    ConnectionStatus,
    PlatformTool,
    PlatformToolCreate,
    ToolSource,
)

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


def _is_ssl_error(error: Exception) -> bool:
    """Check if error is an SSL connection error."""
    error_str = str(error).lower()
    ssl_indicators = [
        "ssl",
        "unexpected_eof",
        "eof occurred",
        "tls",
        "handshake",
        "connection reset",
        "broken pipe",
    ]
    return any(indicator in error_str for indicator in ssl_indicators)


def _with_retry(max_retries: int = 3, delay: float = 0.5):
    """Decorator to add retry logic for SSL/connection errors.

    Args:
        max_retries: Maximum number of retry attempts
        delay: Delay between retries in seconds
    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if _is_ssl_error(e) and attempt < max_retries - 1:
                        logger.warning(
                            f"SSL connection error in {func.__name__}, "
                            f"retrying ({attempt + 1}/{max_retries})..."
                        )
                        # Reset Supabase client to get fresh connection
                        supabase_config.reset_client()
                        time.sleep(delay * (attempt + 1))  # Exponential backoff
                        continue
                    raise
            raise last_error

        return wrapper

    return decorator


def validate_token_status(
    sensitive_config: Optional[str], auth_type: Optional[str] = "oauth2"
) -> AuthStatus:
    """
    Validate authentication token status from encrypted sensitive config.

    Args:
        sensitive_config: Encrypted JSON string containing auth credentials
        auth_type: Authentication type ("oauth2", "api_key", etc.)

    Returns:
        AuthStatus enum indicating the authentication state
    """
    if not sensitive_config:
        return AuthStatus.NOT_AUTHENTICATED

    try:
        decrypted_data = decrypt_data(sensitive_config)
        if not decrypted_data or not isinstance(decrypted_data, dict):
            return AuthStatus.NOT_AUTHENTICATED

        # OAuth token validation
        if auth_type == "oauth2":
            access_token = decrypted_data.get("access_token")
            expires_at = decrypted_data.get("expires_at")

            if not access_token or not expires_at:
                return AuthStatus.NOT_AUTHENTICATED

            # Check if token is still valid (with 5 min buffer)
            current_time = datetime.now().timestamp()
            if current_time >= (expires_at - 300):  # 5 minutes buffer
                return AuthStatus.EXPIRED

            return AuthStatus.AUTHENTICATED

        # API key validation (simple presence check)
        elif auth_type == "api_key":
            api_key = decrypted_data.get("api_key")
            return AuthStatus.AUTHENTICATED if api_key else AuthStatus.NOT_AUTHENTICATED

        else:
            # Unknown auth type - check if any credential exists
            if any(decrypted_data.values()):
                return AuthStatus.AUTHENTICATED
            return AuthStatus.NOT_AUTHENTICATED

    except Exception as e:
        logger.error("Error validating token status (%s)", type(e).__name__)
        return AuthStatus.NOT_AUTHENTICATED


def get_connection_status(
    requires_auth: bool, auth_status: AuthStatus
) -> ConnectionStatus:
    """
    Calculate connection status based on auth requirements and status.

    Args:
        requires_auth: Whether the tool requires authentication
        auth_status: Current authentication status of the tool

    Returns:
        ConnectionStatus enum indicating the connection state
    """
    if not requires_auth:
        return ConnectionStatus.CONNECTED_NO_AUTH

    if auth_status == AuthStatus.AUTHENTICATED:
        return ConnectionStatus.CONNECTED_AUTH_VALID

    return ConnectionStatus.CONNECTED_AUTH_INVALID


def _oauth_response_metadata(
    auth_type: Optional[str],
    auth_config: object,
    encrypted_sensitive_config: Optional[str],
) -> dict[str, object]:
    """Build safe refresh guidance for an agent-tool API response.

    The encrypted connection is inspected only to determine whether a refresh
    token exists. No token value is returned. A connected token without a
    refresh grant is explicitly reported as manual reauthorization so admins
    do not mistake a green access-token status for a persistent connection.
    """
    if auth_type != "oauth2":
        return {
            "oauth_refresh_mode": None,
            "oauth_refresh_interval_minutes": None,
            "oauth_refresh_message": None,
        }

    safe_config = sanitize_oauth_config(auth_config or {})
    has_refresh_token: Optional[bool] = None
    if encrypted_sensitive_config:
        decrypted = decrypt_data(encrypted_sensitive_config)
        if isinstance(decrypted, dict):
            has_refresh_token = bool(decrypted.get("refresh_token"))
            if not safe_config.get("token_url") and decrypted.get("oauth_token_url"):
                safe_config["token_url"] = decrypted["oauth_token_url"]
            if decrypted.get("oauth_token_endpoint_auth_method"):
                safe_config["token_endpoint_auth_method"] = decrypted[
                    "oauth_token_endpoint_auth_method"
                ]
    metadata = get_oauth_refresh_metadata(
        safe_config,
        has_refresh_token=has_refresh_token,
    )
    return {
        "oauth_refresh_mode": metadata.mode,
        "oauth_refresh_interval_minutes": metadata.manual_reauth_interval_minutes,
        "oauth_refresh_message": metadata.message,
    }


def _token_expiry(encrypted_sensitive_config: Optional[str]) -> Optional[float]:
    """Extract a numeric token expiry without exposing the encrypted payload."""
    if not encrypted_sensitive_config:
        return None
    decrypted = decrypt_data(encrypted_sensitive_config)
    if not isinstance(decrypted, dict):
        return None
    try:
        return float(decrypted["expires_at"])
    except (KeyError, TypeError, ValueError):
        return None


class ToolService:
    """Service for handling platform tools and agent tool configurations."""

    def __init__(self) -> None:
        self.supabase_config = supabase_config

    @property
    def supabase(self) -> Optional[Client]:
        """Get Supabase client."""
        return self.supabase_config.client

    # ═══════════════════════════════════════════════════════════════════════════════
    # Token-refresh distributed lock (Postgres-backed lease)
    # ═══════════════════════════════════════════════════════════════════════════════
    # Prevents multiple backend instances from refreshing the same OAuth token at
    # once (which races: providers rotate refresh tokens, concurrent refreshes
    # invalidate each other and the last DB write wins with a stale token). The lock
    # is a per-agent_tool lease with a TTL, implemented by the `claim_token_refresh`
    # / `release_token_refresh` Postgres functions (see Alembic migration
    # 20260623000001). Fail-closed: if the lock cannot be acquired/verified, refresh
    # is skipped rather than racing.
    REFRESH_LOCK_LEASE_SECONDS: int = 120

    @tracer.start_as_current_span("tool.claim_refresh_lock")
    async def claim_refresh_lock(
        self,
        agent_tool_id: UUID,
        lease_seconds: int = REFRESH_LOCK_LEASE_SECONDS,
    ) -> Optional[str]:
        """Atomically claim a per-agent_tool refresh lease.

        Args:
            agent_tool_id: The agent tool whose token we want to refresh.
            lease_seconds: Lease TTL; a crashed holder's lease auto-expires so
                refresh is not blocked forever.

        Returns:
            A claim id (str) if this caller acquired the lease, else ``None``
            (another instance holds it, or the lock could not be verified —
            fail-closed). The same claim id must be passed to
            :meth:`release_refresh_lock`.
        """
        claim_id = str(uuid4())
        try:
            response = self.supabase.rpc(
                "claim_token_refresh",
                {
                    "p_tool_id": str(agent_tool_id),
                    "p_claim": claim_id,
                    "p_lease_seconds": lease_seconds,
                },
            ).execute()
            data = getattr(response, "data", None)
            if isinstance(data, dict):
                return claim_id if data.get("claimed") else None
            # Defensive fallback for scalar returns.
            return claim_id if data else None
        except Exception as e:
            logger.error(
                f"Error claiming refresh lock for {agent_tool_id}: {e}",
                exc_info=True,
            )
            return None  # fail-closed: do not refresh if the lock is unverifiable

    @tracer.start_as_current_span("tool.release_refresh_lock")
    async def release_refresh_lock(
        self,
        agent_tool_id: UUID,
        claim_id: str,
    ) -> bool:
        """Release a refresh lease, only if it still belongs to this caller.

        Args:
            agent_tool_id: The agent tool whose lease to release.
            claim_id: The claim id returned by :meth:`claim_refresh_lock`.

        Returns:
            True if this caller's lease was released, False otherwise (e.g. it
            had already expired and been re-acquired by another instance).
        """
        try:
            response = self.supabase.rpc(
                "release_token_refresh",
                {"p_tool_id": str(agent_tool_id), "p_claim": claim_id},
            ).execute()
            data = getattr(response, "data", None)
            if isinstance(data, dict):
                return bool(data.get("released"))
            return bool(data)
        except Exception as e:
            logger.error(
                f"Error releasing refresh lock for {agent_tool_id}: {e}",
                exc_info=True,
            )
            return False

    # Platform Tools
    @tracer.start_as_current_span("tool.upsert_platform_tool")
    @_with_retry(max_retries=3)
    async def upsert_platform_tool(
        self, tool_data: PlatformToolCreate
    ) -> tuple[Optional[PlatformTool], Optional[str]]:
        """Upsert a platform tool by name.

        Encrypts ``mcp_secret_headers_input`` (plaintext from the UI) into the
        ``mcp_server_secret_headers`` column before persisting. The
        ``mcp_secret_headers_input`` field itself is ``exclude=True`` on the
        model so it is never written to the DB.
        """
        try:
            # Check if exists
            existing = (
                self.supabase.table("platform_tools")
                .select("*")
                .eq("name", tool_data.name)
                .execute()
            )

            # Dump model; mcp_secret_headers_input is exclude=True so it is not
            # in the dump. exclude_none keeps NULL organization_id out of the
            # write so global rows stay global. ``mode="json"`` serializes
            # UUIDs and datetimes to strings — postgrest JSON-encodes the dict,
            # so a raw UUID object would raise
            # "Object of type UUID is not JSON serializable".
            data_dict = tool_data.model_dump(exclude_none=True, mode="json")

            # Publish lifecycle (RFC §6.6): custom MCP servers are
            # platform-published = GLOBAL. Force organization_id off MCP rows
            # so a UI-created server can never become an org-scoped row (the
            # org-scoped custom tier is retired; the column is dormant).
            if tool_data.tool_source is ToolSource.MCP:
                data_dict.pop("organization_id", None)
                # Cleared public headers arrive as None; persist as {} so an
                # upsert-by-name edit does not leave stale JSONB in place.
                data_dict["mcp_server_headers"] = tool_data.mcp_server_headers or {}
                if tool_data.auth_type != "oauth2":
                    # OAuth metadata must not survive a switch to no-auth or
                    # API-key mode and accidentally re-enable the OAuth route.
                    data_dict["auth_config"] = None
            # OAuth client secrets are credentials, not public authorization
            # metadata. Strip legacy/client-supplied secret keys from the JSONB
            # config and persist the write-only input in encrypted storage.
            if isinstance(data_dict.get("auth_config"), dict):
                data_dict["auth_config"] = sanitize_oauth_config(
                    data_dict["auth_config"]
                )

            # Legacy (code-backed) tools carry NO premium metadata in the
            # registry: ``PlatformToolRegistry.sync_with_db`` re-upserts them
            # without ``is_premium`` on every worker startup, which would
            # otherwise reset an admin-set premium flag to False. Preserve the
            # DB value on updates of existing LEGACY rows (inserts keep the
            # model default). Legacy tools are code-owned and must remain
            # published; the draft/publish lifecycle belongs to MCP rows.
            # MCP rows always send ``is_premium`` explicitly (author-form
            # checkbox), so they pass through unchanged.
            if tool_data.tool_source is ToolSource.LEGACY and existing.data:
                data_dict.pop("is_premium", None)
            if tool_data.tool_source is ToolSource.LEGACY:
                data_dict["is_published"] = True

            # Always write clearable fields on update so blanking them in the UI
            # is not a no-op (exclude_none would otherwise drop them).
            if existing.data:
                data_dict["description"] = tool_data.description
                data_dict["auth_type"] = tool_data.auth_type
                data_dict["requires_auth"] = tool_data.requires_auth

            if tool_data.mcp_secret_headers_input:
                data_dict["mcp_server_secret_headers"] = encrypt_data(
                    tool_data.mcp_secret_headers_input
                )
            elif tool_data.auth_type == "oauth2" or tool_data.requires_auth is False:
                # Switching to OAuth or "No auth" clears stored API-key headers
                # so a later discover/runtime session does not send stale
                # credentials alongside the new auth mode.
                data_dict["mcp_server_secret_headers"] = None
            if tool_data.oauth_client_secret_input:
                data_dict["oauth_client_secret_encrypted"] = encrypt_data(
                    {"client_secret": tool_data.oauth_client_secret_input}
                )
            elif tool_data.auth_type != "oauth2":
                data_dict["oauth_client_secret_encrypted"] = None

            if existing.data:
                response = (
                    self.supabase.table("platform_tools")
                    .update(data_dict)
                    .eq("id", existing.data[0]["id"])
                    .execute()
                )
            else:
                response = (
                    self.supabase.table("platform_tools").insert(data_dict).execute()
                )

            if not response.data:
                return None, "Failed to upsert platform tool"
            return (
                self._platform_tool_for_response(PlatformTool(**response.data[0])),
                None,
            )
        except Exception as e:
            logger.error(f"Error upserting platform tool: {e}")
            return None, str(e)

    @staticmethod
    def _platform_tool_for_response(tool: PlatformTool) -> PlatformTool:
        """Strip the encrypted secret-headers blob before returning to the API.

        The frontend gets only a ``mcp_secret_headers_configured`` flag, never
        the encrypted (or decrypted) blob. The worker path
        (``get_agent_tools_with_sensitive_config``) constructs
        ``PlatformTool`` directly from DB rows WITHOUT this stripping, so it
        retains the encrypted blob for the dispatch layer to decrypt.
        """
        tool.mcp_secret_headers_configured = bool(tool.mcp_server_secret_headers)
        tool.oauth_client_secret_configured = bool(tool.oauth_client_secret_encrypted)
        if tool.auth_type == "oauth2":
            safe_auth_config = sanitize_oauth_config(tool.auth_config or {})
            metadata = get_oauth_refresh_metadata(safe_auth_config)
            tool.auth_config = safe_auth_config
            tool.oauth_refresh_mode = metadata.mode
            tool.oauth_refresh_interval_minutes = (
                metadata.manual_reauth_interval_minutes
            )
            tool.oauth_refresh_message = metadata.message
        else:
            tool.auth_config = (
                sanitize_oauth_config(tool.auth_config or {})
                if tool.auth_config
                else tool.auth_config
            )
            tool.oauth_refresh_mode = None
            tool.oauth_refresh_interval_minutes = None
            tool.oauth_refresh_message = None
        tool.mcp_server_headers = {
            str(key): str(value)
            for key, value in (tool.mcp_server_headers or {}).items()
            if not is_sensitive_mcp_header(str(key))
        }
        tool.mcp_server_secret_headers = None
        tool.oauth_client_secret_encrypted = None
        return tool

    @tracer.start_as_current_span("tool.get_platform_tools")
    async def get_platform_tools(
        self,
        only_active: bool = True,
        include_drafts: bool = False,
    ) -> tuple[List[PlatformTool], Optional[str]]:
        """Get platform tools, filtered by the publish lifecycle.

        Publish lifecycle (RFC §6.6): a custom MCP server is authored by a
        platform admin as a **draft** (``is_published=False``), then
        **published** to the global catalog (``is_published=True``). Org users
        see only published rows (combined with ``is_active``); platform admins
        see drafts too.

        Args:
            only_active: Filter to ``is_active=True`` rows.
            include_drafts: When False (default — org-user listing), filter to
                ``is_published=True``. When True, return drafts + published
                (platform-admin management / internal lookups-by-id). The route
                layer enforces that only platform admins may pass True.

        Returns:
            Tuple of (platform tools, error). Secret-header blobs are stripped
            from each tool before return.
        """
        try:
            query = self.supabase.table("platform_tools").select("*")
            if only_active:
                query = query.eq("is_active", True)
            if not include_drafts:
                query = query.eq("is_published", True)
            response = query.execute()
            tools = [
                self._platform_tool_for_response(PlatformTool(**item))
                for item in response.data
            ]
            return tools, None
        except Exception as e:
            logger.error(f"Error getting platform tools: {e}")
            return [], str(e)

    @tracer.start_as_current_span("tool.get_platform_tool_by_id")
    async def get_platform_tool_by_id(
        self, tool_id: UUID
    ) -> tuple[Optional[PlatformTool], Optional[str]]:
        """Fetch a single platform tool row by id.

        Used for attach-time checks (e.g. premium gating) without loading the
        full catalog.

        Args:
            tool_id: ``platform_tools.id``.

        Returns:
            Tuple of (platform tool, error). ``(None, "not found")`` when the
            row does not exist.
        """
        try:
            response = (
                self.supabase.table("platform_tools")
                .select("*")
                .eq("id", str(tool_id))
                .limit(1)
                .execute()
            )
            if not response.data:
                return None, "Platform tool not found"
            return (
                self._platform_tool_for_response(PlatformTool(**response.data[0])),
                None,
            )
        except Exception as e:
            logger.error(f"Error getting platform tool {tool_id}: {e}")
            return None, str(e)

    @tracer.start_as_current_span("tool.get_platform_tool_oauth_client_secret")
    async def get_platform_tool_oauth_client_secret(
        self, tool_name: str
    ) -> tuple[Optional[str], Optional[str]]:
        """Load one platform OAuth client secret for an internal token exchange.

        The secret is stored as Fernet-encrypted JSON in
        ``platform_tools.oauth_client_secret_encrypted``. This method is
        intentionally narrow: it returns only the decrypted secret to the
        backend OAuth route and never exposes it through a platform-tool model
        or API response.

        Args:
            tool_name: Platform tool name whose confidential OAuth client is
                being used.

        Returns:
            ``(secret, error)``. A missing secret is ``(None, None)``; a
            database/decryption failure returns an error string.
        """
        try:
            response = (
                self.supabase.table("platform_tools")
                .select("oauth_client_secret_encrypted")
                .eq("name", tool_name)
                .limit(1)
                .execute()
            )
            if not response.data:
                return None, "Platform tool not found"
            encrypted = response.data[0].get("oauth_client_secret_encrypted")
            if not encrypted:
                return None, None
            decrypted = decrypt_data(encrypted)
            secret = (
                decrypted.get("client_secret") if isinstance(decrypted, dict) else None
            )
            if not isinstance(secret, str) or not secret:
                return None, "OAuth client secret could not be decrypted"
            return secret, None
        except Exception as exc:
            logger.error(
                "Error loading OAuth client secret for platform tool %s: %s",
                tool_name,
                type(exc).__name__,
            )
            return None, "Could not load OAuth client secret"

    @tracer.start_as_current_span("tool.migrate_legacy_oauth_client_secrets")
    async def migrate_legacy_oauth_client_secrets(
        self,
    ) -> tuple[int, Optional[str]]:
        """Move legacy OAuth client secrets out of public tool metadata.

        Prior versions allowed a confidential OAuth client secret to be stored
        in ``platform_tools.auth_config``. That JSONB field is returned as
        administrative metadata and is therefore not an acceptable secret
        store. This startup-safe migration copies a legacy secret into the
        Fernet-encrypted ``oauth_client_secret_encrypted`` column when needed,
        then removes all known grant and credential fields from ``auth_config``.

        Args:
            None.

        Returns:
            A tuple containing the number of rows scrubbed and an optional
            error message. Rows already using encrypted storage are still
            scrubbed if stale credential keys remain in their metadata.

        Raises:
            No exception is intentionally propagated. Database or encryption
            failures are logged without credential material and returned to the
            caller so application startup can report the migration issue.

        Notes:
            The operation is idempotent. Running it on every backend startup
            is safe because a row with an encrypted secret is never encrypted
            again; only the public metadata cleanup is repeated when needed.
        """
        migrated = 0
        try:
            response = (
                self.supabase.table("platform_tools")
                .select("id,auth_type,auth_config,oauth_client_secret_encrypted")
                .eq("auth_type", "oauth2")
                .execute()
            )
            for row in response.data or []:
                raw_config = row.get("auth_config")
                if not isinstance(raw_config, dict):
                    continue

                sanitized_config = sanitize_oauth_config(raw_config)
                legacy_secret = extract_oauth_client_secret(raw_config)
                update_data: dict[str, object] = {}
                if sanitized_config != raw_config:
                    update_data["auth_config"] = sanitized_config
                if legacy_secret and not row.get("oauth_client_secret_encrypted"):
                    update_data["oauth_client_secret_encrypted"] = encrypt_data(
                        {"client_secret": legacy_secret}
                    )
                if not update_data:
                    continue

                (
                    self.supabase.table("platform_tools")
                    .update(update_data)
                    .eq("id", str(row["id"]))
                    .execute()
                )
                migrated += 1
            return migrated, None
        except Exception as exc:
            logger.error(
                "OAuth client-secret migration failed after %s rows (%s)",
                migrated,
                type(exc).__name__,
            )
            return migrated, "Could not migrate legacy OAuth client secrets"

    @tracer.start_as_current_span("tool.update_platform_tool_oauth_metadata")
    async def update_platform_tool_oauth_metadata(
        self,
        tool_id: UUID,
        oauth_metadata: dict,
    ) -> tuple[bool, Optional[str]]:
        """Persist discovered OAuth metadata without persisting credentials.

        MCP authorization-server discovery can fill in the token endpoint,
        public client id, token-endpoint authentication method, and refresh
        grant capability after a platform tool was authored. Those values must
        survive the initial OAuth redirect so the background refresh worker
        can resolve the same request on a later run. This method is deliberately
        narrower than ``update_platform_tool``: it writes only sanitized
        ``auth_config`` metadata and has no path for plaintext credentials.

        Args:
            tool_id: The ``platform_tools.id`` row to update.
            oauth_metadata: Provider metadata returned by MCP discovery. Known
                credential and grant-artifact fields are removed recursively
                before the database write.

        Returns:
            ``(True, None)`` after a successful update, otherwise ``(False,
            error_message)``. Error messages are safe for API logs and do not
            include the submitted metadata.
        """
        try:
            sanitized_metadata = sanitize_oauth_config(oauth_metadata)
            response = (
                self.supabase.table("platform_tools")
                .update({"auth_config": sanitized_metadata})
                .eq("id", str(tool_id))
                .execute()
            )
            if not response.data:
                return False, "Platform tool not found or OAuth metadata was not saved"
            return True, None
        except Exception as exc:
            logger.error(
                "Error persisting discovered OAuth metadata for tool %s (%s)",
                tool_id,
                type(exc).__name__,
            )
            return False, "Could not persist discovered OAuth metadata"

    @tracer.start_as_current_span("tool.merge_stored_mcp_secret_headers")
    async def merge_stored_mcp_secret_headers(
        self,
        tool_id: UUID,
        probe_headers: dict[str, str],
        *,
        test_api_key: Optional[str] = None,
    ) -> tuple[dict[str, str], Optional[str]]:
        """Merge encrypted stored secret headers into an in-memory MCP probe.

        Used by ``POST /tools/mcp/discover`` when a platform admin re-tests an
        existing tool without re-pasting secrets. Request headers win on key
        conflicts so typed overrides still work. ``{{KEY}}`` placeholders in
        stored values are filled from ``test_api_key``; if a placeholder remains
        and no test key was provided, returns a clear 400-style error so the UI
        can prompt for the transient Test API key.

        Args:
            tool_id: ``platform_tools`` row to load secrets from.
            probe_headers: Headers already resolved by the UI (public + any
                typed secret overrides for this probe).
            test_api_key: Optional transient key for ``{{KEY}}`` substitution.
                Never persisted.

        Returns:
            Tuple of ``(merged_headers, error)``. ``error`` is a user-facing
            message when the tool is missing or a ``{{KEY}}`` cannot be filled.
        """
        try:
            response = (
                self.supabase.table("platform_tools")
                .select("id, mcp_server_secret_headers")
                .eq("id", str(tool_id))
                .limit(1)
                .execute()
            )
            if not response.data:
                return probe_headers, "Platform tool not found"

            encrypted = response.data[0].get("mcp_server_secret_headers")
            if not encrypted:
                return dict(probe_headers), None

            try:
                secret_headers = decrypt_data(encrypted)
            except Exception as e:
                logger.error(
                    "Failed to decrypt mcp_server_secret_headers for discover "
                    "probe on tool %s (%s)",
                    tool_id,
                    type(e).__name__,
                )
                return (
                    probe_headers,
                    "Could not decrypt stored secret headers for this tool.",
                )

            if not isinstance(secret_headers, dict):
                return dict(probe_headers), None

            merged = dict(probe_headers)
            needs_test_key = False
            for key, raw_value in secret_headers.items():
                header_key = str(key)
                # Typed overrides from the form win over stored values.
                if any(k.lower() == header_key.lower() for k in merged):
                    continue
                value = str(raw_value)
                if "{{KEY}}" in value:
                    if test_api_key:
                        merged[header_key] = value.replace("{{KEY}}", str(test_api_key))
                    else:
                        needs_test_key = True
                else:
                    merged[header_key] = value

            if needs_test_key:
                return (
                    probe_headers,
                    "Stored secret headers use {{KEY}}. Enter a Test API key "
                    "to substitute it for this probe (it is never saved).",
                )
            return merged, None
        except Exception as e:
            logger.error(
                "Error merging stored MCP secret headers for %s (%s)",
                tool_id,
                type(e).__name__,
            )
            return probe_headers, "Could not merge stored secret headers"

    @tracer.start_as_current_span("tool.publish_platform_tool")
    async def publish_platform_tool(
        self, tool_id: UUID, published: bool
    ) -> tuple[Optional[PlatformTool], Optional[str]]:
        """Flip a platform tool's ``is_published`` state (publish/unpublish).

        Publish-lifecycle write (RFC §6.6): the route gates this on
        ``platform_admin``. Unpublishing hides the server from new attaches
        (org users no longer see it in the catalog); existing ``agent_tools``
        attachments keep working (the worker reads them by join, not via this
        listing). ``is_active`` is untouched.

        When *publishing* an MCP row whose ``tool_functions_schema`` is still
        null, best-effort discover the server's tools live and backfill the
        column so the agent tool-config drawer can render the tool list with
        enable/disable toggles (parity with native tool cards). The authoring
        dialog already persists this at create time from its test-key
        discovery, so the backfill only fires for rows authored before that
        fix or published without discovering. Discovery failure is non-fatal:
        the row keeps its existing (null) schema and the publish still
        succeeds. Unpublish never triggers discovery.

        Args:
            tool_id: The ``platform_tools`` row id.
            published: True to publish, False to unpublish (revert to draft).

        Returns:
            Tuple of (updated PlatformTool, error). ``(None, "not found")`` if
            the row does not exist.
        """
        try:
            response = (
                self.supabase.table("platform_tools")
                .update({"is_published": published})
                .eq("id", str(tool_id))
                .execute()
            )
            if not response.data:
                return None, "Platform tool not found"
            row = response.data[0]

            # Best-effort backfill of the tool list when publishing an MCP row
            # that never had its tool_functions_schema populated.
            if (
                published
                and row.get("tool_source") == "mcp"
                and not row.get("tool_functions_schema")
                and row.get("mcp_server_url")
            ):
                schema = await self._discover_functions_schema(row)
                if schema:
                    backfill = (
                        self.supabase.table("platform_tools")
                        .update({"tool_functions_schema": schema})
                        .eq("id", str(tool_id))
                        .execute()
                    )
                    if backfill.data:
                        row = backfill.data[0]
                    else:
                        # Persist succeeded server-side even if the RETURNING
                        # row was empty; surface the schema we just wrote.
                        row = dict(row)
                        row["tool_functions_schema"] = schema

            return (
                self._platform_tool_for_response(PlatformTool(**row)),
                None,
            )
        except Exception as e:
            logger.error(f"Error publishing platform tool {tool_id}: {e}")
            return None, str(e)

    @tracer.start_as_current_span("tool.update_platform_tool_functions_schema")
    async def update_platform_tool_functions_schema(
        self, tool_id: UUID, schema: dict
    ) -> tuple[Optional[PlatformTool], Optional[str]]:
        """Persist the public tool catalog discovered from an MCP server.

        OAuth discovery may be performed by a platform admin or by an Org
        Admin's agent connection. The resulting function names and JSON
        Schemas are public catalog metadata; OAuth tokens are deliberately not
        accepted by this method and remain scoped to the agent connection.

        Args:
            tool_id: Platform MCP row to update.
            schema: ``{functions: [...]}`` metadata returned by ``tools/list``.

        Returns:
            The updated sanitized platform tool, or an error string when the
            row does not exist or the database update fails.
        """
        try:
            response = (
                self.supabase.table("platform_tools")
                .update({"tool_functions_schema": schema})
                .eq("id", str(tool_id))
                .execute()
            )
            if not response.data:
                return None, "Platform tool not found"
            return (
                self._platform_tool_for_response(PlatformTool(**response.data[0])),
                None,
            )
        except Exception as e:
            logger.error(
                "Error updating tool catalog for platform tool %s: %s",
                tool_id,
                e,
                exc_info=True,
            )
            return None, str(e)

    @tracer.start_as_current_span("tool.set_platform_tool_premium")
    async def set_platform_tool_premium(
        self, tool_id: UUID, is_premium: bool
    ) -> tuple[Optional[PlatformTool], Optional[str]]:
        """Set or clear a platform tool's ``is_premium`` flag by id.

        Mirrors :meth:`publish_platform_tool`: a single-column update keyed
        on the tool id, so the platform-admin Premium toggle in the tools
        manager never has to resubmit the full create payload. Premium tools
        render with a Premium badge in every org's catalog and attach is
        gated on the plan's ``premium_tools`` feature (the route layer
        enforces the 403). Existing ``agent_tools`` attachments keep working
        regardless of the flag.

        Args:
            tool_id: The ``platform_tools`` row id.
            is_premium: True to gate the tool behind the ``premium_tools``
                plan feature; False to make it available to all plans.

        Returns:
            Tuple of (updated PlatformTool, error). ``(None, "not found")``
            if the row does not exist.
        """
        try:
            response = (
                self.supabase.table("platform_tools")
                .update({"is_premium": is_premium})
                .eq("id", str(tool_id))
                .execute()
            )
            if not response.data:
                return None, "Platform tool not found"
            return (
                self._platform_tool_for_response(PlatformTool(**response.data[0])),
                None,
            )
        except Exception as e:
            logger.error(f"Error setting premium flag on platform tool {tool_id}: {e}")
            return None, str(e)

    async def _discover_functions_schema(self, row: dict) -> Optional[dict]:
        """Best-effort live discovery of a platform tool's exposed tools.

        Builds the MCP server config from the row (public headers + decrypted
        literal secret headers, DROPPING any ``{{KEY}}``-templated header since
        no org API key exists in the platform-admin publish context), opens a
        one-shot :class:`McpClient`, calls ``list_tools()``, and maps the
        results to the ``tool_functions_schema`` shape the agent tool-config
        drawer renders (``{functions: [{name, description, parameters}]}``).

        Used by :meth:`publish_platform_tool` to backfill the tool list for
        catalog rows that were authored before the authoring dialog persisted
        ``tool_functions_schema`` (or published without discovering).

        Args:
            row: A raw ``platform_tools`` row dict (must include
                ``mcp_server_url``; optionally ``mcp_server_headers`` and the
                encrypted ``mcp_server_secret_headers`` blob).

        Returns:
            The ``{functions: [...]}`` schema dict, or ``None`` if discovery
            failed (transport error, decryption error, no URL). ``None`` is
            non-fatal — the caller leaves the existing (null) schema in place.
        """
        # Function-level import: keeps the MCP SDK / client out of import-time
        # for every process that pulls in tool_service, and avoids any circular
        # coupling. Not a shadow of a top-level import.
        from shared.voice_agents.tools.mcp.models import McpServerConfig

        url = row.get("mcp_server_url")
        if not url:
            return None

        # 1. Public (plaintext) static headers.
        headers: dict[str, str] = dict(row.get("mcp_server_headers") or {})
        # 2. Encrypted server-level secret headers. Literal values pass through;
        #    {{KEY}}-templated headers are DROPPED (no org key at platform-publish
        #    time — mirrors dispatch.py's runtime rule, RFC §6.6).
        secret_blob = row.get("mcp_server_secret_headers")
        if secret_blob:
            try:
                secret = decrypt_data(secret_blob)
                if isinstance(secret, dict):
                    for k, v in secret.items():
                        value = str(v)
                        if "{{KEY}}" in value:
                            continue
                        headers[str(k)] = value
            except Exception as e:
                logger.error(
                    "Failed to decrypt mcp_server_secret_headers for backfill of "
                    "%s (%s)",
                    row.get("name"),
                    type(e).__name__,
                )

        config = McpServerConfig(
            url=url,
            name=row.get("mcp_server_name") or row.get("name"),
            headers=headers,
        )
        try:
            from shared.voice_agents.tools.mcp.json_http_client import (
                list_tools_json_http,
            )

            tool_defs = await list_tools_json_http(config)
        except Exception as e:
            logger.warning(
                "Publish-time MCP discover failed for %s (%s)",
                row.get("name"),
                type(e).__name__,
            )
            return None

        return {
            "functions": [
                {
                    "name": td.name,
                    "description": td.description,
                    "parameters": td.input_schema or {},
                }
                for td in tool_defs
            ]
        }

    @tracer.start_as_current_span("tool.update_platform_tool")
    async def update_platform_tool(
        self, tool_id: UUID, tool_data: PlatformToolCreate
    ) -> tuple[Optional[PlatformTool], Optional[str]]:
        """Update a platform tool by id (platform-admin edit of a draft/published server).

        Mirrors :meth:`upsert_platform_tool`'s encryption + org-forcing but
        updates by ``id`` instead of upserting by name. Used by the
        ``PUT /tools/platform/{id}`` route so a platform admin can reconfigure a
        server (URL, headers, auth mode) after authoring.

        Args:
            tool_id: The ``platform_tools`` row id to update.
            tool_data: The new full tool config (same shape as create).

        Returns:
            Tuple of (updated PlatformTool, error). ``(None, "not found")`` if
            the row does not exist.
        """
        try:
            data_dict = tool_data.model_dump(exclude_none=True, mode="json")
            if tool_data.tool_source is ToolSource.MCP:
                data_dict.pop("organization_id", None)
                # Cleared form fields arrive as None and would be dropped by
                # exclude_none — write empty/null explicitly so edits persist.
                data_dict["mcp_server_headers"] = tool_data.mcp_server_headers or {}
                if tool_data.auth_type != "oauth2":
                    # OAuth metadata must not survive a switch to no-auth or
                    # API-key mode and accidentally re-enable the OAuth route.
                    data_dict["auth_config"] = None
            if isinstance(data_dict.get("auth_config"), dict):
                data_dict["auth_config"] = sanitize_oauth_config(
                    data_dict["auth_config"]
                )
            # Always write these so clearing them in the UI is not a no-op.
            data_dict["description"] = tool_data.description
            data_dict["auth_type"] = tool_data.auth_type
            data_dict["requires_auth"] = tool_data.requires_auth
            if tool_data.mcp_secret_headers_input:
                data_dict["mcp_server_secret_headers"] = encrypt_data(
                    tool_data.mcp_secret_headers_input
                )
            elif tool_data.auth_type == "oauth2" or tool_data.requires_auth is False:
                # Switching to OAuth or "No auth" clears stored API-key headers
                # so a later discover/runtime session does not send stale
                # credentials alongside the new auth mode.
                data_dict["mcp_server_secret_headers"] = None
            if tool_data.oauth_client_secret_input:
                data_dict["oauth_client_secret_encrypted"] = encrypt_data(
                    {"client_secret": tool_data.oauth_client_secret_input}
                )
            elif tool_data.auth_type != "oauth2":
                data_dict["oauth_client_secret_encrypted"] = None
            response = (
                self.supabase.table("platform_tools")
                .update(data_dict)
                .eq("id", str(tool_id))
                .execute()
            )
            if not response.data:
                return None, "Platform tool not found"
            return (
                self._platform_tool_for_response(PlatformTool(**response.data[0])),
                None,
            )
        except Exception as e:
            logger.error(f"Error updating platform tool {tool_id}: {e}")
            return None, str(e)

    @tracer.start_as_current_span("tool.get_platform_tool_usage")
    async def get_platform_tool_usage(
        self, tool_id: UUID
    ) -> tuple[Optional[List[dict]], Optional[str]]:
        """List the agents currently using a platform tool.

        Joins ``agent_tools`` to ``voice_agents`` so the caller (platform admin
        delete/unpublish flows) can show which agents reference the tool and, on
        a forced delete, audit exactly which agents were detached. Used by:

        - The ``DELETE /platform/{tool_id}`` route to build the ``in_use`` 409
          body (the list of affected agents) and the force-delete audit entry.
        - The unpublish UI banner ("N agents use this; they keep it") — purely
          informational, since unpublish does not affect existing attachments.

        Args:
            tool_id: The ``platform_tools`` row id.

        Returns:
            A tuple of (agents, error). ``agents`` is a list of dicts::

                {"agent_id": str, "agent_name": str|None, "organization_id": str|None}

            Empty list if no agent uses the tool. ``(None, error)`` on failure.
        """
        try:
            response = (
                self.supabase.table("agent_tools")
                .select("agent_id,voice_agents(name,organization_id)")
                .eq("tool_id", str(tool_id))
                .execute()
            )
            rows = response.data or []
            agents: List[dict] = []
            for row in rows:
                va = row.get("voice_agents") or {}
                agents.append(
                    {
                        "agent_id": row.get("agent_id"),
                        "agent_name": va.get("name"),
                        "organization_id": va.get("organization_id"),
                    }
                )
            return agents, None
        except Exception as e:
            logger.error(f"Error fetching usage for platform tool {tool_id}: {e}")
            return None, str(e)

    @tracer.start_as_current_span("tool.delete_platform_tool")
    async def delete_platform_tool(
        self, tool_id: UUID, *, force: bool = False
    ) -> tuple[Optional[bool], Optional[str]]:
        """Permanently delete a platform tool (platform-admin only).

        Guardrails (RFC §6.6):

        - **Legacy (code-backed) tools are never hard-deleted.** They are
          in-tree ``BaseTool`` subclasses re-seeded by
          ``PlatformToolRegistry.sync_with_db`` on every worker startup, so
          deleting the row is partly futile (it reappears as a draft). Return
          ``"legacy_tools_cannot_be_deleted"``; the caller steers the admin
          to unpublish instead.
        - **An MCP tool referenced by any ``agent_tools`` row cannot be
          deleted without ``force``.** Return ``"in_use"``; the caller
          surfaces the affected agents so the admin can confirm. Without this
          guard, a platform admin could silently strip a capability from agents
          owned by other orgs on their next call.
        - **With ``force=True``**, the ``agent_tools`` rows are detached
          *explicitly first* (so the action is auditable — the route logs the
          detached agent ids) and only then is the ``platform_tools`` row
          removed. The explicit detach is also a defense-in-depth backstop for
          the ``ON DELETE CASCADE`` FK (``agent_tools.tool_id →
          platform_tools.id``) documented in ``docs/DATABASE_SCHEMA.md``.
        - **Unpublish** (``publish_platform_tool(..., False)``) is the
          reversible alternative — existing attachments keep working because
          the worker reads tools by join, not via the catalog listing.

        The route gates this on ``platform_admin`` and writes the audit log on
        a successful force-delete; this method only enforces the data-level
        guardrails so the API stays safe even if the frontend is bypassed.

        Args:
            tool_id: The ``platform_tools`` row id to delete.
            force: When ``True``, allow deleting an MCP tool that is in use,
                explicitly cascade-detaching its ``agent_tools`` rows first.
                Has no effect for native tools (always refused) or for tools
                not in use (delete proceeds regardless).

        Returns:
            Tuple of ``(True, None)`` on success, or ``(None, error)`` where
            ``error`` is one of:

            - ``"Platform tool not found"`` — the row does not exist.
            - ``"legacy_tools_cannot_be_deleted"`` — the row is a legacy
              (code-backed) tool; steer to unpublish.
            - ``"in_use"`` — the tool is referenced by agent_tools and
              ``force`` was not set.
            - Any supabase exception message on transport failure.
        """
        try:
            # 1. Fetch the row to determine tool_source. Native tools are
            # code-backed and re-seeded on worker startup — refuse hard-delete.
            fetch = (
                self.supabase.table("platform_tools")
                .select("tool_source")
                .eq("id", str(tool_id))
                .execute()
            )
            if not fetch.data:
                return None, "Platform tool not found"
            tool_source = (fetch.data[0] or {}).get("tool_source")
            if tool_source == "legacy":
                # Legacy tools are code-backed (in-tree BaseTool subclasses) and
                # re-seeded by PlatformToolRegistry.sync_with_db on every worker
                # startup — hard-deleting the row is futile (it reappears as a
                # draft). Steer the admin to unpublish instead.
                return None, "legacy_tools_cannot_be_deleted"

            # 2. Cross-check agent_tools usage. Without force, refuse to delete
            # a tool still attached to agents (the route returns the list of
            # affected agents in the 409 body it fetched separately).
            usage, usage_error = await self.get_platform_tool_usage(tool_id)
            if usage_error:
                return None, usage_error
            agent_count = len(usage or [])
            if agent_count > 0 and not force:
                return None, "in_use"

            # 3. Force or not-in-use: detach agent_tools explicitly first (so
            # the route can audit which agents lost the tool), then delete the
            # platform_tools row.
            if agent_count > 0:
                (
                    self.supabase.table("agent_tools")
                    .delete()
                    .eq("tool_id", str(tool_id))
                    .execute()
                )
            (
                self.supabase.table("platform_tools")
                .delete()
                .eq("id", str(tool_id))
                .execute()
            )
            return True, None
        except Exception as e:
            logger.error(f"Error deleting platform tool {tool_id}: {e}")
            return None, str(e)

    # Agent Tools
    @tracer.start_as_current_span("tool.configure_agent_tool")
    async def configure_agent_tool(
        self, agent_tool_data: AgentToolCreate
    ) -> tuple[Optional[AgentToolResponse], Optional[str]]:
        """Configure a tool for an agent (upsert)."""
        try:
            # Prepare data for Supabase
            data = agent_tool_data.model_dump()

            # Convert UUID to string for JSON serialization
            data["agent_id"] = str(agent_tool_data.agent_id)
            data["tool_id"] = str(agent_tool_data.tool_id)

            # Encrypt sensitive config if present
            if agent_tool_data.sensitive_config:
                data["sensitive_config"] = encrypt_data(
                    agent_tool_data.sensitive_config
                )

            # Check if configuration already exists
            existing = (
                self.supabase.table("agent_tools")
                .select("*")
                .eq("agent_id", str(agent_tool_data.agent_id))
                .eq("tool_id", str(agent_tool_data.tool_id))
                .execute()
            )

            if existing.data:
                # Update
                update_payload = agent_tool_data.model_dump(
                    exclude={"agent_id", "tool_id"}
                )
                if agent_tool_data.sensitive_config:
                    update_payload["sensitive_config"] = data["sensitive_config"]

                response = (
                    self.supabase.table("agent_tools")
                    .update(update_payload)
                    .eq("id", existing.data[0]["id"])
                    .execute()
                )
            else:
                # Insert
                response = self.supabase.table("agent_tools").insert(data).execute()

            if not response.data:
                return None, "Failed to configure agent tool"

            # Fetch platform tool to get requires_auth for connection status
            platform_tools, _ = await self.get_platform_tools(
                only_active=False, include_drafts=True
            )
            platform_tool = next(
                (t for t in platform_tools if t.id == agent_tool_data.tool_id), None
            )

            # Build response model without sensitive config
            result_data = response.data[0]
            auth_type = platform_tool.auth_type if platform_tool else None
            auth_status_val = validate_token_status(
                result_data.get("sensitive_config"), auth_type=auth_type or "oauth2"
            )
            requires_auth = platform_tool.requires_auth if platform_tool else False
            connection_status_val = get_connection_status(
                requires_auth, auth_status_val
            )
            configuration_issues = check_tool_configuration(
                platform_tool.name if platform_tool else None,
                result_data.get("config"),
            )
            if configuration_issues:
                connection_status_val = ConnectionStatus.CONFIGURATION_REQUIRED
            oauth_metadata = _oauth_response_metadata(
                auth_type,
                platform_tool.auth_config if platform_tool else {},
                result_data.get("sensitive_config"),
            )

            response_dict = {
                "id": result_data["id"],
                "agent_id": result_data["agent_id"],
                "tool_id": result_data["tool_id"],
                "config": result_data.get("config"),
                "unselected_functions": result_data.get("unselected_functions"),
                "is_enabled": result_data.get("is_enabled", True),
                "auth_status": auth_status_val,
                "connection_status": connection_status_val,
                "configuration_issues": configuration_issues,
                "token_expires_at": _token_expiry(result_data.get("sensitive_config")),
                "last_refreshed_at": result_data.get("last_refreshed_at"),
                **oauth_metadata,
                "created_at": result_data["created_at"],
                "updated_at": result_data["updated_at"],
            }
            agent_tool_response = AgentToolResponse(**response_dict)
            if platform_tool:
                agent_tool_response.tool = platform_tool
            return agent_tool_response, None
        except Exception as e:
            logger.error(f"Error configuring agent tool: {e}")
            return None, str(e)

    @tracer.start_as_current_span("tool.get_agent_tools")
    async def get_agent_tools(
        self, agent_id: UUID
    ) -> tuple[List[AgentToolResponse], Optional[str]]:
        """Get all tools configured for an agent, including platform tool details (excludes sensitive config)."""  # noqa: E501
        try:
            # Get agent tool configurations
            response = (
                self.supabase.table("agent_tools")
                .select("*, tool:platform_tools(*)")
                .eq("agent_id", str(agent_id))
                .execute()
            )

            agent_tools = []
            for item in response.data:
                # Extract tool details from the joined query
                tool_data = item.pop("tool")

                # Extract only non-secret token metadata for display.
                token_expires_at = _token_expiry(item.get("sensitive_config"))

                # Build response without sensitive config
                auth_type = tool_data.get("auth_type") if tool_data else None
                auth_status_val = validate_token_status(
                    item.get("sensitive_config"), auth_type=auth_type or "oauth2"
                )
                requires_auth = (
                    tool_data.get("requires_auth", False) if tool_data else False
                )
                connection_status_val = get_connection_status(
                    requires_auth, auth_status_val
                )
                configuration_issues = check_tool_configuration(
                    tool_data.get("name") if tool_data else None,
                    item.get("config"),
                )
                if configuration_issues:
                    connection_status_val = ConnectionStatus.CONFIGURATION_REQUIRED
                oauth_metadata = _oauth_response_metadata(
                    auth_type,
                    tool_data.get("auth_config") if tool_data else {},
                    item.get("sensitive_config"),
                )

                response_dict = {
                    "id": item["id"],
                    "agent_id": item["agent_id"],
                    "tool_id": item["tool_id"],
                    "config": item.get("config"),
                    "unselected_functions": item.get("unselected_functions"),
                    "is_enabled": item.get("is_enabled", True),
                    "auth_status": auth_status_val,
                    "connection_status": connection_status_val,
                    "configuration_issues": configuration_issues,
                    "token_expires_at": _token_expiry(item.get("sensitive_config")),
                    "last_refreshed_at": item.get("last_refreshed_at"),
                    **oauth_metadata,
                    "created_at": item["created_at"],
                    "updated_at": item["updated_at"],
                }

                agent_tool = AgentToolResponse(**response_dict)
                if tool_data:
                    agent_tool.tool = self._platform_tool_for_response(
                        PlatformTool(**tool_data)
                    )
                agent_tools.append(agent_tool)

            return agent_tools, None
        except Exception as e:
            logger.error(f"Error getting agent tools for agent {agent_id}: {e}")
            return [], str(e)

    @tracer.start_as_current_span("tool.get_agent_tools_with_sensitive_config")
    async def get_agent_tools_with_sensitive_config(
        self, agent_id: UUID
    ) -> tuple[List[AgentTool], Optional[str]]:
        """Get all tools configured for an agent with full details including sensitive config (for worker)."""  # noqa: E501
        try:
            # Get agent tool configurations
            response = (
                self.supabase.table("agent_tools")
                .select("*, tool:platform_tools(*)")
                .eq("agent_id", str(agent_id))
                .execute()
            )

            agent_tools = []
            for item in response.data:
                # Extract tool details from the joined query
                tool_data = item.pop("tool")

                # Decrypt sensitive config
                sensitive_config = None
                if item.get("sensitive_config"):
                    try:
                        decrypted_config = decrypt_data(item.get("sensitive_config"))
                        if decrypted_config and isinstance(decrypted_config, dict):
                            sensitive_config = decrypted_config
                    except Exception as e:
                        logger.error(
                            "Error decrypting sensitive config (%s)",
                            type(e).__name__,
                        )

                # Build full AgentTool with sensitive config
                agent_tool_dict = {
                    "id": item["id"],
                    "agent_id": item["agent_id"],
                    "tool_id": item["tool_id"],
                    "config": item.get("config"),
                    "sensitive_config": sensitive_config,
                    "unselected_functions": item.get("unselected_functions"),
                    "is_enabled": item.get("is_enabled", True),
                    "last_refreshed_at": item.get("last_refreshed_at"),
                    "created_at": item["created_at"],
                    "updated_at": item["updated_at"],
                }

                agent_tool = AgentTool(**agent_tool_dict)
                if tool_data:
                    agent_tool.tool = PlatformTool(**tool_data)
                agent_tools.append(agent_tool)

            return agent_tools, None
        except Exception as e:
            logger.error(
                f"Error getting agent tools with sensitive config for agent {agent_id}: {e}"  # noqa: E501
            )
            return [], str(e)

    @tracer.start_as_current_span("tool.get_agent_tool_by_id")
    async def get_agent_tool_by_id(
        self, agent_tool_id: UUID
    ) -> tuple[Optional[AgentToolResponse], Optional[str]]:
        """Fetch a single agent tool configuration by its ID.

        Used by route handlers to resolve ``agent_tool_id`` to the parent
        ``agent_id`` for permission checks (so the route can then load the
        agent and verify the caller is an org/platform admin on the agent's
        organization). Returns ``(None, None)`` if not found and ``(None,
        error)`` on a DB failure.

        Args:
            agent_tool_id: UUID of the ``agent_tools`` row to fetch.

        Returns:
            Tuple of (AgentToolResponse or None, error message or None).
        """
        try:
            response = (
                self.supabase.table("agent_tools")
                .select("*, tool:platform_tools(*)")
                .eq("id", str(agent_tool_id))
                .execute()
            )

            if not response.data:
                return None, None

            item = response.data[0]
            tool_data = item.pop("tool") if "tool" in item else None

            auth_type = tool_data.get("auth_type") if tool_data else None
            auth_status_val = validate_token_status(
                item.get("sensitive_config"),
                auth_type=auth_type or "oauth2",
            )
            requires_auth = (
                tool_data.get("requires_auth", False) if tool_data else False
            )
            connection_status_val = get_connection_status(
                requires_auth, auth_status_val
            )

            response_dict = {
                "id": item["id"],
                "agent_id": item["agent_id"],
                "tool_id": item["tool_id"],
                "config": item.get("config"),
                "unselected_functions": item.get("unselected_functions"),
                "is_enabled": item.get("is_enabled", True),
                "auth_status": auth_status_val,
                "connection_status": connection_status_val,
                "token_expires_at": _token_expiry(item.get("sensitive_config")),
                "last_refreshed_at": item.get("last_refreshed_at"),
                **_oauth_response_metadata(
                    auth_type,
                    tool_data.get("auth_config") if tool_data else {},
                    item.get("sensitive_config"),
                ),
                "created_at": item["created_at"],
                "updated_at": item["updated_at"],
            }

            agent_tool = AgentToolResponse(**response_dict)
            if tool_data:
                try:
                    agent_tool.tool = self._platform_tool_for_response(
                        PlatformTool(**tool_data)
                    )
                except Exception:
                    # Tool metadata is optional in the response; swallow
                    # validation errors here so the route can still resolve
                    # the agent_id for the permission check.
                    pass
            return agent_tool, None
        except Exception as e:
            logger.error(f"Error getting agent tool {agent_tool_id}: {e}")
            return None, str(e)

    @tracer.start_as_current_span("tool.update_agent_tool")
    async def update_agent_tool(
        self, agent_tool_id: UUID, update_data: AgentToolUpdate
    ) -> tuple[Optional[AgentToolResponse], Optional[str]]:
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

            # Handle last_refreshed_at - convert datetime to ISO string if present
            if update_data.last_refreshed_at is not None:
                data["last_refreshed_at"] = update_data.last_refreshed_at.isoformat()

            response = (
                self.supabase.table("agent_tools")
                .update(data)
                .eq("id", str(agent_tool_id))
                .execute()
            )

            if not response.data:
                return None, "Agent tool configuration not found"

            # Fetch platform tool to get auth_type for auth status validation
            result_data = response.data[0]
            platform_tools, _ = await self.get_platform_tools(
                only_active=False, include_drafts=True
            )
            platform_tool = next(
                (t for t in platform_tools if t.id == result_data["tool_id"]), None
            )

            # Build response model without sensitive config
            auth_type = platform_tool.auth_type if platform_tool else None
            response_dict = {
                "id": result_data["id"],
                "agent_id": result_data["agent_id"],
                "tool_id": result_data["tool_id"],
                "config": result_data.get("config"),
                "unselected_functions": result_data.get("unselected_functions"),
                "is_enabled": result_data.get("is_enabled", True),
                "auth_status": validate_token_status(
                    result_data.get("sensitive_config"), auth_type=auth_type or "oauth2"
                ),
                "token_expires_at": _token_expiry(result_data.get("sensitive_config")),
                "last_refreshed_at": result_data.get("last_refreshed_at"),
                **_oauth_response_metadata(
                    auth_type,
                    platform_tool.auth_config if platform_tool else {},
                    result_data.get("sensitive_config"),
                ),
                "created_at": result_data["created_at"],
                "updated_at": result_data["updated_at"],
            }

            return AgentToolResponse(**response_dict), None
        except Exception as e:
            logger.error(f"Error updating agent tool {agent_tool_id}: {e}")
            return None, str(e)

    @tracer.start_as_current_span("tool.delete_agent_tool")
    async def delete_agent_tool(
        self, agent_tool_id: UUID
    ) -> tuple[Optional[bool], Optional[str]]:
        """Permanently delete an agent tool configuration."""
        try:
            (
                self.supabase.table("agent_tools")
                .delete()
                .eq("id", str(agent_tool_id))
                .execute()
            )

            return True, None
        except Exception as e:
            logger.error(f"Error deleting agent tool {agent_tool_id}: {e}")
            return None, str(e)

    @tracer.start_as_current_span("tool.get_all_agent_tools_with_auth")
    @_with_retry(max_retries=3)
    async def get_all_agent_tools_with_auth(
        self,
    ) -> tuple[List[AgentTool], Optional[str]]:
        """Get all enabled OAuth agent tools with decrypted state for refresh.

        Returns:
            List of OAuth AgentTool objects with sensitive config for token refresh
        """
        try:
            # Get all agent_tools that require auth (requires filter)
            # Join with platform_tools to filter by requires_auth
            response = (
                self.supabase.table("agent_tools")
                .select(
                    "*, tool:platform_tools(*), " "voice_agents(name,organization_id)"
                )
                .eq("is_enabled", True)
                .execute()
            )

            agent_tools = []
            for item in response.data:
                # Defense-in-depth: skip disabled tools even if the DB filter changes.
                if not item.get("is_enabled", True):
                    continue

                # Extract tool details from joined query
                tool_data = item.get("tool")

                # Filter to only tools requiring auth
                if not tool_data or not tool_data.get("requires_auth", False):
                    continue

                # TokenRefreshService is OAuth-specific. Keep API-key and
                # other manual credential tools out of its candidate set while
                # still accepting future OAuth rows whose auth_type was not
                # normalized but whose metadata clearly contains OAuth fields.
                auth_type = str(tool_data.get("auth_type") or "").lower()
                auth_config = tool_data.get("auth_config")
                oauth_metadata_keys = {
                    "token_url",
                    "authorization_url",
                    "oauth_mode",
                    "oauth_refresh_mode",
                    "oauth2",
                }
                has_oauth_metadata = isinstance(auth_config, dict) and bool(
                    oauth_metadata_keys.intersection(auth_config)
                )
                if (
                    auth_type not in {"oauth", "oauth2", "oauth_2"}
                    and not has_oauth_metadata
                ):
                    continue

                # Only process if there's sensitive_config (tokens exist)
                if not item.get("sensitive_config"):
                    continue

                # Decrypt sensitive config
                sensitive_config = None
                try:
                    decrypted_config = decrypt_data(item.get("sensitive_config"))
                    if decrypted_config and isinstance(decrypted_config, dict):
                        sensitive_config = decrypted_config
                except Exception as e:
                    logger.error(
                        "Error decrypting sensitive config (%s)",
                        type(e).__name__,
                    )
                    continue

                # Build full AgentTool with sensitive config
                agent_data = item.get("voice_agents") or {}
                if isinstance(agent_data, list):
                    agent_data = agent_data[0] if agent_data else {}
                agent_tool_dict = {
                    "id": item["id"],
                    "agent_id": item["agent_id"],
                    "tool_id": item["tool_id"],
                    "config": item.get("config"),
                    "sensitive_config": sensitive_config,
                    "unselected_functions": item.get("unselected_functions"),
                    "is_enabled": item.get("is_enabled", True),
                    "created_at": item["created_at"],
                    "updated_at": item["updated_at"],
                    "last_refreshed_at": item.get("last_refreshed_at"),
                    "agent_name": agent_data.get("name"),
                    "organization_id": agent_data.get("organization_id"),
                }

                agent_tool = AgentTool(**agent_tool_dict)
                if tool_data:
                    agent_tool.tool = PlatformTool(**tool_data)
                agent_tools.append(agent_tool)

            return agent_tools, None
        except Exception as e:
            logger.error(
                "Error getting all agent tools with auth (%s)", type(e).__name__
            )
            return [], str(e)


tool_service = ToolService()
