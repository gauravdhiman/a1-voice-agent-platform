/**
 * Tests for the /organization/billing page (N1 nav bug fix + page-level gate).
 *
 * Contract (mirrors /organization and the user-reported bug):
 *   - When the URL has no `?org_id=`, the page falls back to
 *     `currentOrganization.id` from the org context. This is the
 *     fix for the user-reported bug: the sidebar nav links to bare
 *     `/organization/billing` (no `?org_id=`), and the org admin
 *     should see the page, not "Access Denied".
 *   - When the URL has `?org_id=...` for an org the user belongs
 *     to, the page renders the billing overview.
 *   - When neither URL nor context provides an org, the page
 *     shows AccessDenied ("Organization ID Required").
 *   - When `?org_id=` is for an org the user does NOT belong to,
 *     the page shows AccessDenied ("Access Denied").
 *   - A regular org member (not an admin) sees AccessDenied
 *     (CRIT frontend leak — billing controls include cancel/reactivate
 *     subscription, which only admins should touch).
 *   - The `setCurrentOrganization` side effect must NOT fire
 *     during render (it must be in a useEffect).
 */
import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => {
  const FIXTURE_ORG = {
    id: "org-1",
    name: "Acme",
    slug: "acme",
  };
  const OTHER_ORG = { ...FIXTURE_ORG, id: "org-2", name: "Other" };
  return { FIXTURE_ORG, OTHER_ORG };
});

const mockUseAuth = vi.fn();
const mockUseOrganization = vi.fn();
const mockUseUserPermissions = vi.fn();
const mockUseOrganizationById = vi.fn();
const mockUseBillingSummary = vi.fn();
const mockUseCreditUsage = vi.fn();
const mockSetCurrentOrganization = vi.fn();

declare global {
  // eslint-disable-next-line no-var
  var __orgBillingSearchParams: string | undefined;
}

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn(),
    back: vi.fn(),
  }),
  useSearchParams: () =>
    new URLSearchParams(globalThis.__orgBillingSearchParams ?? ""),
  usePathname: () => "/organization/billing",
  useParams: () => ({}),
}));

vi.mock("@/contexts/auth-context", () => ({
  useAuth: () => mockUseAuth(),
}));

vi.mock("@/contexts/organization-context", () => ({
  useOrganization: () => mockUseOrganization(),
}));

vi.mock("@/hooks/use-user-permissions", () => ({
  useUserPermissions: () => mockUseUserPermissions(),
}));

vi.mock("@/hooks/use-organization-by-id", () => ({
  useOrganizationById: (...args: unknown[]) => mockUseOrganizationById(...args),
}));

vi.mock("@/hooks/use-billing-summary", () => ({
  useBillingSummary: (...args: unknown[]) => mockUseBillingSummary(...args),
}));

vi.mock("@/hooks/use-credit-usage", () => ({
  useCreditUsage: (...args: unknown[]) => mockUseCreditUsage(...args),
}));

// Stub the heavy children — we just want to assert the gate.
vi.mock("@/components/billing/plan-selection", () => ({
  PlanSelection: () => <div data-testid="plan-selection" />,
}));

vi.mock("@/components/billing/credit-purchase", () => ({
  CreditPurchase: () => <div data-testid="credit-purchase" />,
}));

vi.mock("@/components/billing/admin-credit-grant", () => ({
  AdminCreditGrant: () => <div data-testid="admin-credit-grant" />,
}));

vi.mock("@/components/billing/subscription-management", () => ({
  SubscriptionManagement: () => <div data-testid="subscription-management" />,
}));

import BillingPage from "../page";

const { FIXTURE_ORG, OTHER_ORG } = mocks;

function makeWrapper(queryClient: QueryClient) {
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
}

