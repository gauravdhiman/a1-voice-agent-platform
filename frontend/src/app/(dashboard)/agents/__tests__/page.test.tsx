/**
 * Tests for the /agents page (permission-aware New Agent button + cards).
 *
 * Contract (mirrors the N1 permission-aware-UI follow-up; see
 * `docs/tw-drafts/navigation-redesign.md` Section 6.5 + the user
 * feedback that "actions like deleting a skill ... should respect
 * the permissions of the user's role"):
 *
 *   - The "New Agent" button is gated on the user being an org admin
 *     OR platform admin (i.e. canCreate === isPlatformAdmin || isOrgAdmin).
 *     A regular org member with workspace permissions only does not
 *     see the button.
 *   - The "Create Your First Agent" empty-state button is gated on
 *     the same flag (regular members see a "no agents found" state
 *     but no create CTA).
 *   - Every <AgentCard> receives `canDelete` matching the page-level
 *     permission (regular members: false, admins: true).
 *
 * Organization scope contract:
 *   - Organization users load and see only agents for the active
 *     organization selected in the organization switcher.
 *   - Platform admins retain the cross-organization list and filter.
 *   - The page still applies a client-side scope check as defense in depth;
 *     the organization-scoped API remains the authorization boundary.
 */
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mockUseOrganization = vi.fn();
const mockUseUserPermissions = vi.fn();
const mockUseMyAgents = vi.fn();
const mockUseOrgAgents = vi.fn();
const mockUseDeleteAgent = vi.fn();
const mockUseSearchParams = vi.fn();
const mockPush = vi.fn();
// `mockUseAuth` returns a user object whose `hasRole(role, orgId?)` is
// mocked per-test. By default it returns `false` for every role. Tests
// override it with `mockHasRole.mockImplementation(...)` to model
// specific user → org role grants.
const mockHasRole = vi.fn().mockReturnValue(false);
const mockUseAuth = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
    replace: vi.fn(),
    prefetch: vi.fn(),
    back: vi.fn(),
  }),
  useSearchParams: () => mockUseSearchParams(),
  usePathname: () => "/agents",
  useParams: () => ({}),
}));

vi.mock("@/contexts/organization-context", () => ({
  useOrganization: () => mockUseOrganization(),
}));

vi.mock("@/contexts/auth-context", () => ({
  useAuth: () => mockUseAuth(),
}));

vi.mock("@/hooks/use-user-permissions", () => ({
  useUserPermissions: () => mockUseUserPermissions(),
}));

vi.mock("@/hooks/use-agent-queries", () => ({
  useMyAgents: (enabled?: boolean) => mockUseMyAgents(enabled),
  useOrgAgents: (orgId: string) => mockUseOrgAgents(orgId),
  useDeleteAgent: () => mockUseDeleteAgent(),
}));

import AgentsPage from "../page";

const FIXTURE_AGENT = {
  id: "agent-1",
  organization_id: "org-1",
  name: "Fixture Agent",
  is_active: true,
  phone_number: "+15555550100",
  system_prompt: "You are a fixture.",
};

// Second agent in a different org — used by the per-agent canDelete
// tests to assert that a page-level canDelete would have been wrong
// (an org admin on org-1 must not be able to delete this org-2 agent).
const FIXTURE_AGENT_OTHER_ORG = {
  id: "agent-2",
  organization_id: "org-2",
  name: "Other Org Agent",
  is_active: true,
  phone_number: "+15555550200",
  system_prompt: "You are in another org.",
};

function makeWrapper(queryClient: QueryClient) {
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(
      QueryClientProvider,
      { client: queryClient },
      children,
    );
}

