import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { PlatformNotificationSettingsForm } from "@/components/notifications/platform-notification-settings-form";
import { notificationSettingsService } from "@/services/notification-settings-service";

vi.mock("@/services/notification-settings-service", () => ({
  notificationSettingsService: {
    getSettings: vi.fn(),
    getHealth: vi.fn(),
    updateSettings: vi.fn(),
  },
}));

const getSettingsMock = vi.mocked(notificationSettingsService.getSettings);
const getHealthMock = vi.mocked(notificationSettingsService.getHealth);
const updateSettingsMock = vi.mocked(notificationSettingsService.updateSettings);

const settings = {
  id: "00000000-0000-0000-0000-000000000001",
  platform_admin_email: "admin@example.com",
  platform_admin_sms_phone: null,
  platform_admin_sms_notifications_enabled: false,
  sms_sender_configured: true,
  verification_from_email: "noreply@example.com",
  verification_from_name: "24x7 AI",
  email_verification_active: true,
  telegram_chat_id: null,
  telegram_notifications_enabled: false,
  telegram_bot_token_configured: false,
  telegram_bot_id: null,
  updated_by: null,
  created_at: "2026-09-10T00:00:00Z",
  updated_at: "2026-09-10T00:00:00Z",
};

describe("PlatformNotificationSettingsForm", () => {
  beforeEach(() => {
    getSettingsMock.mockResolvedValue({ success: true, data: settings });
    getHealthMock.mockResolvedValue({
      success: true,
      data: { resend_configured: true, from_email: "noreply@example.com" },
    });
    updateSettingsMock.mockResolvedValue({ success: true, data: settings });
  });

  it("loads and saves the platform-admin lead recipient", async () => {
    const user = userEvent.setup();
    render(<PlatformNotificationSettingsForm />);

    const recipient = await screen.findByLabelText("Platform admin email");
    expect((recipient as HTMLInputElement).value).toBe("admin@example.com");

    await user.clear(recipient);
    await user.type(recipient, "leads@example.com");
    await user.click(screen.getByRole("button", { name: "Save settings" }));

    await waitFor(() => expect(updateSettingsMock).toHaveBeenCalled());
    expect(updateSettingsMock).toHaveBeenCalledWith(
      expect.objectContaining({ platform_admin_email: "leads@example.com" }),
    );
  });

  it("saves an opted-in platform SMS destination in E.164 form", async () => {
    const user = userEvent.setup();
    render(<PlatformNotificationSettingsForm />);

    const phone = await screen.findByLabelText("Platform admin phone");
    await user.type(phone, "+15551234567");
    await user.click(screen.getByRole("switch", { name: "Enable SMS OAuth alerts" }));
    await user.click(screen.getByRole("button", { name: "Save settings" }));

    await waitFor(() => expect(updateSettingsMock).toHaveBeenCalled());
    expect(updateSettingsMock).toHaveBeenCalledWith(
      expect.objectContaining({
        platform_admin_sms_phone: "+15551234567",
        platform_admin_sms_notifications_enabled: true,
      }),
    );
  });
});
