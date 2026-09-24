/**
 * Service for platform notification settings API.
 */

import { apiClient } from "@/lib/api/client";

export interface PlatformNotificationSettings {
  id: string;
  platform_admin_email?: string | null;
  platform_admin_sms_phone?: string | null;
  platform_admin_sms_notifications_enabled: boolean;
  sms_sender_configured: boolean;
  verification_from_email?: string | null;
  verification_from_name?: string | null;
  email_verification_active: boolean;
  telegram_chat_id?: string | null;
  telegram_notifications_enabled: boolean;
  telegram_bot_token_configured: boolean;
  telegram_bot_id?: string | null;
  updated_by?: string | null;
  created_at: string;
  updated_at: string;
}

export interface PlatformNotificationSettingsUpdate {
  platform_admin_email?: string | null;
  platform_admin_sms_phone?: string | null;
  platform_admin_sms_notifications_enabled?: boolean;
  verification_from_email?: string | null;
  verification_from_name?: string | null;
  telegram_chat_id?: string | null;
  telegram_notifications_enabled?: boolean;
  telegram_bot_token?: string | null;
}

class NotificationSettingsService {
  private baseUrl = "/api/v1/notifications/admin/settings";

  async getSettings(): Promise<{
    success: boolean;
    error?: string;
    data?: PlatformNotificationSettings;
  }> {
    try {
      const response =
        await apiClient.get<PlatformNotificationSettings>(this.baseUrl);
      return { success: true, data: response.data };
    } catch (error) {
      return {
        success: false,
        error:
          error instanceof Error ? error.message : "Failed to load settings.",
      };
    }
  }

  async updateSettings(
    payload: PlatformNotificationSettingsUpdate,
  ): Promise<{
    success: boolean;
    error?: string;
    data?: PlatformNotificationSettings;
  }> {
    try {
      const response = await apiClient.put<PlatformNotificationSettings>(
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

  async getHealth(): Promise<{
    success: boolean;
    error?: string;
    data?: { resend_configured: boolean; from_email?: string };
  }> {
    try {
      const response = await apiClient.get<{
        resend_configured: boolean;
        from_email?: string;
      }>("/api/v1/notifications/health");
      return { success: true, data: response.data };
    } catch (error) {
      return {
        success: false,
        error:
          error instanceof Error ? error.message : "Failed to load email health.",
      };
    }
  }
}

export const notificationSettingsService = new NotificationSettingsService();
