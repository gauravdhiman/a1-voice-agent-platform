import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { OrganizationNotificationSettings } from "@/services/notification-settings-service";

const mocks = vi.hoisted(() => ({
  getOrganizationSettings: vi.fn(),
  updateOrganizationSettings: vi.fn(),
}));

vi.mock("@/services/notification-settings-service", () => ({
  notificationSettingsService: {
    getOrganizationSettings: mocks.getOrganizationSettings,
    updateOrganizationSettings: mocks.updateOrganizationSettings,
  },
}));

import { OrganizationNotificationSettingsForm } from "../organization-notification-settings-form";

const SETTINGS: OrganizationNotificationSettings = {
  organization_id: "org-1",
  alert_email: "ops@example.com",
  sms_phone: "+15551234567",
  sms_enabled: false,
  telegram_chat_id: "-100123456789",
  telegram_enabled: false,
  sms_sender_configured: true,
  telegram_bot_configured: false,
  updated_by: null,
  created_at: "2026-09-24T00:00:00Z",
  updated_at: "2026-09-24T00:00:00Z",
};

describe("OrganizationNotificationSettingsForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.getOrganizationSettings.mockResolvedValue({
      success: true,
      data: SETTINGS,
    });
    mocks.updateOrganizationSettings.mockResolvedValue({
      success: true,
      data: SETTINGS,
    });
  });

  it("loads saved destinations and makes provider readiness visible", async () => {
    render(<OrganizationNotificationSettingsForm organizationId="org-1" />);

    expect(await screen.findByLabelText("Additional alert email")).toBeTruthy();
    expect(screen.getByText("SMS provider ready")).toBeTruthy();
    expect(screen.getByText("Telegram bot not configured")).toBeTruthy();
    expect(screen.getByLabelText("Additional alert email")).toHaveProperty(
      "value",
      "ops@example.com",
    );
    expect(mocks.getOrganizationSettings).toHaveBeenCalledWith("org-1");
  });

  it("saves normalized destinations and channel choices", async () => {
    const user = userEvent.setup();
    const saved: OrganizationNotificationSettings = {
      ...SETTINGS,
      alert_email: "ops-team@example.com",
      sms_phone: "+15557654321",
      sms_enabled: true,
      telegram_chat_id: "-100987654321",
      telegram_enabled: true,
    };
    mocks.updateOrganizationSettings.mockResolvedValue({ success: true, data: saved });
    render(<OrganizationNotificationSettingsForm organizationId="org-1" />);

    const email = await screen.findByLabelText("Additional alert email");
    await user.clear(email);
    await user.type(email, " ops-team@example.com ");
    const phone = screen.getByLabelText("Phone number");
    await user.clear(phone);
    await user.type(phone, "+15557654321");
    await user.click(screen.getByLabelText("Enable SMS alerts"));
    const chatId = screen.getByLabelText("Chat ID or channel username");
    await user.clear(chatId);
    await user.type(chatId, "-100987654321");
    await user.click(screen.getByLabelText("Enable Telegram alerts"));
    await user.click(screen.getByRole("button", { name: "Save notification settings" }));

    await waitFor(() => {
      expect(mocks.updateOrganizationSettings).toHaveBeenCalledWith("org-1", {
        alert_email: "ops-team@example.com",
        sms_phone: "+15557654321",
        sms_enabled: true,
        telegram_chat_id: "-100987654321",
        telegram_enabled: true,
      });
    });
    expect(await screen.findByText("Organization notification settings saved.")).toBeTruthy();
  });

  it("prevents opting into a channel without a destination", async () => {
    const user = userEvent.setup();
    render(<OrganizationNotificationSettingsForm organizationId="org-1" />);

    await screen.findByLabelText("Additional alert email");
    const phone = screen.getByLabelText("Phone number");
    await user.clear(phone);
    await user.click(screen.getByLabelText("Enable SMS alerts"));
    fireEvent.click(screen.getByRole("button", { name: "Save notification settings" }));

    expect(await screen.findByText("Enter a phone number before enabling SMS alerts.")).toBeTruthy();
    expect(mocks.updateOrganizationSettings).not.toHaveBeenCalled();
  });

  it("shows a loading error instead of an editable empty form", async () => {
    mocks.getOrganizationSettings.mockResolvedValue({
      success: false,
      error: "Access denied.",
    });
    render(<OrganizationNotificationSettingsForm organizationId="org-1" />);

    expect(await screen.findByText("Access denied.")).toBeTruthy();
    expect(screen.queryByLabelText("Additional alert email")).toBeNull();
  });
});