describe("/organization/billing page (N1 — fallback + page-level admin gate)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    globalThis.__orgBillingSearchParams = undefined;
    mockUseAuth.mockReturnValue({
      user: { id: "user-1", roles: [] },
      isAuthenticated: true,
      loading: false,
    });
    mockUseOrganization.mockReturnValue({
      organizations: [FIXTURE_ORG],
      currentOrganization: FIXTURE_ORG,
      setCurrentOrganization: mockSetCurrentOrganization,
      loading: false,
      error: null,
    });
    mockUseUserPermissions.mockReturnValue({
      isPlatformAdmin: false,
      isOrgAdmin: true,
      canManageBilling: true,
    });
    mockUseOrganizationById.mockImplementation((orgId: string | null) => ({
      isValid: !!orgId,
      loading: false,
      error: null,
      organization: orgId ? FIXTURE_ORG : null,
    }));
    mockUseBillingSummary.mockReturnValue({
      data: {
        subscription: { status: "active", plan: { name: "Pro" } },
        credit_balance: 1000,
        next_billing_date: "2026-08-01",
        amount_due: 5000,
        current_period_usage: 200,
      },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
      isRefetching: false,
    });
    mockUseCreditUsage.mockReturnValue({
      data: null,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });
  });

  afterEach(() => {
    delete globalThis.__orgBillingSearchParams;
  });

  it("falls back to currentOrganization.id when ?org_id= is absent (user-reported bug fix)", async () => {
    mockUseOrganizationById.mockImplementation((orgId: string | null) => ({
      isValid: orgId === "org-1",
      loading: false,
      error: null,
      organization: orgId === "org-1" ? FIXTURE_ORG : null,
    }));

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(<BillingPage />, { wrapper: makeWrapper(queryClient) });

    expect(mockUseOrganizationById).toHaveBeenCalledWith("org-1");
    expect(mockUseBillingSummary).toHaveBeenCalledWith("org-1");

    // The page header should be "Billing & Subscriptions".
    await waitFor(() => {
      expect(screen.getByText(/Billing & Subscriptions/i)).toBeInTheDocument();
    });
    expect(
      screen.queryByText(/organization id required/i),
    ).not.toBeInTheDocument();
  });

  it("uses ?org_id= when present, ignoring currentOrganization.id", async () => {
    globalThis.__orgBillingSearchParams = "org_id=org-2";
    mockUseOrganizationById.mockImplementation((orgId: string | null) => ({
      isValid: orgId === "org-2",
      loading: false,
      error: null,
      organization: orgId === "org-2" ? OTHER_ORG : null,
    }));

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(<BillingPage />, { wrapper: makeWrapper(queryClient) });

    expect(mockUseOrganizationById).toHaveBeenCalledWith("org-2");
    expect(mockUseBillingSummary).toHaveBeenCalledWith("org-2");
  });

  it("shows AccessDenied when neither ?org_id= nor currentOrganization provide an org", async () => {
    mockUseOrganization.mockReturnValue({
      organizations: [],
      currentOrganization: null,
      setCurrentOrganization: mockSetCurrentOrganization,
      loading: false,
      error: null,
    });
    mockUseOrganizationById.mockImplementation((orgId: string | null) => ({
      isValid: false,
      loading: false,
      error: null,
      organization: null,
    }));

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(<BillingPage />, { wrapper: makeWrapper(queryClient) });

    await waitFor(() => {
      expect(screen.getByText(/organization id required/i)).toBeInTheDocument();
    });
  });

  it("shows AccessDenied when ?org_id= is for an org the user does not belong to", async () => {
    globalThis.__orgBillingSearchParams = "org_id=org-other";
    mockUseOrganizationById.mockImplementation((orgId: string | null) => ({
      isValid: false,
      loading: false,
      error: "Not found",
      organization: null,
    }));

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(<BillingPage />, { wrapper: makeWrapper(queryClient) });

    await waitFor(() => {
      expect(screen.getByText(/access denied/i)).toBeInTheDocument();
    });
  });

  it("shows AccessDenied when the user is not an org admin or platform admin (CRIT)", async () => {
    // Regular org member — must not see the billing page (the page
    // contains PlanSelection / CreditPurchase / SubscriptionManagement
    // which can cancel/reactivate the org's subscription).
    mockUseUserPermissions.mockReturnValue({
      isPlatformAdmin: false,
      isOrgAdmin: false,
      canManageBilling: false,
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(<BillingPage />, { wrapper: makeWrapper(queryClient) });

    await waitFor(() => {
      expect(screen.getByText(/access denied/i)).toBeInTheDocument();
    });
  });

  it("platform admin can see billing reporting without platform allocation controls", async () => {
    globalThis.__orgBillingSearchParams = "tab=credits";
    mockUseUserPermissions.mockReturnValue({
      isPlatformAdmin: true,
      isOrgAdmin: false,
      canManageBilling: true,
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(<BillingPage />, { wrapper: makeWrapper(queryClient) });

    await waitFor(() => {
      expect(screen.getByText(/Billing & Subscriptions/i)).toBeInTheDocument();
    });
    expect(screen.queryByTestId("admin-credit-grant")).not.toBeInTheDocument();
  });

  it("does not expose platform credit allocation to organization admins", async () => {
    globalThis.__orgBillingSearchParams = "tab=credits";
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(<BillingPage />, { wrapper: makeWrapper(queryClient) });

    await waitFor(() => {
      expect(screen.getByText(/Billing & Subscriptions/i)).toBeInTheDocument();
    });
    expect(screen.queryByTestId("admin-credit-grant")).not.toBeInTheDocument();
  });

  it("orders the useful billing tabs with Overview first", async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(<BillingPage />, { wrapper: makeWrapper(queryClient) });

    await waitFor(() => {
      expect(screen.getAllByRole("tab").map((tab) => tab.textContent)).toEqual([
        "Overview",
        "Plans",
        "Credits",
      ]);
    });
    expect(screen.getByRole("tab", { name: "Overview" })).toHaveAttribute(
      "data-state",
      "active",
    );
  });

  it("shows the active free plan instead of falling back to no plan", async () => {
    mockUseBillingSummary.mockReturnValue({
      data: {
        subscription: {
          status: "active",
          plan: null,
          metadata: { billing_mode: "free" },
        },
        credit_balance: 1000,
        next_billing_date: "2026-08-01",
        amount_due: null,
        current_period_usage: 200,
      },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
      isRefetching: false,
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(<BillingPage />, { wrapper: makeWrapper(queryClient) });

    await waitFor(() => {
      expect(screen.getByText("Free plan")).toBeInTheDocument();
    });
    expect(screen.queryByText("No Plan")).not.toBeInTheDocument();
  });
});
