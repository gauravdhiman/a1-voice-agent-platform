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
 * Cross-org delete limitation (TODO, out of scope here): the page
 * lists agents across all orgs. A page-level canDelete derived from
 * the current org is wrong for non-current-org agents. The simple
 * rule for now matches the org-scoped /skills page: a page-level
 * canDelete is good enough for the user-facing surface, and the
 * backend re-validates per-org.
 */
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mockUseOrganization = vi.fn();
const mockUseUserPermissions = vi.fn();
const mockUseMyAgents = vi.fn();
const mockUseDeleteAgent = vi.fn();
const mockUseSearchParams = vi.fn();
const mockPush = vi.fn();

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

vi.mock("@/hooks/use-user-permissions", () => ({
  useUserPermissions: () => mockUseUserPermissions(),
}));

vi.mock("@/hooks/use-agent-queries", () => ({
  useMyAgents: () => mockUseMyAgents(),
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
    mockUseOrganization.mockReturnValue({
      organizations: [{ id: "org-1", name: "Acme" }],
      currentOrganization: { id: "org-1", name: "Acme" },
    });
    mockUseSearchParams.mockReturnValue({
      get: vi.fn().mockReturnValue(null),
    });
    mockUseDeleteAgent.mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue(undefined),
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders the 'New Agent' button for an org admin", () => {
    mockUseUserPermissions.mockReturnValue({
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
    mockUseUserPermissions.mockReturnValue({
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

    expect(
      screen.getByRole("button", { name: /new agent/i }),
    ).toBeInTheDocument();
  });

  it("does NOT render the 'New Agent' button for a regular org member", () => {
    mockUseUserPermissions.mockReturnValue({
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
});
