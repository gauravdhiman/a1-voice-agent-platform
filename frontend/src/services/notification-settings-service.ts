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
  platform_admin_whatsapp_phone?: string | null;
  platform_admin_whatsapp_notifications_enabled: boolean;
  whatsapp_sender_configured: boolean;
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
  platform_admin_whatsapp_phone?: string | null;
  platform_admin_whatsapp_notifications_enabled?: boolean;
  verification_from_email?: string | null;
  verification_from_name?: string | null;
  telegram_chat_id?: string | null;
  telegram_notifications_enabled?: boolean;
  telegram_bot_token?: string | null;
}

export interface OrganizationNotificationSettings {
  organization_id: string;
  alert_email?: string | null;
  sms_phone?: string | null;
  telegram_chat_id?: string | null;
  telegram_bot_configured: boolean;
  updated_by?: string | null;
  created_at: string;
  updated_at: string;
}

export interface OrganizationNotificationSettingsUpdate {
  alert_email?: string | null;
  sms_phone?: string | null;
  telegram_chat_id?: string | null;
  telegram_bot_token?: string | null;
}

class NotificationSettingsService {
  private baseUrl = "/api/v1/notifications/admin/settings";

  /** Send one fixed test to the saved admin destination; provider acceptance requires receipt confirmation. */
  async testDelivery(channel: "email" | "telegram", organizationId?: string): Promise<{
    success: boolean; error?: string; data?: { status: "accepted"; message: string };
  }> {
    const url = organizationId
      ? `/api/v1/notifications/organizations/${encodeURIComponent(organizationId)}/settings/test`
      : `${this.baseUrl}/test`;
    try {
      const response = await apiClient.post<{ status: "accepted"; message: string }>(url, { channel });
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: error instanceof Error ? error.message : "Notification test failed." };
    }
  }

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

  async getOrganizationSettings(
    organizationId: string,
  ): Promise<{
    success: boolean;
    error?: string;
    data?: OrganizationNotificationSettings;
  }> {
    try {
      const response = await apiClient.get<OrganizationNotificationSettings>(
        `/api/v1/notifications/organizations/${encodeURIComponent(organizationId)}/settings`,
      );
      return { success: true, data: response.data };
    } catch (error) {
      return {
        success: false,
        error:
          error instanceof Error
            ? error.message
            : "Failed to load organization notification settings.",
      };
    }
  }

  async updateOrganizationSettings(
    organizationId: string,
    payload: OrganizationNotificationSettingsUpdate,
  ): Promise<{
    success: boolean;
    error?: string;
    data?: OrganizationNotificationSettings;
  }> {
    try {
      const response = await apiClient.put<OrganizationNotificationSettings>(
        `/api/v1/notifications/organizations/${encodeURIComponent(organizationId)}/settings`,
        payload,
      );
      return { success: true, data: response.data };
    } catch (error) {
      return {
        success: false,
        error:
          error instanceof Error
            ? error.message
            : "Failed to save organization notification settings.",
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
