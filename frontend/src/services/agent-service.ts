// services/agent-service.ts
import { apiClient } from "@/lib/api/client";
import type {
  VoiceAgent,
  VoiceAgentCreate,
  VoiceAgentUpdate,
  PlatformTool,
  PlatformToolUsage,
  AgentTool,
  AgentToolCreate,
  AgentToolUpdate,
  DiscoveredMcpTool,
  ParsedMcpServersResult,
} from "@/types/agent";

class AgentService {
  private agentBaseUrl = "/api/v1/agents";
  private toolBaseUrl = "/api/v1/tools";

  // Voice Agent Methods
  async createAgent(agentData: VoiceAgentCreate): Promise<VoiceAgent> {
    const response = await apiClient.post<VoiceAgent>(
      this.agentBaseUrl,
      agentData,
    );
    return response.data;
  }

  async getOrgAgents(orgId: string): Promise<VoiceAgent[]> {
    const response = await apiClient.get<VoiceAgent[]>(
      `${this.agentBaseUrl}/organization/${orgId}`,
    );
    return response.data;
  }

  async getMyAgents(): Promise<VoiceAgent[]> {
    const response = await apiClient.get<VoiceAgent[]>(
      `${this.agentBaseUrl}/my-agents`,
    );
    return response.data;
  }

  async getAgentById(agentId: string): Promise<VoiceAgent> {
    const response = await apiClient.get<VoiceAgent>(
      `${this.agentBaseUrl}/${agentId}`,
    );
    return response.data;
  }

  async getAgentSystemPrompt(agentId: string): Promise<string> {
    const response = await apiClient.get<string>(
      `${this.agentBaseUrl}/${agentId}/system-prompt`,
    );
    return response.data;
  }

  async generateMarkdown(agentId: string): Promise<string> {
    const response = await apiClient.post<string>(
      `${this.agentBaseUrl}/${agentId}/generate-markdown`,
    );
    return response.data;
  }

  async updateAgent(
    agentId: string,
    agentData: VoiceAgentUpdate,
  ): Promise<VoiceAgent> {
    const response = await apiClient.put<VoiceAgent>(
      `${this.agentBaseUrl}/${agentId}`,
      agentData,
    );
    return response.data;
  }

  async deleteAgent(agentId: string): Promise<void> {
    await apiClient.delete(`${this.agentBaseUrl}/${agentId}`);
  }

  // Tool Methods
  /**
   * List platform tools visible to the caller (publish lifecycle, RFC §6.6).
   *
   * Org users see only **published** rows by default — the global catalog they
   * can attach to their agents. Platform admins pass `{ includeDrafts: true }`
   * to also see draft (unpublished) MCP servers they are authoring; the
   * backend rejects a non-platform-admin that sets it (403). The org-scoped
   * custom tier is retired, so there is no per-org filter.
   */
  async getPlatformTools(
    onlyActive = true,
    opts?: { includeDrafts?: boolean },
  ): Promise<PlatformTool[]> {
    const params = new URLSearchParams({ only_active: String(onlyActive) });
    if (opts?.includeDrafts) params.set("include_drafts", "true");
    const response = await apiClient.get<PlatformTool[]>(
      `${this.toolBaseUrl}/platform?${params.toString()}`,
    );
    return response.data;
  }

  /**
   * Publish or unpublish a platform tool (platform-admin only, RFC §6.6).
   * Publishing flips `is_published` to true, surfacing the server in every
   * org's tool catalog; unpublishing hides it from new attaches (existing
   * attachments keep working).
   */
  async publishPlatformTool(
    toolId: string,
    published: boolean,
  ): Promise<PlatformTool> {
    const endpoint = published ? "publish" : "unpublish";
    const response = await apiClient.post<PlatformTool>(
      `${this.toolBaseUrl}/platform/${toolId}/${endpoint}`,
    );
    return response.data;
  }

  /**
   * Update a platform tool (platform-admin only, RFC §6.6). Used to edit a
   * draft or published MCP server's URL, headers, or `{{KEY}}` template.
   * Secret headers are encrypted at rest by the backend; never sent back as
   * plaintext.
   */
  async updatePlatformTool(
    toolId: string,
    payload: Record<string, unknown>,
  ): Promise<PlatformTool> {
    const response = await apiClient.put<PlatformTool>(
      `${this.toolBaseUrl}/platform/${toolId}`,
      payload,
    );
    return response.data;
  }

