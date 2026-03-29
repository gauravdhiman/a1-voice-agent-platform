// services/voice-template-service.ts
import { apiClient } from "@/lib/api/client";
import type { VoiceTemplate } from "@/types/voice-template";

class VoiceTemplateService {
  private baseUrl = "/api/v1/voice-templates";

  async listTemplates(industry?: string): Promise<VoiceTemplate[]> {
    const params = industry ? `?industry=${encodeURIComponent(industry)}` : "";
    const response = await apiClient.get<VoiceTemplate[]>(`${this.baseUrl}${params}`);
    return response.data;
  }

  async getTemplate(templateId: string): Promise<VoiceTemplate> {
    const response = await apiClient.get<VoiceTemplate>(`${this.baseUrl}/${templateId}`);
    return response.data;
  }
}

export const voiceTemplateService = new VoiceTemplateService();
