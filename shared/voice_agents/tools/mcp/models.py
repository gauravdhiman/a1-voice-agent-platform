"""Data models for the MCP tool-integration path.

These models are intentionally narrow: they carry only what the worker and the
backend schema-discovery path need from an MCP server. They are decoupled from
the ``mcp`` SDK's own types so callers do not depend on SDK internals.
"""

from typing import Any, Optional

from pydantic import BaseModel, Field


class McpServerConfig(BaseModel):
    """Connection definition for a remote MCP server.

    Attributes:
        url: Streamable HTTP endpoint of the MCP server, e.g.
            ``https://host/mcp``. The path is server-defined (FastMCP uses
            ``/mcp``).
        name: Human-readable server name, used for logging and for the
            ``platform_tools`` row label. Optional.
        headers: Static headers sent on every request (e.g. a public tenant
            identifier). Per-org OAuth/API-key credentials are injected
            separately at call time.
        secret_headers: Credential header templates extracted from a pasted
            host configuration. ``{{KEY}}`` is the platform's canonical
            placeholder and is resolved only after an org admin connects the
            server.
        transport: Normalized remote transport. The hosted runtime currently
            executes ``streamable_http``; other transports are reported by the
            parser instead of being silently misconfigured.
        auth_type: Normalized authentication mode (``api_key`` or ``oauth2``)
            when the source configuration declares one.
        requires_auth: Whether an end-user credential is needed to connect.
        auth_config: Normalized OAuth metadata when the source configuration
            includes it. MCP itself does not define a universal config-file
            schema, so this field intentionally accepts provider extensions.
        timeout: Per-request timeout in seconds.
    """

    url: str
    name: Optional[str] = None
    headers: dict[str, str] = Field(default_factory=dict)
    secret_headers: dict[str, str] = Field(default_factory=dict)
    transport: str = "streamable_http"
    auth_type: Optional[str] = None
    requires_auth: bool = False
    auth_config: dict[str, Any] = Field(default_factory=dict)
    timeout: float = 30.0


class McpToolDef(BaseModel):
    """A tool exposed by an MCP server, as discovered via ``tools/list``.

    Attributes:
        name: Tool name (unique within a server).
        description: Human-readable description exposed to the LLM.
        input_schema: JSON Schema (2020-12) for the tool's arguments, taken
            verbatim from the server's ``inputSchema`` and sanitized for Pipecat.
    """

    name: str
    description: Optional[str] = None
    input_schema: dict[str, Any] = Field(default_factory=dict)


class McpToolResult(BaseModel):
    """The result of invoking an MCP tool via ``tools/call``.

    Attributes:
        content: Raw content blocks returned by the server, each a dict with
            at least a ``type`` key (e.g. ``{"type": "text", "text": "5"}``).
            Preserved verbatim so callers can handle non-text content
            (images, embedded resources) in later phases.
        is_error: True when the server reports the call as an error (unknown
            tool, bad arguments, server-side failure). The client does not
            raise on these; it surfaces them here so the agent loop can decide.

    The :pyattr:`text` convenience property joins all ``text`` content blocks
    into a single string, which covers the common arithmetic / string tool
    case used in Phase 1.
    """

    content: list[dict[str, Any]] = Field(default_factory=list)
    is_error: bool = False

    @property
    def text(self) -> str:
        """Concatenate all ``text`` content blocks into one string.

        Non-text blocks (images, resources) are skipped. Returns "" when there
        is no text content (e.g. an error result with no text payload).
        """
        return "".join(
            block.get("text", "")
            for block in self.content
            if isinstance(block, dict) and block.get("type") == "text"
        )
