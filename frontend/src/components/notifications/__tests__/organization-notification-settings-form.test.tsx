import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
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
  telegram_chat_id: "-100123456789",
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

  it("explains critical notifications generally and derives channels from saved details", async () => {
    render(<OrganizationNotificationSettingsForm organizationId="org-1" />);

    expect(await screen.findByLabelText("Additional email address")).toBeTruthy();
    expect(
      screen.getByText(/important updates about your organization/i),
    ).toBeTruthy();
    expect(
      screen.queryByText(/OAuth connection recovery notices/i),
    ).toBeNull();
    expect(screen.queryByRole("switch")).toBeNull();
    expect(screen.getByLabelText("Additional email address")).toHaveProperty(
      "value",
      "ops@example.com",
    );
    expect(screen.getByLabelText("Phone number")).toHaveProperty(
      "value",
      "+15551234567",
    );
    expect(
      screen.getByText(/Clear the number to turn SMS off/i),
    ).toBeTruthy();
    expect(
      screen.getByText(/Both are required. Remove the saved bot token or clear/i),
    ).toBeTruthy();
    expect(mocks.getOrganizationSettings).toHaveBeenCalledWith("org-1");
  });

  it("saves organization-owned Telegram credentials without separate channel flags", async () => {
    const user = userEvent.setup();
    const token = "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi";
    const saved: OrganizationNotificationSettings = {
      ...SETTINGS,
      alert_email: "ops-team@example.com",
      sms_phone: "+15557654321",
      telegram_chat_id: "-100987654321",
      telegram_bot_configured: true,
    };
    mocks.updateOrganizationSettings.mockResolvedValue({ success: true, data: saved });
    render(<OrganizationNotificationSettingsForm organizationId="org-1" />);

    const email = await screen.findByLabelText("Additional email address");
    await user.clear(email);
    await user.type(email, "ops-team@example.com");
    const phone = screen.getByLabelText("Phone number");
    await user.clear(phone);
    await user.type(phone, "+15557654321");
    const chatId = screen.getByLabelText("Chat ID or channel username");
    await user.clear(chatId);
    await user.type(chatId, "-100987654321");
    await user.type(screen.getByLabelText("Telegram bot token"), token);
    await user.click(screen.getByRole("button", { name: "Save notification settings" }));

    await waitFor(() => {
      expect(mocks.updateOrganizationSettings).toHaveBeenCalledWith("org-1", {
        alert_email: "ops-team@example.com",
        sms_phone: "+15557654321",
        telegram_chat_id: "-100987654321",
        telegram_bot_token: token,
      });
    });
    expect(await screen.findByText("Notification settings saved.")).toBeTruthy();
    expect(screen.getByText("Token saved")).toBeTruthy();
    expect(screen.getByLabelText("Telegram bot token")).toHaveProperty(
      "value",
      "",
    );
  });

  it("removes a saved Telegram token only when the form is saved", async () => {
    const user = userEvent.setup();
    mocks.getOrganizationSettings.mockResolvedValue({
      success: true,
      data: { ...SETTINGS, telegram_bot_configured: true },
    });
    mocks.updateOrganizationSettings.mockResolvedValue({
      success: true,
      data: { ...SETTINGS, telegram_bot_configured: false },
    });
    render(<OrganizationNotificationSettingsForm organizationId="org-1" />);

    await user.click(
      await screen.findByRole("button", { name: "Remove saved token" }),
    );
    expect(
      screen.getByText("The saved token will be removed when you save."),
    ).toBeTruthy();
    expect(mocks.updateOrganizationSettings).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Save notification settings" }));

    await waitFor(() => {
      expect(mocks.updateOrganizationSettings).toHaveBeenCalledWith("org-1", {
        alert_email: "ops@example.com",
        sms_phone: "+15551234567",
        telegram_chat_id: "-100123456789",
        telegram_bot_token: null,
      });
    });
  });

  it("shows a loading error instead of an editable empty form", async () => {
    mocks.getOrganizationSettings.mockResolvedValue({
      success: false,
      error: "Access denied.",
    });
    render(<OrganizationNotificationSettingsForm organizationId="org-1" />);

    expect(await screen.findByText("Access denied.")).toBeTruthy();
    expect(screen.queryByLabelText("Additional email address")).toBeNull();
  });
});
