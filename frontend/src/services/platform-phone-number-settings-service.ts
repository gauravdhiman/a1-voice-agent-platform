/**
 * Service for platform-admin phone-number lifecycle settings.
 */

import { apiClient } from "@/lib/api/client";

export interface PlatformPhoneNumberSettings {
  id: string;
  billing_grace_period_days: number;
  billing_check_interval_hours: number;
  release_retry_interval_hours: number;
  updated_by?: string | null;
  created_at: string;
  updated_at: string;
}

export interface PlatformPhoneNumberSettingsUpdate {
  billing_grace_period_days?: number;
  billing_check_interval_hours?: number;
  release_retry_interval_hours?: number;
}

class PlatformPhoneNumberSettingsService {
  private readonly baseUrl = "/api/v1/phone-numbers/admin/settings";

  /** Fetches the current platform-admin phone-number settings. */
  async getSettings(): Promise<{
    success: boolean;
    error?: string;
    data?: PlatformPhoneNumberSettings;
  }> {
    try {
      const response = await apiClient.get<PlatformPhoneNumberSettings>(
        this.baseUrl,
      );
      return { success: true, data: response.data };
    } catch (error) {
      return {
        success: false,
        error:
          error instanceof Error ? error.message : "Failed to load settings.",
      };
    }
  }

  /** Persists the supplied platform-admin settings. */
  async updateSettings(
    payload: PlatformPhoneNumberSettingsUpdate,
  ): Promise<{
    success: boolean;
    error?: string;
    data?: PlatformPhoneNumberSettings;
  }> {
    try {
      const response = await apiClient.put<PlatformPhoneNumberSettings>(
        this.baseUrl,
        payload,
      );
      return { success: true, data: response.data };
    } catch (error) {
      return {
        success: false,
        error:
          error instanceof Error ? error.message : "Failed to save settings.",
      };
    }
  }
}

export const platformPhoneNumberSettingsService =
  new PlatformPhoneNumberSettingsService();
