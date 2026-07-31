/**
 * Tests for the /organization page (settings-only, N1 redesign).
 *
 * Contract (mirrors the user-reported bug + the N1 follow-up #1 contract):
 *   - When the URL has `?org_id=...`, the page renders the org
 *     details for that org (after validating the user has access).
 *   - When the URL has no `?org_id=...`, the page falls back to
 *     `currentOrganization.id` from the org context. This is the
 *     fix for the user-reported bug: the sidebar nav links to bare
 *     `/organization` (no `?org_id=`), and the org admin should see
 *     the page, not "Access Denied".
 *   - When neither URL nor context provides an org, the page shows
 *     `AccessDenied` ("Organization ID Required").
 *   - When the user is not an org admin / platform admin, the page
 *     shows `AccessDenied` ("Access Denied").
 *   - When the URL `?org_id=` is for an org the user does not
 *     belong to, the page shows `AccessDenied` (failed validation).
 */
import React from "react";
import {
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import userEvent from "@testing-library/user-event";

// `vi.mock` is hoisted above the module body, so we use `vi.hoisted` to
// share state between the mock factories and the test cases.
const mocks = vi.hoisted(() => {
  const FIXTURE_ORG = {
    id: "org-1",
    name: "Acme",
    slug: "acme",
    description: "An org",
    website: null,
    is_active: true,
    onboarding_completed: true,
    industry: null,
    location: null,
    business_details: null,
    google_api_key: null,
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
  };
  const OTHER_ORG = { ...FIXTURE_ORG, id: "org-2", name: "Other" };
  // Per-test lookup table for the mocked organizationService.
  const mockOrgsById: Record<string, typeof FIXTURE_ORG> = {};
  return {
    FIXTURE_ORG,
    OTHER_ORG,
    mockOrgsById,
  };
});

const mockUseOrganization = vi.fn();
const mockUseUserPermissions = vi.fn();
const mockUseOrganizationById = vi.fn();
const mockUseAuth = vi.fn();
const mockPush = vi.fn();
const mockReplace = vi.fn();
const mockPrefetch = vi.fn();
const mockBack = vi.fn();

declare global {
  // eslint-disable-next-line no-var
  var __orgPageSearchParams: string | undefined;
}

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
    replace: mockReplace,
    prefetch: mockPrefetch,
    back: mockBack,
  }),
  useSearchParams: () =>
    new URLSearchParams(globalThis.__orgPageSearchParams ?? ""),
  usePathname: () => "/organization",
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

vi.mock("@/services/organization-service", () => ({
  organizationService: {
    getOrganizationById: vi.fn().mockImplementation((orgId: string) => {
      // mocks is in the closure; vi.hoisted guarantees it's defined.
      const org = mocks.mockOrgsById[orgId] ?? mocks.FIXTURE_ORG;
      return Promise.resolve(org);
    }),
    updateOrganization: vi.fn().mockResolvedValue(mocks.FIXTURE_ORG),
  },
}));

// Stub the edit dialog so we don't pull in the full dialog tree.
vi.mock("@/components/organizations/organization-edit-dialog", () => ({
  OrganizationEditDialog: () => null,
}));

import OrganizationPage from "../page";

const { FIXTURE_ORG, OTHER_ORG } = mocks;

function makeWrapper(queryClient: QueryClient) {
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(
      QueryClientProvider,
      { client: queryClient },
      children,
    );
}

