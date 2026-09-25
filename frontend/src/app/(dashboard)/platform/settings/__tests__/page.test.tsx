import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

declare global {
  // eslint-disable-next-line no-var
  var __platformSettingsSearchParams: string | undefined;
}

const mocks = vi.hoisted(() => ({ platformAdmin: true }));

vi.mock("next/navigation", () => ({
  useSearchParams: () =>
    new URLSearchParams(globalThis.__platformSettingsSearchParams ?? ""),
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("@/contexts/auth-context", () => ({
  useAuth: () => ({
    user: {
      hasRole: (role: string) => role === "platform_admin" && mocks.platformAdmin,
    },
  }),
}));

vi.mock("@/components/notifications/platform-notification-settings-form", () => ({
  PlatformNotificationSettingsForm: () => <div>Notification settings form</div>,
}));

vi.mock("@/components/phone-numbers/platform-phone-number-settings-form", () => ({
  PlatformPhoneNumberSettingsForm: () => <div>Phone number settings form</div>,
}));

import PlatformSettingsPage from "../page";

beforeEach(() => {
  mocks.platformAdmin = true;
  globalThis.__platformSettingsSearchParams = undefined;
});

afterEach(() => {
  cleanup();
  delete globalThis.__platformSettingsSearchParams;
});

describe("platform settings hub", () => {
  it("shows notifications by default with links to all settings sections", () => {
    render(<PlatformSettingsPage />);

    expect(
      screen.getByRole("heading", { name: "Platform settings" }),
    ).toBeTruthy();
    expect(screen.getByText("Notification settings form")).toBeTruthy();
    expect(
      screen
        .getByRole("link", { name: /Notifications/ })
        .getAttribute("aria-current"),
    ).toBe("page");
    expect(
      screen
        .getByRole("link", { name: /Phone numbers/ })
        .getAttribute("href"),
    ).toContain("section=phone-numbers");
  });

  it("opens the phone-number section from its deep link", () => {
    globalThis.__platformSettingsSearchParams = "section=phone-numbers";

    render(<PlatformSettingsPage />);

    expect(screen.getByText("Phone number settings form")).toBeTruthy();
    expect(
      screen
        .getByRole("link", { name: /Phone numbers/ })
        .getAttribute("aria-current"),
    ).toBe("page");
  });

  it("denies access to users without the platform-admin role", () => {
    mocks.platformAdmin = false;

    render(<PlatformSettingsPage />);

    expect(screen.getByText(/Only platform administrators/)).toBeTruthy();
    expect(screen.queryByText("Notification settings form")).toBeNull();
  });
});