  /**
   * Delete a platform tool (platform-admin only, RFC §6.6).
   *
   * Guardrails: a legacy (code-backed) tool is refused with 400 (steer to
   * unpublish); an MCP tool referenced by any agent is refused with 409
   * `in_use` unless `force` is set. With `force`, the backend cascade-detaches
   * the agent_tools rows first (audited) and removes the catalog row.
   *
   * The UI pre-fetches usage via `getPlatformToolUsage` and passes
   * `force = count > 0` after a type-to-confirm dialog, so the 409 path is a
   * backend safety net against races / direct API calls.
   *
   * @param toolId  Platform tool id to delete.
   * @param force   When true, sends `?force=true` to allow an in-use delete.
   */
  async deletePlatformTool(
    toolId: string,
    force = false,
  ): Promise<{ deleted: boolean }> {
    const query = force ? "?force=true" : "";
    const response = await apiClient.delete<{ deleted: boolean }>(
      `${this.toolBaseUrl}/platform/${toolId}${query}`,
    );
    return response.data;
  }

  /**
   * List the agents currently using a platform tool (platform-admin only,
   * RFC §6.6). Powers the delete-confirm dialog's "used by N agents" warning
   * list and the unpublish info banner. Returns `{ count, agents[] }`.
   */
  async getPlatformToolUsage(
    toolId: string,
  ): Promise<PlatformToolUsage> {
    const response = await apiClient.get<PlatformToolUsage>(
      `${this.toolBaseUrl}/platform/${toolId}/usage`,
    );
    return response.data;
  }

  async getAgentTools(agentId: string): Promise<AgentTool[]> {
    const response = await apiClient.get<AgentTool[]>(
      `${this.toolBaseUrl}/agent/${agentId}`,
    );
    return response.data;
  }

  async configureAgentTool(toolData: AgentToolCreate): Promise<AgentTool> {
    const response = await apiClient.post<AgentTool>(
      `${this.toolBaseUrl}/agent`,
      toolData,
    );
    return response.data;
  }

  async updateAgentTool(
    agentToolId: string,
    updateData: AgentToolUpdate,
  ): Promise<AgentTool> {
    const response = await apiClient.put<AgentTool>(
      `${this.toolBaseUrl}/agent/${agentToolId}`,
      updateData,
    );
    return response.data;
  }

  async startOAuth(
    toolName: string,
    agentId: string,
  ): Promise<{ auth_url: string }> {
    const response = await apiClient.get<{ auth_url: string }>(
      `${this.toolBaseUrl}/auth/${toolName}?agent_id=${agentId}`,
    );
    return response.data;
  }

  async logoutAgentTool(agentToolId: string): Promise<AgentTool> {
    const response = await apiClient.post<AgentTool>(
      `${this.toolBaseUrl}/agent/${agentToolId}/logout`,
    );
    return response.data;
  }

  async setApiKey(agentToolId: string, apiKey: string): Promise<AgentTool> {
    const response = await apiClient.put<AgentTool>(
      `${this.toolBaseUrl}/agent/${agentToolId}/api-key`,
      { api_key: apiKey },
    );
    return response.data;
  }

  async deleteAgentTool(agentToolId: string): Promise<void> {
    await apiClient.delete(`${this.toolBaseUrl}/agent/${agentToolId}`);
  }

  // MCP Server Methods

  /**
   * Discover the tools exposed by a remote MCP server (in-memory; nothing
   * persisted). Used by the "Test connection & discover tools" button in the
   * Add MCP Server dialog. The backend validates the URL against the SSRF guard
   * before opening a transient McpClient.
   */
  async discoverMcpTools(
    payload: { url: string; headers?: Record<string, string> },
  ): Promise<DiscoveredMcpTool[]> {
    const response = await apiClient.post<{ tools: DiscoveredMcpTool[] }>(
      `${this.toolBaseUrl}/mcp/discover`,
      payload,
    );
    return response.data.tools;
  }

  /**
   * Parse a pasted `mcpServers` JSON config (Claude Desktop / VS Code format)
   * into structured server entries, surfacing per-entry errors (e.g. rejected
   * stdio entries). Backend is the single source of truth for parsing.
   */
  async parseMcpServersJson(
    raw: string,
  ): Promise<ParsedMcpServersResult> {
    const response = await apiClient.post<ParsedMcpServersResult>(
      `${this.toolBaseUrl}/mcp/parse`,
      { raw },
    );
    return response.data;
  }

  /**
   * Create a platform_tools row (used for both curated-catalog additions by
   * platform admins and org-scoped custom MCP servers). Secret headers are
   * encrypted at rest by the backend; never send them back as plaintext.
   */
  async createPlatformTool(
    payload: Record<string, unknown>,
  ): Promise<PlatformTool> {
    const response = await apiClient.post<PlatformTool>(
      `${this.toolBaseUrl}/platform`,
      payload,
    );
    return response.data;
  }

