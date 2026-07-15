/**
 * Tests for the top-level /phone-numbers page.
 *
 * Contract (mirrors docs/tw-drafts/navigation-redesign.md Section 6.5):
 *   - The page renders the existing PhoneNumberDashboard component.
 *   - The component receives the current orgId (from the `?org_id=...`
 *     search param, falling back to the currentOrganization from context).
 *   - Loading and error states match the embedded version (the dashboard
 *     is a controlled component, so the page owns the fetch).
 *   - The dashboard receives `canManage={canManagePhoneNumbers}`
 *     — a regular member gets `canManage=false` so the per-card write
 *     buttons don't render (N1 #2 follow-up).
 */
import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// `useSearchParams` returns a URLSearchParams parsed from this global
// string. Tests set/clear it to drive the URL state without needing a
// real router.
declare global {
  // eslint-disable-next-line no-var
  var __pnSearchParams: string | undefined;
}

const mockUseOrganization = vi.fn();
const mockUseUserPermissions = vi.fn();
const mockGetOrganizationNumbers = vi.fn();
const mockGetCreditBalance = vi.fn();
const mockPush = vi.fn();
const mockReplace = vi.fn();

// Record the props the page passes to <PhoneNumberDashboard> so the
// test can assert the `canManage` wire-up without having to render
// the dashboard's full child tree.
const mockDashboardProps: Record<string, unknown> = {};

vi.mock("@/contexts/organization-context", () => ({
  useOrganization: () => mockUseOrganization(),
}));

vi.mock("@/hooks/use-user-permissions", () => ({
  useUserPermissions: () => mockUseUserPermissions(),
}));

vi.mock("@/services/phone-number-service", () => ({
  phoneNumberService: {
    getOrganizationNumbers: (...args: unknown[]) =>
      mockGetOrganizationNumbers(...args),
  },
}));

vi.mock("@/services/billing-service", () => ({
  billingService: {
    getCreditBalance: (...args: unknown[]) => mockGetCreditBalance(...args),
  },
}));

vi.mock("@/components/phone-numbers/phone-number-dashboard", () => ({
  PhoneNumberDashboard: (props: Record<string, unknown>) => {
    Object.assign(mockDashboardProps, props);
    return <div data-testid="phone-number-dashboard" />;
  },
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
    replace: mockReplace,
    prefetch: vi.fn(),
    back: vi.fn(),
  }),
  useSearchParams: () => new URLSearchParams(globalThis.__pnSearchParams ?? ""),
  usePathname: () => "/phone-numbers",
}));

import PhoneNumbersPage from "../page";

describe("/phone-numbers page (N1)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Object.keys(mockDashboardProps).forEach(
      (k) => delete mockDashboardProps[k],
    );
    globalThis.__pnSearchParams = "org_id=org-1";
    mockUseOrganization.mockReturnValue({
      organizations: [],
      currentOrganization: null,
      setCurrentOrganization: vi.fn(),
    });
    mockUseUserPermissions.mockReturnValue({
      canManagePhoneNumbers: true,
      isPlatformAdmin: false,
      isOrgAdmin: true,
    });
    mockGetOrganizationNumbers.mockResolvedValue({ items: [] });
    mockGetCreditBalance.mockResolvedValue({ total_credits: 0 });
  });

  afterEach(() => {
    delete globalThis.__pnSearchParams;
  });

  it("fetches and renders the dashboard for the given org", async () => {
    render(<PhoneNumbersPage />);

    await waitFor(() =>
      expect(mockGetOrganizationNumbers).toHaveBeenCalledWith("org-1"),
    );
  });

  it("uses the currentOrganization from context when ?org_id is missing", async () => {
    delete globalThis.__pnSearchParams;
    mockUseOrganization.mockReturnValue({
      organizations: [],
      currentOrganization: {
        id: "org-from-ctx",
        name: "Acme",
        slug: "acme",
        description: null,
        website: null,
        is_active: true,
        onboarding_completed: true,
        created_at: "",
        updated_at: "",
      },
      setCurrentOrganization: vi.fn(),
    });

    render(<PhoneNumbersPage />);

    await waitFor(() =>
      expect(mockGetOrganizationNumbers).toHaveBeenCalledWith("org-from-ctx"),
    );
  });

  it("shows a 'no org selected' state when no org id is available", () => {
    delete globalThis.__pnSearchParams;
    mockUseOrganization.mockReturnValue({
      organizations: [],
      currentOrganization: null,
      setCurrentOrganization: vi.fn(),
    });

    render(<PhoneNumbersPage />);

    // The page must NOT call the service when there's no org to scope to.
    expect(mockGetOrganizationNumbers).not.toHaveBeenCalled();
    // And it must tell the user why nothing is showing.
    expect(
      screen.getByText(/select an organization/i),
    ).toBeInTheDocument();
  });

  it("passes canManage=true to the dashboard for an org admin (N1 #2)", async () => {
    mockUseUserPermissions.mockReturnValue({
      canManagePhoneNumbers: true,
      isPlatformAdmin: false,
      isOrgAdmin: true,
    });

    render(<PhoneNumbersPage />);

    await waitFor(() => {
      expect(
        screen.getByTestId("phone-number-dashboard"),
      ).toBeInTheDocument();
    });
    expect(mockDashboardProps.canManage).toBe(true);
  });

  it("passes canManage=true to the dashboard for a platform admin", async () => {
    mockUseUserPermissions.mockReturnValue({
      canManagePhoneNumbers: true,
      isPlatformAdmin: true,
      isOrgAdmin: false,
    });

    render(<PhoneNumbersPage />);

    await waitFor(() => {
      expect(
        screen.getByTestId("phone-number-dashboard"),
      ).toBeInTheDocument();
    });
    expect(mockDashboardProps.canManage).toBe(true);
  });

  it("passes canManage=false to the dashboard for a regular org member (N1 #2 — CRIT)", async () => {
    mockUseUserPermissions.mockReturnValue({
      canManagePhoneNumbers: false,
      isPlatformAdmin: false,
      isOrgAdmin: false,
    });

    render(<PhoneNumbersPage />);

    await waitFor(() => {
      expect(
        screen.getByTestId("phone-number-dashboard"),
      ).toBeInTheDocument();
    });
    // The page is the strict gate — the regular member must NOT see
    // the dashboard's write buttons.
    expect(mockDashboardProps.canManage).toBe(false);
  });
});
