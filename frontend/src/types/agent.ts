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
  CONFIGURATION_REQUIRED = "configuration_required", // Attached but missing required tool configuration
}

/** Scoped agent counts returned by the workspace dashboard endpoint. */
export interface OrganizationAgentSummary {
  total_agents: number;
  active_agents: number;
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
  /** When true, this agent is a demo agent (platform-admin only, bypasses credits, public at /demo/{slug}). */
  is_demo?: boolean;
  /** Unique slug for the demo public page (required when is_demo true). */
  demo_slug?: string | null;
  /** Customer-facing description shown on the public demo page (marketing copy). */
  public_description?: string | null;
  /** Optional HTTPS destination shown after a successful demo handoff. */
  demo_public_result_url?: string | null;
  /** Remaining demo call reservations; -1 means unlimited. */
  demo_calls_remaining?: number;
  /** Maximum demo call duration in seconds; -1 means unlimited. */
  demo_max_call_duration_seconds?: number;
  instructions_markdown: string | null;
  /**
   * Voice-engine preset referenced by this agent (Phase 4). `null` = use the
   * system default voice profile (the admin-designated fallback on
   * `/platform/presets`; the worker falls back to the hardcoded realtime config
   * only if the default row is missing/unparseable). The worker fetches the
   * preset row live on every call. Set via the agent picker ("voice profile");
   * the org user picks by preset name + description only and never sees
   * engine/stage detail. May be `null` for agents created before presets shipped.
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
  /** Platform-admin only: demo flag, public copy, and optional trial limits. */
  is_demo?: boolean;
  demo_slug?: string | null;
  public_description?: string | null;
  /** Platform-admin only: optional HTTPS destination shown after success. */
  demo_public_result_url?: string | null;
  /** Platform-admin only: remaining demo call reservations; -1 means unlimited. */
  demo_calls_remaining?: number;
  /** Platform-admin only: maximum demo call duration in seconds; -1 means unlimited. */
  demo_max_call_duration_seconds?: number;
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
  call_recording_enabled?: boolean;
  use_platform_credits?: boolean;
  /** Platform-admin only: mark as demo agent. */
  is_demo?: boolean;
  /** Platform-admin only: unique slug for /demo/{slug} (required when is_demo true). */
  demo_slug?: string | null;
  /** Customer-facing description for the public demo page. */
  public_description?: string | null;
  /** Platform-admin only: optional HTTPS destination shown after success. */
  demo_public_result_url?: string | null;
  /** Platform-admin only: remaining demo call reservations; -1 means unlimited. */
  demo_calls_remaining?: number;
  /** Platform-admin only: maximum demo call duration in seconds; -1 means unlimited. */
  demo_max_call_duration_seconds?: number;
  instructions_markdown?: string | null;
  /** Voice-engine preset id; `null` = system default. */
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

/**
 * How an OAuth provider keeps a connection alive after its access token
 * expires. The value is derived by the backend from provider metadata and the
 * live connection's encrypted refresh-token presence.
 */
export type OAuthRefreshMode = "automatic" | "manual" | "unknown";

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
  /** Effective organization-level visibility for this catalog response. */
  is_visible?: boolean;
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
  /** Whether OAuth refresh is automatic, manual, or not declared. */
  oauth_refresh_mode?: OAuthRefreshMode | null;
  /** Optional platform-admin-declared manual reauthorization interval. */
  oauth_refresh_interval_minutes?: number | null;
  /** Safe refresh guidance suitable for platform and organization admins. */
  oauth_refresh_message?: string | null;
  /** Whether a confidential OAuth client secret is configured. */
  oauth_client_secret_configured?: boolean;
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
  /** Missing configuration pieces (empty when the attachment is complete). */
  configuration_issues?: string[];
  /** Timestamp of the most recent automatic token refresh, if any. */
  last_refreshed_at: string | null;
  /** Actual/expected OAuth refresh behavior for this connection. */
  oauth_refresh_mode: OAuthRefreshMode | null;
  /** Optional manual reauthorization interval in minutes. */
  oauth_refresh_interval_minutes: number | null;
  /** Safe refresh guidance for the connection administrator. */
  oauth_refresh_message: string | null;
  created_at: string;
  updated_at: string;
  tool?: PlatformTool;
}

/** Safe tool-health flags returned for one agent on the agents list page. */
export interface AgentToolAttentionSummary {
  agent_id: string;
  /** True when any connected tool needs authentication or configuration. */
  needs_attention: boolean;
  /** True when the agent has the organization-configured Resend tool attached. */
  has_resend_email_tool: boolean;
}

/** Read-only tab/header metadata returned while configuring Google Sheets. */
export interface GoogleSheetsDiscoveredSheet {
  title: string;
  sheet_id: number | null;
  headers: string[];
  header_range: string;
  issues: string[];
}

/** Safe result of the authenticated Google Sheets header discovery probe. */
export interface GoogleSheetsDiscovery {
  status: "succeeded";
  provider: "google_sheets";
  sheets: GoogleSheetsDiscoveredSheet[];
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