  /**
   * Bootstrap a browser test call over Pipecat WebSocket transport.
   */
  async getTestToken(agentId: string): Promise<{
    transport: "pipecat";
    token: string;
    wsUrl: string;
    sessionId: string;
  }> {
    const response = await apiClient.post<{
      transport?: "pipecat";
      token: string;
      wsUrl: string;
      sessionId: string;
    }>(`${this.agentBaseUrl}/${agentId}/test-token`);
    const data = response.data;
    return {
      transport: data.transport ?? "pipecat",
      token: data.token,
      wsUrl: data.wsUrl,
      sessionId: data.sessionId,
    };
  }

  // Embed Configuration Methods
  async getEmbedConfig(
    agentId: string,
  ): Promise<EmbedConfig | null> {
    const response = await apiClient.get<EmbedConfigApiResponse | null>(
      `${this.agentBaseUrl}/${agentId}/embed-config`,
    );
    if (!response.data) return null;
    return transformEmbedConfigResponse(response.data);
  }

  async createEmbedConfig(
    agentId: string,
    configData: EmbedConfigCreate,
  ): Promise<EmbedConfig> {
    const response = await apiClient.post<EmbedConfigApiResponse>(
      `${this.agentBaseUrl}/${agentId}/embed-config`,
      transformEmbedConfigCreate(configData),
    );
    return transformEmbedConfigResponse(response.data);
  }

  async deleteEmbedConfig(agentId: string): Promise<void> {
    await apiClient.delete(`${this.agentBaseUrl}/${agentId}/embed-config`);
  }

  // Embed Token Method (for authenticated testing)
  async getEmbedToken(agentId: string): Promise<{
    embed_token: string;
    token: string;
    wsUrl: string;
    sessionId: string;
  }> {
    const response = await apiClient.post<{
      embed_token: string;
      token: string;
      wsUrl: string;
      sessionId: string;
    }>(`${this.agentBaseUrl}/${agentId}/embed-token`);
    return response.data;
  }
}

// Embed Configuration Types
export interface EmbedConfig {
  id: string;
  agentId: string;
  buttonText: string;
  buttonColor: string;
  buttonTextColor: string;
  buttonBorderRadius: number;
  buttonSize: 'small' | 'medium' | 'large';
  buttonPosition: 'bottom-right' | 'bottom-left' | 'bottom-center' | 'top-right' | 'top-left' | 'top-center' | 'center';
  buttonStyle?: 'filled' | 'outline';
  allowedDomains: string[] | null;
  customCss: string | null;
  isActive: boolean;
  dailyCallLimit: number;
  createdAt: string;
  updatedAt: string;
}

export interface EmbedConfigCreate {
  buttonText: string;
  buttonColor: string;
  buttonTextColor: string;
  buttonBorderRadius: number;
  buttonSize: 'small' | 'medium' | 'large';
  buttonPosition: 'bottom-right' | 'bottom-left' | 'bottom-center' | 'top-right' | 'top-left' | 'top-center' | 'center';
  buttonStyle?: 'filled' | 'outline';
  allowedDomains?: string[];
  customCss?: string;
  isActive: boolean;
  dailyCallLimit: number;
}

interface EmbedConfigApiResponse {
  id: string;
  agent_id: string;
  button_text: string;
  button_color: string;
  button_text_color: string;
  button_border_radius: number;
  button_size: string;
  button_position: string;
  button_style: string;
  allowed_domains: string[] | null;
  custom_css: string | null;
  is_active: boolean;
  daily_call_limit: number;
  created_at: string;
  updated_at: string;
}

function transformEmbedConfigResponse(data: EmbedConfigApiResponse): EmbedConfig {
  return {
    id: data.id,
    agentId: data.agent_id,
    buttonText: data.button_text,
    buttonColor: data.button_color,
    buttonTextColor: data.button_text_color,
    buttonBorderRadius: data.button_border_radius,
    buttonSize: data.button_size as EmbedConfig['buttonSize'],
    buttonPosition: data.button_position as EmbedConfig['buttonPosition'],
    buttonStyle: data.button_style as EmbedConfig['buttonStyle'],
    allowedDomains: data.allowed_domains,
    customCss: data.custom_css,
    isActive: data.is_active,
    dailyCallLimit: data.daily_call_limit,
    createdAt: data.created_at,
    updatedAt: data.updated_at,
  };
}

function transformEmbedConfigCreate(data: EmbedConfigCreate): Record<string, unknown> {
  return {
    button_text: data.buttonText,
    button_color: data.buttonColor,
    button_text_color: data.buttonTextColor,
    button_border_radius: data.buttonBorderRadius,
    button_size: data.buttonSize,
    button_position: data.buttonPosition,
    button_style: data.buttonStyle,
    allowed_domains: data.allowedDomains,
    custom_css: data.customCss,
    is_active: data.isActive,
    daily_call_limit: data.dailyCallLimit,
  };
}

export const agentService = new AgentService();
