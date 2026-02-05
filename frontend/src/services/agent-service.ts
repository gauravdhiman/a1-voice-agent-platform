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
}

export const agentService = new AgentService();
