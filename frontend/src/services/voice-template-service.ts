// services/voice-template-service.ts
import { apiClient } from "@/lib/api/client";
import type {
  VoiceTemplate,
  VoiceTemplateInput,
  VoiceTemplateUpdate,
} from "@/types/voice-template";

/**
 * Service for the reusable voice-template catalog.
 *
 * Public methods intentionally return active templates only, which keeps the
 * existing agent create/edit insertion flow unchanged. Admin methods use a
 * separate platform endpoint and are only exposed on the platform-admin page;
 * the backend enforces the same role independently.
 */
class VoiceTemplateService {
  private baseUrl = "/api/v1/voice-templates";
  private platformBaseUrl = "/api/v1/platform/voice-templates";

  /** Fetch active templates for onboarding or agent editing. */
  async listTemplates(industry?: string): Promise<VoiceTemplate[]> {
    const params = industry ? `?industry=${encodeURIComponent(industry)}` : "";
    const response = await apiClient.get<VoiceTemplate[]>(`${this.baseUrl}${params}`);
    return response.data;
  }

  /** Fetch one active template for a public selection surface. */
  async getTemplate(templateId: string): Promise<VoiceTemplate> {
    const response = await apiClient.get<VoiceTemplate>(`${this.baseUrl}/${templateId}`);
    return response.data;
  }

  /** Fetch active and inactive templates for platform-admin management. */
  async listAdminTemplates(): Promise<VoiceTemplate[]> {
    const response = await apiClient.get<VoiceTemplate[]>(
      `${this.platformBaseUrl}/`,
    );
    return response.data;
  }

  /** Create a platform-managed template. */
  async createTemplate(payload: VoiceTemplateInput): Promise<VoiceTemplate> {
    const response = await apiClient.post<VoiceTemplate>(
      `${this.platformBaseUrl}/`,
      payload,
    );
    return response.data;
  }

  /** Update a platform-managed template by id. */
  async updateTemplate(
    templateId: string,
    payload: VoiceTemplateUpdate,
  ): Promise<VoiceTemplate> {
    const response = await apiClient.put<VoiceTemplate>(
      `${this.platformBaseUrl}/${templateId}`,
      payload,
    );
    return response.data;
  }

  /** Permanently delete a platform-managed template by id. */
  async deleteTemplate(templateId: string): Promise<void> {
    await apiClient.delete(`${this.platformBaseUrl}/${templateId}`);
  }
}

export const voiceTemplateService = new VoiceTemplateService();
