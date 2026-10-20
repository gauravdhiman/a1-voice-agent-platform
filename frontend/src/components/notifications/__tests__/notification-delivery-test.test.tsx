import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { notificationSettingsService } from "@/services/notification-settings-service";
import { NotificationDeliveryTest } from "../notification-delivery-test";

vi.mock("@/services/notification-settings-service", () => ({ notificationSettingsService: { testDelivery: vi.fn() } }));

describe("NotificationDeliveryTest", () => {
  beforeEach(() => vi.resetAllMocks());

  it("tests the platform saved email and asks for receipt confirmation", async () => {
    vi.mocked(notificationSettingsService.testDelivery).mockResolvedValue({ success: true, data: { status: "accepted", message: "Provider accepted the test. Confirm receipt." } });
    render(<NotificationDeliveryTest />);
    await userEvent.click(screen.getByRole("button", { name: "Send test email" }));
    expect(notificationSettingsService.testDelivery).toHaveBeenCalledWith("email", undefined);
    expect((await screen.findByRole("status")).textContent).toContain("Confirm receipt");
  });

  it("scopes Telegram to the organization and displays provider failure", async () => {
    vi.mocked(notificationSettingsService.testDelivery).mockResolvedValue({ success: false, error: "Provider unavailable" });
    render(<NotificationDeliveryTest organizationId="tenant-a" />);
    await userEvent.click(screen.getByRole("button", { name: "Send test Telegram" }));
    expect(notificationSettingsService.testDelivery).toHaveBeenCalledWith("telegram", "tenant-a");
    expect((await screen.findByRole("alert")).textContent).toBe("Provider unavailable");
    expect(screen.queryByRole("status")).toBeNull();
  });

  it("prevents duplicate tests while a provider request is pending", async () => {
    let finish: (result: { success: boolean; error: string }) => void = () => {};
    vi.mocked(notificationSettingsService.testDelivery).mockImplementation(() => new Promise(resolve => { finish = resolve; }));
    render(<NotificationDeliveryTest />);
    const button = screen.getByRole("button", { name: "Send test email" });
    await userEvent.click(button);
    await userEvent.click(button);
    expect(notificationSettingsService.testDelivery).toHaveBeenCalledTimes(1);
    finish({ success: false, error: "Retry later" });
    expect(await screen.findByRole("alert")).toBeTruthy();
  });
});