describe("/organization page (N1 — fallback to currentOrganization)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    globalThis.__orgPageSearchParams = undefined;
    mocks.mockOrgsById["org-1"] = FIXTURE_ORG;
    mockUseAuth.mockReturnValue({
      user: { id: "user-1", roles: [] },
      isAuthenticated: true,
    });
    mockUseOrganization.mockReturnValue({
      organizations: [FIXTURE_ORG],
      currentOrganization: FIXTURE_ORG,
      setCurrentOrganization: vi.fn(),
      loading: false,
      error: null,
    });
    mockUseUserPermissions.mockReturnValue({
      isPlatformAdmin: false,
      isOrgAdmin: true,
      canUpdateOrganization: true,
      canViewMembers: true,
    });
    // useOrganizationById returns valid org for the requested id.
    mockUseOrganizationById.mockImplementation((orgId: string | null) => ({
      isValid: !!orgId,
      loading: false,
      error: null,
      organization: orgId ? FIXTURE_ORG : null,
    }));
  });

  afterEach(() => {
    delete globalThis.__orgPageSearchParams;
  });

  it("falls back to currentOrganization.id when ?org_id= is absent (user-reported bug fix)", async () => {
    // No ?org_id= in the URL — the page should use currentOrganization.id.
    mockUseOrganizationById.mockImplementation((orgId: string | null) => ({
      isValid: orgId === "org-1",
      loading: false,
      error: null,
      organization: orgId === "org-1" ? FIXTURE_ORG : null,
    }));

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(<OrganizationPage />, { wrapper: makeWrapper(queryClient) });

    // The page should call useOrganizationById with the fallback id.
    expect(mockUseOrganizationById).toHaveBeenCalledWith("org-1");

    // Wait for the page to finish loading and render the org name.
    // (Acme may appear in the H1, the slug, and the org-switcher label —
    // we just want to confirm the page actually rendered the org, not
    // the AccessDenied fallback.)
    await waitFor(() => {
      expect(screen.getAllByText("Acme").length).toBeGreaterThan(0);
    });
    // And the "Organization ID Required" AccessDenied title must NOT be present.
    expect(
      screen.queryByText(/organization id required/i),
    ).not.toBeInTheDocument();
  });

  it("uses ?org_id= when present, ignoring currentOrganization.id", async () => {
    globalThis.__orgPageSearchParams = "org_id=org-2";
    mocks.mockOrgsById["org-2"] = OTHER_ORG;
    mockUseOrganizationById.mockImplementation((orgId: string | null) => ({
      isValid: orgId === "org-2",
      loading: false,
      error: null,
      organization: orgId === "org-2" ? OTHER_ORG : null,
    }));

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(<OrganizationPage />, { wrapper: makeWrapper(queryClient) });

    expect(mockUseOrganizationById).toHaveBeenCalledWith("org-2");
    await waitFor(() => {
      expect(screen.getAllByText("Other").length).toBeGreaterThan(0);
    });
  });

  it("shows AccessDenied when neither ?org_id= nor currentOrganization provide an org", async () => {
    mockUseOrganization.mockReturnValue({
      organizations: [],
      currentOrganization: null,
      setCurrentOrganization: vi.fn(),
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

    render(<OrganizationPage />, { wrapper: makeWrapper(queryClient) });

    await waitFor(() => {
      expect(
        screen.getByText(/organization id required/i),
      ).toBeInTheDocument();
    });
  });

  it("shows AccessDenied when the user is not an org admin or platform admin", async () => {
    mockUseUserPermissions.mockReturnValue({
      isPlatformAdmin: false,
      isOrgAdmin: false,
      canUpdateOrganization: false,
      canViewMembers: false,
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(<OrganizationPage />, { wrapper: makeWrapper(queryClient) });

    await waitFor(() => {
      expect(screen.getByText(/access denied/i)).toBeInTheDocument();
    });
  });

  it("shows AccessDenied when ?org_id= is for an org the user does not belong to", async () => {
    globalThis.__orgPageSearchParams = "org_id=org-other";
    // useOrganizationById returns isValid: false for the unknown org.
    mockUseOrganizationById.mockImplementation((orgId: string | null) => ({
      isValid: false,
      loading: false,
      error: "Not found",
      organization: null,
    }));

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(<OrganizationPage />, { wrapper: makeWrapper(queryClient) });

    await waitFor(() => {
      expect(screen.getByText(/access denied/i)).toBeInTheDocument();
    });
  });

  it("renders the Organization Info + API Credentials tabs and defaults to info", async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(<OrganizationPage />, { wrapper: makeWrapper(queryClient) });

    await waitFor(() => {
      expect(screen.getAllByText("Acme").length).toBeGreaterThan(0);
    });

    // Both tabs are present.
    expect(
      screen.getByRole("tab", { name: /organization info/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("tab", { name: /api credentials/i }),
    ).toBeInTheDocument();

    // Info tab is active by default: its card title is in the document and the
    // credentials card title is not.
    expect(screen.getByText(/Organization Information/i)).toBeInTheDocument();
    expect(
      screen.queryByText(/Third-party API Credentials/i),
    ).not.toBeInTheDocument();
  });

  it("switches to the API Credentials tab on click and pushes ?tab=credentials", async () => {
    const user = userEvent.setup();
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(<OrganizationPage />, { wrapper: makeWrapper(queryClient) });

    await waitFor(() => {
      expect(screen.getAllByText("Acme").length).toBeGreaterThan(0);
    });

    // Credentials card title is NOT visible while the info tab is active.
    expect(
      screen.queryByText(/Third-party API Credentials/i),
    ).not.toBeInTheDocument();

    // userEvent simulates the full pointer + focus + click sequence; Radix
    // TabsTrigger activates on mouseDown (button 0) and on focus.
    await user.click(screen.getByRole("tab", { name: /api credentials/i }));

    // The credentials card title becomes visible (credentials TabsContent mounts).
    await waitFor(() => {
      expect(
        screen.getByText(/Third-party API Credentials/i),
      ).toBeInTheDocument();
    });
    // The info card title is no longer mounted (Radix unmounts inactive content).
    expect(
      screen.queryByText(/Organization Information/i),
    ).not.toBeInTheDocument();

    // The tab switch persists to ?tab=credentials.
    expect(mockPush).toHaveBeenCalledWith(
      expect.stringContaining("tab=credentials"),
      expect.objectContaining({ scroll: false }),
    );
  });

  it("does not surface a Google API Key field on the Organization Info tab (google is managed in the API Credentials tab)", async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(<OrganizationPage />, { wrapper: makeWrapper(queryClient) });

    await waitFor(() => {
      expect(screen.getAllByText("Acme").length).toBeGreaterThan(0);
    });

    // The Info tab is active by default (read mode). It must NOT show a Google
    // API Key field — google keys are configured exclusively under the
    // "API Credentials" tab now. The credentials TabsContent is unmounted while
    // the info tab is active, so this query targets the info card only.
    expect(screen.queryByText("Google API Key")).not.toBeInTheDocument();
    // And no Google API key <input> on the info tab either.
    expect(
      screen.queryByRole("textbox", { name: /google api key/i }),
    ).not.toBeInTheDocument();
  });

  it("deep-links to the credentials tab when ?tab=credentials is in the URL", async () => {
    globalThis.__orgPageSearchParams = "org_id=org-1&tab=credentials";
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(<OrganizationPage />, { wrapper: makeWrapper(queryClient) });

    // The credentials card title renders (info card title does not).
    await waitFor(() => {
      expect(
        screen.getByText(/Third-party API Credentials/i),
      ).toBeInTheDocument();
    });
    expect(
      screen.queryByText(/Organization Information/i),
    ).not.toBeInTheDocument();
  });

  it("shows Remove key for configured providers on the credentials tab", async () => {
    globalThis.__orgPageSearchParams = "org_id=org-1&tab=credentials";
    mocks.mockOrgsById["org-1"] = {
      ...FIXTURE_ORG,
      provider_credentials_status: { deepgram: true, openai: false },
    } as typeof FIXTURE_ORG & {
      provider_credentials_status: Record<string, boolean>;
    };
    mockUseOrganizationById.mockImplementation((orgId: string | null) => ({
      isValid: orgId === "org-1",
      loading: false,
      error: null,
      organization:
        orgId === "org-1"
          ? mocks.mockOrgsById["org-1"]
          : null,
    }));

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(<OrganizationPage />, { wrapper: makeWrapper(queryClient) });

    await waitFor(() => {
      expect(
        screen.getByText(/Third-party API Credentials/i),
      ).toBeInTheDocument();
    });

    expect(screen.getAllByText("Configured").length).toBeGreaterThan(0);
    expect(
      screen.getByRole("button", { name: /remove key/i }),
    ).toBeInTheDocument();
    expect(
      screen.getAllByRole("button", { name: /add api key/i }).length,
    ).toBeGreaterThan(0);
  });
});
