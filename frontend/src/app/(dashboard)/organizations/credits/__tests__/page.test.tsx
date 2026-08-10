/**
 * Tests for the platform-admin organization credits control page.
 *
 * Credit allocation belongs to platform operations, so this route must expose
 * the allocation control only to platform admins and only for a validated
 * organization selected from the platform organization directory.
 */
import React from "react";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockUseAuth = vi.fn();
const mockUseOrganizationById = vi.fn();
const mockUseCreditUsage = vi.fn();

declare global {
  // eslint-disable-next-line no-var
  var __platformCreditsSearchParams: string | undefined;
}

vi.mock("next/navigation", () => ({
  useSearchParams: () =>
    new URLSearchParams(globalThis.__platformCreditsSearchParams ?? ""),
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/organizations/credits",
}));

vi.mock("@/contexts/auth-context", () => ({
  useAuth: () => mockUseAuth(),
}));

vi.mock("@/hooks/use-organization-by-id", () => ({
  useOrganizationById: (...args: unknown[]) => mockUseOrganizationById(...args),
}));

vi.mock("@/hooks/use-credit-usage", () => ({
  useCreditUsage: (...args: unknown[]) => mockUseCreditUsage(...args),
}));

vi.mock("@/components/ui/access-denied", () => ({
  AccessDenied: ({
    title,
    description,
  }: {
    title: string;
    description: string;
  }) => (
    <div data-testid="access-denied">
      <span>{title}</span>
      <span>{description}</span>
    </div>
  ),
}));

vi.mock("@/components/billing/admin-credit-grant", () => ({
  AdminCreditGrant: ({ organizationId }: { organizationId: string }) => (
    <div data-testid="admin-credit-grant">Granting to {organizationId}</div>
  ),
}));

vi.mock("@/components/billing/credit-usage-panel", () => ({
  CreditUsagePanel: () => <div data-testid="credit-usage-panel" />,
}));

import PlatformOrganizationCreditsPage from "../page";

const ORGANIZATION = { id: "org-1", name: "Acme" };

describe("/organizations/credits page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    globalThis.__platformCreditsSearchParams = "org_id=org-1";
    mockUseAuth.mockReturnValue({
      user: { hasRole: (role: string) => role === "platform_admin" },
    });
    mockUseOrganizationById.mockReturnValue({
      isValid: true,
      loading: false,
      organization: ORGANIZATION,
    });
    mockUseCreditUsage.mockReturnValue({
      data: { balance: {}, transactions: [] },
      isLoading: false,
      error: null,
    });
  });

  it("shows organization context, reporting, and allocation for a platform admin", () => {
    render(<PlatformOrganizationCreditsPage />);

    expect(
      screen.getByRole("heading", { name: "Credits & entitlements" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/Acme/)).toBeInTheDocument();
    expect(screen.getByTestId("credit-usage-panel")).toBeInTheDocument();
    expect(screen.getByTestId("admin-credit-grant")).toHaveTextContent("org-1");
    expect(screen.queryByTestId("access-denied")).not.toBeInTheDocument();
  });

  it("denies an org admin and does not mount platform controls", () => {
    mockUseAuth.mockReturnValue({
      user: { hasRole: (role: string) => role === "org_admin" },
    });

    render(<PlatformOrganizationCreditsPage />);

    expect(screen.getByTestId("access-denied")).toBeInTheDocument();
    expect(screen.queryByTestId("admin-credit-grant")).not.toBeInTheDocument();
  });

  it("requires an organization id", () => {
    globalThis.__platformCreditsSearchParams = "";

    render(<PlatformOrganizationCreditsPage />);

    expect(screen.getByText("Organization ID Required")).toBeInTheDocument();
    expect(screen.queryByTestId("admin-credit-grant")).not.toBeInTheDocument();
  });

  it("denies an organization that cannot be validated", () => {
    mockUseOrganizationById.mockReturnValue({
      isValid: false,
      loading: false,
      organization: null,
    });

    render(<PlatformOrganizationCreditsPage />);

    expect(screen.getByTestId("access-denied")).toBeInTheDocument();
    expect(screen.queryByTestId("admin-credit-grant")).not.toBeInTheDocument();
  });
});