describe("/agents page (N1 permission-aware UI)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default `useAuth` user: holds `org_admin` on the current org
    // (org-1). The per-agent canActOnAgent check needs a real
    // user.hasRole to compute per-agent flags. Tests that exercise
    // a different role shape override `mockHasRole` directly.
    mockHasRole.mockReset().mockImplementation(
      (role: string, orgId?: string) =>
        role === "org_admin" && orgId === "org-1",
    );
    mockUseAuth.mockReturnValue({ user: { hasRole: mockHasRole } });
    mockUseOrganization.mockReturnValue({
      organizations: [{ id: "org-1", name: "Acme" }],
      currentOrganization: { id: "org-1", name: "Acme" },
      loading: false,
    });
    // Default: org admin (matches the original tests' expectations
    // for the 'New Agent' button + per-card trash/Edit/Tools icons).
    // The per-agent tests override `mockHasRole` directly.
    mockUseUserPermissions.mockReturnValue({
      canCreateAgent: true,
      isPlatformAdmin: false,
      isOrgAdmin: true,
    });
    mockUseSearchParams.mockReturnValue({
      get: vi.fn().mockReturnValue(null),
    });
    mockUseDeleteAgent.mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue(undefined),
    });
    mockUseOrgAgents.mockImplementation(() => mockUseMyAgents());
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders the 'New Agent' button for an org admin", () => {
    mockUseUserPermissions.mockReturnValue({
      canCreateAgent: true,
      isPlatformAdmin: false,
      isOrgAdmin: true,
    });
    mockUseMyAgents.mockReturnValue({
      data: [FIXTURE_AGENT],
      isLoading: false,
      error: null,
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(<AgentsPage />, { wrapper: makeWrapper(queryClient) });

    expect(
      screen.getByRole("button", { name: /new agent/i }),
      "org admin must see the 'New Agent' button",
    ).toBeInTheDocument();
  });

  it("renders the 'New Agent' button for a platform admin", () => {
    mockHasRole.mockImplementation((role: string) => role === "platform_admin");
    mockUseUserPermissions.mockReturnValue({
      canCreateAgent: true,
      isPlatformAdmin: true,
      isOrgAdmin: false,
    });
    mockUseMyAgents.mockReturnValue({
      data: [FIXTURE_AGENT],
      isLoading: false,
      error: null,
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(<AgentsPage />, { wrapper: makeWrapper(queryClient) });

    expect(mockUseMyAgents).toHaveBeenCalledWith(true);
    expect(
      screen.getByRole("button", { name: /new agent/i }),
    ).toBeInTheDocument();
  });

  it("loads the active organization for org users and hides out-of-scope agents", () => {
    mockUseUserPermissions.mockReturnValue({
      canCreateAgent: true,
      isPlatformAdmin: false,
      isOrgAdmin: true,
    });
    mockUseMyAgents.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    });
    mockUseOrgAgents.mockReturnValue({
      data: [FIXTURE_AGENT, FIXTURE_AGENT_OTHER_ORG],
      isLoading: false,
      error: null,
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(<AgentsPage />, { wrapper: makeWrapper(queryClient) });

    expect(mockUseOrgAgents).toHaveBeenCalledWith("org-1");
    expect(mockUseMyAgents).toHaveBeenCalledWith(false);
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
    expect(screen.getByText("Fixture Agent")).toBeInTheDocument();
    expect(screen.queryByText("Other Org Agent")).not.toBeInTheDocument();
  });

  it("keeps a platform admin cross-organization even without an active org", () => {
    mockHasRole.mockImplementation((role: string) => role === "platform_admin");
    mockUseOrganization.mockReturnValue({
      organizations: [],
      currentOrganization: null,
      loading: false,
    });
    mockUseUserPermissions.mockReturnValue({
      canCreateAgent: false,
      isPlatformAdmin: false,
      isOrgAdmin: false,
    });
    mockUseMyAgents.mockReturnValue({
      data: [FIXTURE_AGENT_OTHER_ORG],
      isLoading: false,
      error: null,
    });
    mockUseOrgAgents.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(<AgentsPage />, { wrapper: makeWrapper(queryClient) });

    expect(mockUseMyAgents).toHaveBeenCalledWith(true);
    expect(screen.getByText("Other Org Agent")).toBeInTheDocument();
  });

  it("does NOT render the 'New Agent' button for a regular org member", () => {
    mockUseUserPermissions.mockReturnValue({
      canCreateAgent: false,
      isPlatformAdmin: false,
      isOrgAdmin: false,
    });
    mockUseMyAgents.mockReturnValue({
      data: [FIXTURE_AGENT],
      isLoading: false,
      error: null,
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(<AgentsPage />, { wrapper: makeWrapper(queryClient) });

    expect(
      screen.queryByRole("button", { name: /new agent/i }),
      "regular member must not see the 'New Agent' button",
    ).not.toBeInTheDocument();
  });

  it("does NOT render the empty-state 'Create Your First Agent' button for a regular member", () => {
    mockUseUserPermissions.mockReturnValue({
      canCreateAgent: false,
      isPlatformAdmin: false,
      isOrgAdmin: false,
    });
    mockUseMyAgents.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(<AgentsPage />, { wrapper: makeWrapper(queryClient) });

    expect(
      screen.queryByRole("button", { name: /create your first agent/i }),
      "regular member must not see the empty-state create CTA",
    ).not.toBeInTheDocument();
  });

  it("renders the empty-state 'Create Your First Agent' button for an org admin", () => {
    mockUseUserPermissions.mockReturnValue({
      canCreateAgent: true,
      isPlatformAdmin: false,
      isOrgAdmin: true,
    });
    mockUseMyAgents.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(<AgentsPage />, { wrapper: makeWrapper(queryClient) });

    expect(
      screen.getByRole("button", { name: /create your first agent/i }),
    ).toBeInTheDocument();
  });

  it("regular member does NOT see any AgentCard with a trash icon (canDelete=false)", () => {
    // The AgentCard now accepts canDelete. The page must pass
    // canDelete={false} for a regular member so the trash icon is
    // not rendered. This is the contract the page-level wire-up
    // enforces.
    mockUseUserPermissions.mockReturnValue({
      canCreateAgent: false,
      isPlatformAdmin: false,
      isOrgAdmin: false,
    });
    // A regular member has no admin role on any org.
    mockHasRole.mockReset().mockReturnValue(false);
    mockUseMyAgents.mockReturnValue({
      data: [FIXTURE_AGENT],
      isLoading: false,
      error: null,
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(<AgentsPage />, { wrapper: makeWrapper(queryClient) });

    // The card shows the agent name; assert it is present.
    expect(screen.getByText("Fixture Agent")).toBeInTheDocument();

    // No trash icon (lucide-react's Trash2 SVG) should be present.
    const trashIcons = document.querySelectorAll("svg.lucide-trash2");
    expect(
      trashIcons.length,
      "regular member must not see any per-card trash icon",
    ).toBe(0);
  });

  it("org admin DOES see AgentCards with a trash icon (canDelete=true)", () => {
    mockUseUserPermissions.mockReturnValue({
      canCreateAgent: true,
      isPlatformAdmin: false,
      isOrgAdmin: true,
    });
    mockUseMyAgents.mockReturnValue({
      data: [FIXTURE_AGENT],
      isLoading: false,
      error: null,
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(<AgentsPage />, { wrapper: makeWrapper(queryClient) });

    expect(screen.getByText("Fixture Agent")).toBeInTheDocument();
    expect(
      document.querySelectorAll("svg.lucide-trash2").length,
      "org admin must see per-card trash icon",
    ).toBeGreaterThan(0);
  });

  it("regular member does NOT see any per-card Edit or Tools buttons (canEdit=false, canConfigure=false)", () => {
    // canEdit and canConfigure are derived the same way as canCreate
    // (isPlatformAdmin || isOrgAdmin). A regular member with no
    // admin role must not see the per-card Edit or Tools buttons.
    // The page is the strict gate; the AgentCard defaults to true
    // for back-compat, so the page must pass false explicitly.
    mockUseUserPermissions.mockReturnValue({
      canCreateAgent: false,
      isPlatformAdmin: false,
      isOrgAdmin: false,
    });
    // A regular member has no admin role on any org.
    mockHasRole.mockReset().mockReturnValue(false);
    mockUseMyAgents.mockReturnValue({
      data: [FIXTURE_AGENT],
      isLoading: false,
      error: null,
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(<AgentsPage />, { wrapper: makeWrapper(queryClient) });

    expect(
      screen.queryByRole("button", { name: /^edit$/i }),
      "regular member must not see the per-card Edit button",
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /^tools$/i }),
      "regular member must not see the per-card Tools button",
    ).not.toBeInTheDocument();
  });

  it("org admin DOES see per-card Edit and Tools buttons", () => {
    mockUseUserPermissions.mockReturnValue({
      canCreateAgent: true,
      isPlatformAdmin: false,
      isOrgAdmin: true,
    });
    mockUseMyAgents.mockReturnValue({
      data: [FIXTURE_AGENT],
      isLoading: false,
      error: null,
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(<AgentsPage />, { wrapper: makeWrapper(queryClient) });

    expect(
      screen.getByRole("button", { name: /^edit$/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /^tools$/i }),
    ).toBeInTheDocument();
  });

  // --- Task #25: per-agent canDelete (fixes the cross-org delete leak) ---
  // The page used to derive canDelete from the user's role on the
  // CURRENT org and apply it uniformly to every card. That meant an
  // org admin viewing another org's agent saw a trash icon and could
  // try to delete (the backend would 403, but the UI was leaking
  // intent). The fix is to compute canDelete per-agent using
  // `user.hasRole(role, agent.organization_id)`.

  it("regular user sees no trash icon on any agent card (per-agent canDelete)", () => {
    // Regular user: no admin role on any org. Even the agent in the
    // current org must not show a trash icon.
    mockUseUserPermissions.mockReturnValue({
      canCreateAgent: false,
      isPlatformAdmin: false,
      isOrgAdmin: false,
    });
    // Explicitly clear the role grants — a regular member has none.
    mockHasRole.mockReset().mockReturnValue(false);
    mockUseMyAgents.mockReturnValue({
      data: [FIXTURE_AGENT, FIXTURE_AGENT_OTHER_ORG],
      isLoading: false,
      error: null,
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(<AgentsPage />, { wrapper: makeWrapper(queryClient) });

    expect(document.querySelectorAll("svg.lucide-trash2").length).toBe(0);
  });

  it("org admin sees trash icon on current-org agent but NOT on a non-current-org agent", () => {
    // Per-agent canDelete: org-1 admin can delete org-1 agents,
    // must NOT be able to delete org-2 agents.
    mockHasRole.mockImplementation(
      (role: string, orgId?: string) =>
        role === "org_admin" && orgId === "org-1",
    );
    mockUseMyAgents.mockReturnValue({
      data: [FIXTURE_AGENT, FIXTURE_AGENT_OTHER_ORG],
      isLoading: false,
      error: null,
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(<AgentsPage />, { wrapper: makeWrapper(queryClient) });

    // The list view shows cards as a flat sequence. We use the agent
    // names as anchors and look at the trash icon counts adjacent to
    // each card. Easier invariant: there is exactly ONE trash icon
    // (the org-1 agent), not two.
    expect(
      document.querySelectorAll("svg.lucide-trash2").length,
      "org admin on org-1 must see exactly 1 trash icon (org-1 agent only)",
    ).toBe(1);
  });

  it("platform admin sees a trash icon on EVERY agent card (per-agent canDelete)", () => {
    // platform_admin role is org-agnostic — the page's per-agent check
    // must short-circuit to true regardless of the agent's org.
    mockHasRole.mockImplementation((role: string) => role === "platform_admin");
    mockUseUserPermissions.mockReturnValue({
      canCreateAgent: true,
      isPlatformAdmin: true,
      isOrgAdmin: false,
    });
    mockUseMyAgents.mockReturnValue({
      data: [FIXTURE_AGENT, FIXTURE_AGENT_OTHER_ORG],
      isLoading: false,
      error: null,
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(<AgentsPage />, { wrapper: makeWrapper(queryClient) });

    expect(
      document.querySelectorAll("svg.lucide-trash2").length,
      "platform admin must see a trash icon on every agent card",
    ).toBe(2);
  });

  it("per-agent canEdit / canConfigure get the same treatment (org admin, non-current-org agent)", () => {
    // Same per-agent logic gates canEdit and canConfigure. An org-1
    // admin viewing an org-2 agent must NOT see Edit or Tools for
    // that card. List view renders Edit + Tools as labeled buttons,
    // so we can count them by accessible name.
    mockHasRole.mockReset().mockImplementation(
      (role: string, orgId?: string) =>
        role === "org_admin" && orgId === "org-1",
    );
    mockUseMyAgents.mockReturnValue({
      data: [FIXTURE_AGENT, FIXTURE_AGENT_OTHER_ORG],
      isLoading: false,
      error: null,
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(<AgentsPage />, { wrapper: makeWrapper(queryClient) });

    // One Edit + one Tools for the org-1 agent; zero for the org-2
    // agent. Total: 1 of each.
    expect(screen.getAllByRole("button", { name: /^edit$/i }).length).toBe(1);
    expect(screen.getAllByRole("button", { name: /^tools$/i }).length).toBe(1);
  });

  // --- Task #37: read-only click into agent details ---
  // A regular org member sees the agent cards on /agents but has no
  // Edit/Tools/Trash affordance. They need a way to open the detail
  // page in read-only mode. The fix: the card body is itself a
  // clickable surface (button with the agent name as its accessible
  // name) that navigates to /agents/[id]?tab=persona. Admin
  // buttons inside the card (Edit, Tools, Trash) must still work and
  // must not be eaten by the outer click handler.

  it("regular user can click an agent card to open the read-only detail view", () => {
    // No admin role → no per-card Edit/Tools/Trash buttons. The card
    // body itself is the only way in. The detail page is rendered
    // read-only for non-admins (the detail page gates its write
    // actions per-button, not at the page level).
    mockUseUserPermissions.mockReturnValue({
      canCreateAgent: false,
      isPlatformAdmin: false,
      isOrgAdmin: false,
    });
    mockHasRole.mockReset().mockReturnValue(false);
    mockUseMyAgents.mockReturnValue({
      data: [FIXTURE_AGENT],
      isLoading: false,
      error: null,
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(<AgentsPage />, { wrapper: makeWrapper(queryClient) });

    // The card body should be a button whose accessible name includes
    // the agent name. The user clicks it; we expect router.push to
    // the detail page.
    const cardButton = screen.getByRole("button", { name: /fixture agent/i });
    fireEvent.click(cardButton);

    expect(mockPush).toHaveBeenCalledWith("/agents/agent-1?tab=persona");
  });

  it("does not render an agent from another organization for an org user", () => {
    // Organization users are scoped to the active organization. The
    // backend normally enforces this through /organization/{org_id}; this
    // assertion also protects the UI if a stale or malformed response
    // contains an agent from another organization.
    mockUseUserPermissions.mockReturnValue({
      canCreateAgent: false,
      isPlatformAdmin: false,
      isOrgAdmin: false,
    });
    mockHasRole.mockReset().mockReturnValue(false);
    mockUseOrgAgents.mockReturnValue({
      data: [FIXTURE_AGENT_OTHER_ORG],
      isLoading: false,
      error: null,
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(<AgentsPage />, { wrapper: makeWrapper(queryClient) });

    expect(screen.queryByText("Other Org Agent")).not.toBeInTheDocument();
  });

  it("org admin's per-card Edit button still navigates to the detail page (not double-fired)", () => {
    // The outer card click + the inner Edit click both navigate to
    // the same place. That's fine — the inner button must not be
    // swallowed by the outer click handler, and the inner click is
    // the one the admin actually uses. We assert the inner button
    // exists and is clickable; the click is intentionally local to
    // the Edit button (router.push should be called with the same
    // URL as the card click — duplication is OK; it's the same
    // destination).
    mockUseMyAgents.mockReturnValue({
      data: [FIXTURE_AGENT],
      isLoading: false,
      error: null,
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(<AgentsPage />, { wrapper: makeWrapper(queryClient) });

    const editButton = screen.getByRole("button", { name: /^edit$/i });
    fireEvent.click(editButton);

    expect(mockPush).toHaveBeenCalledWith("/agents/agent-1?tab=persona");
  });
});
