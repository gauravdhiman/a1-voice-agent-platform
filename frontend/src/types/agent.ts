/**
 * Voice Agent and Tool related type definitions
 */

export enum AuthStatus {
  NOT_AUTHENTICATED = "not_authenticated", // No tokens exist
  AUTHENTICATED = "authenticated", // Valid tokens exist
  EXPIRED = "expired", // Tokens exist but have expired
}

export enum ConnectionStatus {
  NOT_CONNECTED = "not_connected", // No agent_tools record
  CONNECTED_NO_AUTH = "connected_no_auth", // Connected, tool doesn't require auth
  CONNECTED_AUTH_VALID = "connected_auth_valid", // Connected, requires auth, valid tokens
  CONNECTED_AUTH_INVALID = "connected_auth_invalid", // Connected, requires auth, invalid/missing tokens
}

export interface VoiceAgent {
  id: string;
  organization_id: string;
  name: string;
  description: string | null;
  phone_number: string | null;
  system_prompt: string | null;
  persona: string | null;
  tone: string | null;
  mission: string | null;
  custom_instructions: string | null;
  voice_settings: Record<string, unknown> | null;
  is_active: boolean;
  /** Explicit publish flag for the org public page at `/o/{slug}`. */
  is_published_on_public_page?: boolean;
  /** Whether calls handled by this agent may be recorded. Defaults to false. */
  call_recording_enabled: boolean;
  use_platform_credits: boolean;
  instructions_markdown: string | null;
  /**
   * Voice-engine preset referenced by this agent (Phase 4). `null` = use the
   * system default voice profile (the admin-designated fallback on
   * `/platform/presets`; the worker falls back to the hardcoded realtime config
   * only if the default row is missing/unparseable). The worker fetches the
   * preset row live on every call. Set via the agent picker ("voice profile");
   * the org user picks by preset name + description only and never sees
   * engine/stage
   * detail. May be `null` for agents created before presets shipped.
   */
  preset_id: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface VoiceAgentCreate {
  organization_id: string;
  name: string;
  phone_number?: string | null;
  system_prompt?: string | null;
  persona?: string | null;
  tone?: string | null;
  mission?: string | null;
  custom_instructions?: string | null;
  is_active?: boolean;
  /** Whether calls handled by this agent may be recorded. Defaults to false. */
  call_recording_enabled?: boolean;
  use_platform_credits?: boolean;
  instructions_markdown?: string | null;
  /** Voice-engine preset id; `null` = system default. */
  preset_id?: string | null;
}

export interface VoiceAgentUpdate {
  name?: string;
  phone_number?: string | null;
  system_prompt?: string | null;
  persona?: string | null;
  tone?: string | null;
  mission?: string | null;
  custom_instructions?: string | null;
  is_active?: boolean;
  is_published_on_public_page?: boolean;
  /** Whether calls handled by this agent may be recorded. */
  call_recording_enabled?: boolean;
  use_platform_credits?: boolean;
  instructions_markdown?: string | null;
  /** Voice-engine preset id; `null` clears it (falls back to the system default). */
  preset_id?: string | null;
}

export interface PlatformToolFunction {
  type: string;
  name: string;
  description: string;
  parameters?: {
    type: string;
    properties?: Record<
      string,
      {
        type: string;
        description?: string;
        default?: unknown;
      }
    >;
    required?: string[];
  };
}

/**
 * Where a `PlatformTool` is served from.
 *
 * Mirrors the backend `ToolSource` enum in `shared/voice_agents/tool_models.py`:
 *   - `legacy` — a hand-rolled `BaseTool` subclass resolved via the platform tool registry
 *     registry (in `shared/voice_agents/tools/base/`).
 *   - `mcp` — a remote MCP server (Streamable HTTP) discovered at runtime by
 *     the worker's MCP client (`shared/voice_agents/tools/mcp/`).
 *
 * Optional on the frontend so legacy tool payloads that predate the MCP
 * schema extension still type-check; the backend always emits it (defaulting
 * to `legacy`).
 */
export type ToolSource = "legacy" | "mcp";

export interface PlatformTool {
  id: string;
  name: string;
  description: string | null;
  config_schema: Record<string, unknown> | null;
  tool_functions_schema: {
    functions: PlatformToolFunction[];
  } | null;
  is_active: boolean;
  /**
   * Premium tools require the org's plan to entitle the ``premium_tools``
   * feature. They remain visible in the catalog with a Premium badge; the
   * attach action is blocked in the UI and enforced by the API.
   */
  is_premium?: boolean;
  /**
   * Publish-lifecycle flag (RFC §6.6). `false` (draft) = platform-admin-only;
   * `true` (published) + `is_active=true` = visible to all org users in the
   * tool panel as a normal tool card they can attach. Platform admins author a
   * server as a draft, test it, then publish it to the global catalog.
   */
  is_published?: boolean;
  created_at: string;
  updated_at: string;
  auth_type: string | null;
  requires_auth: boolean;
  auth_config: Record<string, unknown> | null;
  /** Origin of the tool — legacy BaseTool vs remote MCP server. */
  tool_source?: ToolSource;
  /** Streamable-HTTP URL of the remote MCP server (MCP tools only). */
  mcp_server_url?: string | null;
  /** Short label for the MCP server (MCP tools only). */
  mcp_server_name?: string | null;
  /** Extra HTTP headers to send to the MCP server (e.g. auth). */
  mcp_server_headers?: Record<string, string> | null;
  /**
   * Owning organization for an MCP server.
   * DORMANT: the org-scoped custom tier is retired (RFC §6.6) — all published
   * MCP servers are global catalog entries (`null`), authored by platform
   * admins. The column is kept for a future org-private-publish tier; the
   * org-scoped read/create code paths are removed.
   */
  organization_id?: string | null;
  /**
   * Read-only flag: true when encrypted server-level secret headers are
   * configured for this MCP server. The decrypted secret values are never
   * returned to the frontend — this flag just drives UI affordances.
   */
  mcp_secret_headers_configured?: boolean;
}

/**
 * One agent currently using a platform tool (RFC §6.6 delete guardrails).
 *
 * Surfaced by `GET /api/v1/tools/platform/{toolId}/usage` so the platform-admin
 * delete-confirm dialog can list which agents reference the tool (and, on a
 * forced delete, which agents will lose it on their next call) and the
 * unpublish flow can show an informational "N agents use this" banner.
 *
 * `agent_name` / `organization_id` may be null if the joined voice_agents row
 * is missing or the column is unset.
 */
export interface PlatformToolUsageAgent {
  agent_id: string;
  agent_name: string | null;
  organization_id: string | null;
}

/** Result of `GET /api/v1/tools/platform/{toolId}/usage`. */
export interface PlatformToolUsage {
  count: number;
  agents: PlatformToolUsageAgent[];
}

/**
 * A discovered tool from a remote MCP server (POST /tools/mcp/discover).
 * Returned sanitized — name, description, and the JSON Schema of its input.
 */
export interface DiscoveredMcpTool {
  name: string;
  description: string | null;
  input_schema: Record<string, unknown> | null;
}

/** Response from POST /tools/mcp/parse — parsed `mcpServers` JSON. */
export interface ParsedMcpServer {
  name: string;
  url: string;
  headers: Record<string, string>;
  /** Credential templates extracted from host config and encrypted on save. */
  secret_headers?: Record<string, string>;
  /** Normalized auth mode: api_key, oauth2, or null for anonymous HTTP. */
  auth_type?: string | null;
  /** True when the org admin must provide a credential at attach time. */
  requires_auth?: boolean;
  /** Provider-neutral OAuth metadata when present in the source config. */
  auth_config?: Record<string, unknown>;
  /** Normalized transport; currently streamable_http for hosted entries. */
  transport?: string;
}

/** Per-entry parse error (e.g. a stdio entry was rejected). */
export interface ParsedMcpServerError {
  name: string;
  message: string;
}

export interface ParsedMcpServersResult {
  servers: ParsedMcpServer[];
  errors: ParsedMcpServerError[];
}

export interface AgentTool {
  id: string;
  agent_id: string;
  tool_id: string;
  config: Record<string, unknown> | null;
  sensitive_config: Record<string, unknown> | null;
  unselected_functions: string[] | null;
  is_enabled: boolean;
  auth_status: AuthStatus;
  token_expires_at: number | null;
  connection_status: ConnectionStatus;
  created_at: string;
  updated_at: string;
  tool?: PlatformTool;
}

export interface AgentToolCreate {
  agent_id: string;
  tool_id: string;
  config?: Record<string, unknown> | null;
  sensitive_config?: Record<string, unknown> | null;
  unselected_functions?: string[] | null;
  is_enabled?: boolean;
}

export interface AgentToolUpdate {
  config?: Record<string, unknown> | null;
  sensitive_config?: Record<string, unknown> | null;
  unselected_functions?: string[] | null;
  is_enabled?: boolean;
}
