/** Platform-admin API service for write-only voice-provider credentials. */

import { apiClient } from "@/lib/api/client";
import type {
  PlatformVoiceProviderCredentialStatus,
  PlatformVoiceProviderCredentialsResponse,
  VoiceProviderKey,
} from "@/types/platform-voice-credentials";

class PlatformVoiceCredentialsService {
  private readonly baseUrl = "/api/v1/platform/api-credentials";

  /** Fetch stored-key and environment-fallback flags without secret values. */
  async getCredentials(): Promise<{
    success: boolean;
    error?: string;
    data?: PlatformVoiceProviderCredentialsResponse;
  }> {
    try {
      const response =
        await apiClient.get<PlatformVoiceProviderCredentialsResponse>(
          `${this.baseUrl}/`,
        );
      return { success: true, data: response.data };
    } catch (error) {
      return {
        success: false,
        error:
          error instanceof Error
            ? error.message
            : "Failed to load platform API credentials.",
      };
    }
  }

  /** Create or rotate a platform key; the server never returns its value. */
  async saveCredential(
    provider: VoiceProviderKey,
    apiKey: string,
  ): Promise<{
    success: boolean;
    error?: string;
    data?: PlatformVoiceProviderCredentialStatus;
  }> {
    try {
      const response =
        await apiClient.put<PlatformVoiceProviderCredentialStatus>(
          `${this.baseUrl}/${provider}`,
          { api_key: apiKey },
        );
      return { success: true, data: response.data };
    } catch (error) {
      return {
        success: false,
        error:
          error instanceof Error
            ? error.message
            : "Failed to save platform API credential.",
      };
    }
  }

  /** Remove the stored platform key for one provider. */
  async removeCredential(
    provider: VoiceProviderKey,
  ): Promise<{ success: boolean; error?: string }> {
    try {
      await apiClient.delete<void>(`${this.baseUrl}/${provider}`);
      return { success: true };
    } catch (error) {
      return {
        success: false,
        error:
          error instanceof Error
            ? error.message
            : "Failed to remove platform API credential.",
      };
    }
  }
}

export const platformVoiceCredentialsService =
  new PlatformVoiceCredentialsService();
