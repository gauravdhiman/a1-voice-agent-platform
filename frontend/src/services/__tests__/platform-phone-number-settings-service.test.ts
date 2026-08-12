import { beforeEach, describe, expect, it, vi } from "vitest";

const { apiClient } = vi.hoisted(() => ({
  apiClient: {
    get: vi.fn(),
    put: vi.fn(),
  },
}));

vi.mock("@/lib/api/client", () => ({ apiClient }));

import { platformPhoneNumberSettingsService } from "../platform-phone-number-settings-service";

describe("platformPhoneNumberSettingsService", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiClient.get.mockResolvedValue({ data: { billing_grace_period_days: 7 } });
    apiClient.put.mockResolvedValue({ data: { billing_grace_period_days: 14 } });
  });

  it("loads the platform-admin settings endpoint", async () => {
    const result = await platformPhoneNumberSettingsService.getSettings();

    expect(result.success).toBe(true);
    expect(apiClient.get).toHaveBeenCalledWith(
      "/api/v1/phone-numbers/admin/settings",
    );
  });

  it("updates the configured grace period and scheduler intervals", async () => {
    const result = await platformPhoneNumberSettingsService.updateSettings({
      billing_grace_period_days: 14,
      billing_check_interval_hours: 24,
      release_retry_interval_hours: 12,
    });

    expect(result.success).toBe(true);
    expect(apiClient.put).toHaveBeenCalledWith(
      "/api/v1/phone-numbers/admin/settings",
      {
        billing_grace_period_days: 14,
        billing_check_interval_hours: 24,
        release_retry_interval_hours: 12,
      },
    );
  });

  it("returns a safe error object when loading fails", async () => {
    apiClient.get.mockRejectedValue(new Error("network down"));

    await expect(
      platformPhoneNumberSettingsService.getSettings(),
    ).resolves.toEqual({ success: false, error: "network down" });
  });
});
