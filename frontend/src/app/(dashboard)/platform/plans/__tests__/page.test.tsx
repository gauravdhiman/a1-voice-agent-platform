import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  replace: vi.fn(),
  search: "",
  hasRole: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  usePathname: () => "/platform/plans",
  useRouter: () => ({ replace: mocks.replace }),
  useSearchParams: () => new URLSearchParams(mocks.search),
}));

vi.mock("@/contexts/auth-context", () => ({
  useAuth: () => ({ user: { hasRole: mocks.hasRole } }),
}));

vi.mock("@/components/billing/platform-plans-manager", () => ({
  PlatformPlansManager: () => React.createElement("div", null, "Plans content"),
}));

vi.mock("@/components/billing/platform-entitlements-manager", () => ({
  PlatformEntitlementsManager: () =>
    React.createElement("div", null, "Entitlements content"),
}));

vi.mock("@/components/billing/platform-usage-pricing-manager", () => ({
  PlatformUsagePricingManager: () =>
    React.createElement("div", null, "Usage pricing content"),
}));

vi.mock("@/components/ui/access-denied", () => ({
  AccessDenied: () => React.createElement("div", null, "Access denied"),
}));

import PlatformPlansPage from "../page";

describe("/platform/plans tab navigation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.search = "";
    mocks.hasRole.mockReturnValue(true);
  });

  it("opens the tab named by the URL", () => {
    mocks.search = "tab=usage";

    render(<PlatformPlansPage />);

    expect(screen.getByText("Usage pricing content")).toBeInTheDocument();
    expect(screen.queryByText("Plans content")).not.toBeInTheDocument();
  });

  it("updates the URL when a different tab is selected", async () => {
    const user = userEvent.setup();
    render(<PlatformPlansPage />);

    await user.click(screen.getByRole("tab", { name: "Usage pricing" }));

    expect(mocks.replace).toHaveBeenCalledWith(
      "/platform/plans?tab=usage",
      { scroll: false },
    );
  });
});
