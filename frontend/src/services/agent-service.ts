// services/agent-service.ts
import { apiClient } from "@/lib/api/client";
import type {
  VoiceAgent,
  VoiceAgentCreate,
  VoiceAgentUpdate,
  PlatformTool,
  AgentTool,
  AgentToolCreate,
  AgentToolUpdate,
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
  async getPlatformTools(onlyActive = true): Promise<PlatformTool[]> {
    const response = await apiClient.get<PlatformTool[]>(
      `${this.toolBaseUrl}/platform?only_active=${onlyActive}`,
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

  // Test Token Methods
  async getTestToken(
    agentId: string,
  ): Promise<{ token: string; serverUrl: string; roomName: string }> {
    const response = await apiClient.post<{
      token: string;
      serverUrl: string;
      roomName: string;
    }>(`${this.agentBaseUrl}/${agentId}/test-token`);
    return response.data;
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
  async getEmbedToken(
    agentId: string,
  ): Promise<{ embedToken: string; livekitToken: string; serverUrl: string; roomName: string }> {
    const response = await apiClient.post<{
      embedToken: string;
      livekitToken: string;
      serverUrl: string;
      roomName: string;
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
