/**
 * Tests for the /agents/create page (CRIT frontend leak — direct URL bypass).
 *
 * Contract (N1 Epic B gap fix):
 *   - Gate uses `canCreateAgent` (`agent:create` from `/me.permissions`),
 *     not a bare isOrgAdmin / isPlatformAdmin role check.
 *   - Direct URL navigation without the permission shows AccessDenied.
 *   - Users with canCreateAgent see the create widget.
 */
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockUseUserPermissions = vi.fn();
const mockUseOrganization = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn(),
    back: vi.fn(),
  }),
  useSearchParams: () => ({
    get: vi.fn().mockReturnValue(null),
  }),
  usePathname: () => "/agents/create",
  useParams: () => ({}),
}));

vi.mock("@/contexts/organization-context", () => ({
  useOrganization: () => mockUseOrganization(),
}));

vi.mock("@/hooks/use-user-permissions", () => ({
  useUserPermissions: () => mockUseUserPermissions(),
}));

// Stub the create widget so we don't pull in its full dependency tree
// (which includes the agent service + form state). The test only cares
// about the page-level permission gate.
vi.mock("@/components/agents/agent-create-widget", () => ({
  AgentCreateWidget: () => <div data-testid="agent-create-widget" />,
}));

import CreateAgentPage from "../page";

function makeWrapper(queryClient: QueryClient) {
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(
      QueryClientProvider,
      { client: queryClient },
      children,
    );
}

describe("/agents/create page (N1 — page-level admin gate)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseOrganization.mockReturnValue({
      organizations: [{ id: "org-1", name: "Acme" }],
      currentOrganization: { id: "org-1", name: "Acme" },
    });
  });

  it("renders the create widget when canCreateAgent is true (org admin grants)", () => {
    mockUseUserPermissions.mockReturnValue({
      canCreateAgent: true,
      isPlatformAdmin: false,
      isOrgAdmin: true,
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(<CreateAgentPage />, { wrapper: makeWrapper(queryClient) });

    expect(screen.getByTestId("agent-create-widget")).toBeInTheDocument();
  });

  it("renders the create widget when canCreateAgent is true (platform admin)", () => {
    mockUseUserPermissions.mockReturnValue({
      canCreateAgent: true,
      isPlatformAdmin: true,
      isOrgAdmin: false,
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(<CreateAgentPage />, { wrapper: makeWrapper(queryClient) });

    expect(screen.getByTestId("agent-create-widget")).toBeInTheDocument();
  });

  it("shows AccessDenied when canCreateAgent is false (CRIT — direct URL bypass)", () => {
    mockUseUserPermissions.mockReturnValue({
      canCreateAgent: false,
      isPlatformAdmin: false,
      isOrgAdmin: false,
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(<CreateAgentPage />, { wrapper: makeWrapper(queryClient) });

    expect(screen.getByText(/access denied/i)).toBeInTheDocument();
    expect(screen.queryByTestId("agent-create-widget")).not.toBeInTheDocument();
  });
});
