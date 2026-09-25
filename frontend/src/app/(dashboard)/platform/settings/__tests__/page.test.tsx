import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

declare global {
  // eslint-disable-next-line no-var
  var __platformSettingsSearchParams: string | undefined;
}

const mocks = vi.hoisted(() => ({
  platformAdmin: true,
  push: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useSearchParams: () =>
    new URLSearchParams(globalThis.__platformSettingsSearchParams ?? ""),
  useRouter: () => ({ push: mocks.push }),
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
  mocks.push.mockClear();
  globalThis.__platformSettingsSearchParams = undefined;
});

afterEach(() => {
  cleanup();
  delete globalThis.__platformSettingsSearchParams;
});

describe("platform settings hub", () => {
  it("shows horizontal settings tabs and notifications by default", () => {
    render(<PlatformSettingsPage />);

    expect(screen.getByRole("heading", { name: "Platform settings" })).toBeTruthy();
    expect(screen.getByText("Notification settings form")).toBeTruthy();
    expect(
      screen.getByRole("tab", { name: "Notifications" }).getAttribute("aria-selected"),
    ).toBe("true");
    expect(screen.getByRole("tab", { name: "Phone numbers" })).toBeTruthy();
    expect(screen.queryByRole("link", { name: /Notifications/ })).toBeNull();
  });

  it("opens the phone-number section from its deep link and persists tab selection", async () => {
    globalThis.__platformSettingsSearchParams = "section=phone-numbers";
    const user = userEvent.setup();
    render(<PlatformSettingsPage />);

    expect(screen.getByText("Phone number settings form")).toBeTruthy();
    expect(
      screen.getByRole("tab", { name: "Phone numbers" }).getAttribute("aria-selected"),
    ).toBe("true");

    await user.click(screen.getByRole("tab", { name: "Notifications" }));
    expect(screen.getByText("Notification settings form")).toBeTruthy();
    expect(mocks.push).toHaveBeenCalledWith(
      "/platform/settings?section=notifications",
      { scroll: false },
    );
  });

  it("denies access to users without the platform-admin role", () => {
    mocks.platformAdmin = false;

    render(<PlatformSettingsPage />);

    expect(screen.getByText(/Only platform administrators/)).toBeTruthy();
    expect(screen.queryByText("Notification settings form")).toBeNull();
  });
});
