import React from "react";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  hasRole: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  usePathname: () => "/platform/legal",
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(""),
}));

vi.mock("@/contexts/auth-context", () => ({
  useAuth: () => ({ user: { hasRole: mocks.hasRole } }),
}));

vi.mock("@/components/legal/legal-documents-manager", () => ({
  LegalDocumentsManager: () =>
    React.createElement("div", null, "Legal documents content"),
}));

vi.mock("@/components/ui/access-denied", () => ({
  AccessDenied: () => React.createElement("div", null, "Access denied"),
}));

import PlatformLegalPage from "../page";

describe("/platform/legal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.hasRole.mockReturnValue(true);
  });

  it("renders the legal documents manager for platform admins", () => {
    render(<PlatformLegalPage />);

    expect(screen.getByText("Legal Documents")).toBeTruthy();
    expect(screen.getByText("Legal documents content")).toBeTruthy();
    expect(screen.queryByText("Access denied")).toBeNull();
  });

  it("denies access to users without the platform_admin role", () => {
    mocks.hasRole.mockReturnValue(false);

    render(<PlatformLegalPage />);

    expect(screen.getByText("Access denied")).toBeTruthy();
    expect(screen.queryByText("Legal documents content")).toBeNull();
    expect(mocks.hasRole).toHaveBeenCalledWith("platform_admin");
  });
});
