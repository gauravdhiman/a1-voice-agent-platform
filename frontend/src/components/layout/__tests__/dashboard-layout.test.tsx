/**
 * Tests for the dashboard layout's permission-aware nav rendering.
 *
 * Contract (mirrors docs/tw-drafts/navigation-redesign.md Section 6.3):
 *   - The nav is rendered in three sections (workspace, org_admin,
 *     platform_admin) in that order, with a visual separator between
 *     them.
 *   - An item with `requiredPermission: null` is rendered for every
 *     signed-in user.
 *   - An item with a `requiredPermission` string is rendered only when
 *     `useHasPermission(item.requiredPermission)` returns `true`.
 *   - The `platform_admin` section header is hidden when no item in it
 *     is visible to the current user (no empty heading).
 *   - The `org_admin` section header is hidden when no item in it is
 *     visible to the current user.
 *   - Platform admins (wildcard) see every item.
 */
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Override the global next/navigation mock (in tests/setup.ts) to add the
// usePathname hook used by the dashboard layout. The global mock only
// exposes useRouter, useSearchParams, useParams; usePathname is needed
// for the active-link highlight in the sidebar AND the breadcrumb header.
// `mockUsePathname` is hoisted so the vi.mock factory (also hoisted) can
// reference it; tests override the return value to exercise other routes.
const mockUsePathname = vi.hoisted(() => vi.fn(() => "/dashboard"));
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn(),
    back: vi.fn(),
  }),
  usePathname: () => mockUsePathname(),
  useSearchParams: () => ({
    get: vi.fn().mockReturnValue(null),
  }),
  useParams: () => ({}),
}));

// Mock the theme toggle so we don't need a real ThemeProvider in tests.
vi.mock("@/components/ui/theme-toggle", () => ({
  ThemeToggle: () => <div data-testid="theme-toggle-stub" />,
}));

const mockUseAuth = vi.fn();
vi.mock("@/contexts/auth-context", () => ({
  useAuth: () => mockUseAuth(),
}));

const mockUseOrganization = vi.fn();
vi.mock("@/contexts/organization-context", () => ({
  useOrganization: () => mockUseOrganization(),
}));

const mockUseMyPermissions = vi.fn();
vi.mock("@/hooks/use-has-permission", async () => {
  const actual =
    await vi.importActual<typeof import("@/hooks/use-has-permission")>(
      "@/hooks/use-has-permission",
    );
  return {
    ...actual,
    useMyPermissions: () => mockUseMyPermissions(),
    useHasPermission: (perm: string | null) => {
      // Mirrors the real helper: null -> always visible, wildcard ->
      // always visible, otherwise resource+action must be in the set.
      if (perm === null) return true;
      const { permissions } = mockUseMyPermissions();
      if (permissions["*"]?.includes("*")) return true;
      const [resource, action] = perm.split(":", 2);
      if (!resource || !action) return false;
      return Boolean(permissions[resource]?.includes(action));
    },
    useHasAnyPermission: (perms: readonly string[]) => {
      if (perms.length === 0) return false;
      const { permissions } = mockUseMyPermissions();
      if (permissions["*"]?.includes("*")) return true;
      return perms.some((perm) => {
        const [resource, action] = perm.split(":", 2);
        if (!resource || !action) return false;
        return Boolean(permissions[resource]?.includes(action));
      });
    },
  };
});

// Mock the role-derived permissions hook (isPlatformAdmin / isOrgAdmin).
// The real hook reads `user.hasRole(...)` from the auth context; tests
// control the role flags here so section visibility is deterministic.
const mockUseUserPermissions = vi.fn();
vi.mock("@/hooks/use-user-permissions", () => ({
  useUserPermissions: () => mockUseUserPermissions(),
}));

import { DashboardLayout } from "../dashboard-layout";

function makeWrapper(queryClient: QueryClient) {
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(
      QueryClientProvider,
      { client: queryClient },
      children,
    );
}

function defaultUser(orgId = "org-1") {
  return {
    id: "u-1",
    firstName: "Test",
    lastName: "User",
    email: "test@example.com",
    signOut: vi.fn().mockResolvedValue({ error: null }),
    hasRole: () => false,
    hasPermission: () => false,
  };
}

function defaultOrg(orgId = "org-1") {
  return {
    id: orgId,
    name: "Acme",
    slug: "acme",
    role: "member",
  };
}

describe("DashboardLayout - permission-aware nav", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset the pathname to the default route; individual breadcrumb tests
    // override this to exercise other routes.
    mockUsePathname.mockReturnValue("/dashboard");
    mockUseAuth.mockReturnValue({
      user: defaultUser(),
      isAuthenticated: true,
      signOut: vi.fn().mockResolvedValue({ error: null }),
    });
    mockUseOrganization.mockReturnValue({
      organizations: [defaultOrg()],
      currentOrganization: defaultOrg(),
    });
    // Default: regular org member permissions (per design doc Section 6.3
    // test plan, item 3 - "no org_admin items for a regular member").
    // Members get workspace permissions only; org_admin requires a more
    // permissive role on the current org.
    mockUseMyPermissions.mockReturnValue({
      permissions: {
        agent: ["read", "write", "delete"],
        phone_number: ["read", "write", "delete"],
        skill: ["read", "write", "delete"],
        call_log: ["read"],
      },
      isLoading: false,
      currentOrganizationId: "org-1",
    });
    // Default: regular member, not an org admin and not a platform admin.
    // Tests that exercise org_admin / platform_admin behaviour override
    // these flags explicitly.
    mockUseUserPermissions.mockReturnValue({
      isPlatformAdmin: false,
      isOrgAdmin: false,
      canUpdateOrganization: false,
      canDeleteOrganization: false,
      canViewOrganization: false,
      canManageMembers: false,
      canViewMembers: false,
      canInviteMembers: false,
      canRemoveMembers: false,
      canUpdateSettings: false,
      canViewSettings: false,
      canManageBilling: false,
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders all workspace items for a regular org member", () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <DashboardLayout>
        <div data-testid="page-content">Hello</div>
      </DashboardLayout>,
      { wrapper: makeWrapper(queryClient) },
    );

    // Workspace items should all be present.
    expect(screen.getByText("Home")).toBeInTheDocument();
    expect(screen.getByText("Agents")).toBeInTheDocument();
    expect(screen.getByText("Phone Numbers")).toBeInTheDocument();
    expect(screen.getByText("Skills")).toBeInTheDocument();
    expect(screen.getByText("Calls")).toBeInTheDocument();
  });

  it("does NOT render org_admin items for a regular member", () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <DashboardLayout>
        <div />
      </DashboardLayout>,
      { wrapper: makeWrapper(queryClient) },
    );

    // Regular member (default mock) has no member/billing/organization
    // permissions at all, so none of those items should render.
    expect(screen.queryByText("Members")).not.toBeInTheDocument();
    expect(screen.queryByText("Billing")).not.toBeInTheDocument();
    expect(screen.queryByText("Organization")).not.toBeInTheDocument();
  });

  it("does NOT render the platform_admin section for a regular member", () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <DashboardLayout>
        <div />
      </DashboardLayout>,
      { wrapper: makeWrapper(queryClient) },
    );

    // Platform admin items should not be present.
    expect(screen.queryByText("All Users")).not.toBeInTheDocument();
    expect(screen.queryByText("Platform Skills")).not.toBeInTheDocument();
  });

  it("renders org_admin items for an org admin (full set)", () => {
    // Org admin: full set of org-scoped permissions (member:invite,
    // billing:manage, organization:update). The layout shows the
    // org_admin section header AND every item in it. Under Option C
    // (role for section, permission for item) the org_admin section
    // is also gated by `isOrgAdmin`, so the role flag must be on.
    mockUseUserPermissions.mockReturnValue({
      isPlatformAdmin: false,
      isOrgAdmin: true,
      canUpdateOrganization: true,
      canDeleteOrganization: true,
      canViewOrganization: true,
      canManageMembers: true,
      canViewMembers: true,
      canInviteMembers: true,
      canRemoveMembers: true,
      canUpdateSettings: true,
      canViewSettings: true,
      canManageBilling: true,
    });
    mockUseMyPermissions.mockReturnValue({
      permissions: {
        agent: ["read", "write", "delete"],
        phone_number: ["read", "write", "delete"],
        skill: ["read", "write", "delete"],
        call_log: ["read"],
        member: ["read", "invite", "remove"],
        billing: ["manage"],
        organization: ["read", "update", "delete"],
      },
      isLoading: false,
      currentOrganizationId: "org-1",
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <DashboardLayout>
        <div />
      </DashboardLayout>,
      { wrapper: makeWrapper(queryClient) },
    );

    expect(screen.getByText("Members")).toBeInTheDocument();
    expect(screen.getByText("Billing")).toBeInTheDocument();
    expect(screen.getByText("Organization")).toBeInTheDocument();
    // But not platform-admin items.
    expect(screen.queryByText("All Users")).not.toBeInTheDocument();
  });

  it("renders the platform_admin section only for platform admins", () => {
    // Wildcard permission: every item should be visible.
    mockUseUserPermissions.mockReturnValue({
      isPlatformAdmin: true,
      isOrgAdmin: false,
      canUpdateOrganization: true,
      canDeleteOrganization: true,
      canViewOrganization: true,
      canManageMembers: true,
      canViewMembers: true,
      canInviteMembers: true,
      canRemoveMembers: true,
      canUpdateSettings: true,
      canViewSettings: true,
      canManageBilling: true,
    });
    mockUseMyPermissions.mockReturnValue({
      permissions: { "*": ["*"] },
      isLoading: false,
      currentOrganizationId: null,
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <DashboardLayout>
        <div />
      </DashboardLayout>,
      { wrapper: makeWrapper(queryClient) },
    );

    expect(screen.getByText("All Users")).toBeInTheDocument();
    expect(screen.getByText("Platform Skills")).toBeInTheDocument();
  });

  it("Option C: regular user with org-scoped permissions still sees no org_admin items", () => {
    // This is the lock-in test for Option C: a user with the
    // underlying permissions (member:read, billing:manage,
    // organization:read) but no org_admin role must NOT see the
    // org_admin section items. Before Option C, the layout relied
    // only on per-item permission checks; a future role with those
    // permissions would see "Members" / "Billing" / "Organization"
    // even though the role isn't an admin. The section-level role
    // gate prevents that.
    mockUseUserPermissions.mockReturnValue({
      isPlatformAdmin: false,
      isOrgAdmin: false,
      canUpdateOrganization: false,
      canDeleteOrganization: false,
      canViewOrganization: false,
      canManageMembers: false,
      canViewMembers: false,
      canInviteMembers: false,
      canRemoveMembers: false,
      canUpdateSettings: false,
      canViewSettings: false,
      canManageBilling: false,
    });
    mockUseMyPermissions.mockReturnValue({
      permissions: {
        agent: ["read"],
        phone_number: ["read"],
        skill: ["read"],
        call_log: ["read"],
        member: ["read"],
        billing: ["manage"],
        organization: ["read"],
      },
      isLoading: false,
      currentOrganizationId: "org-1",
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <DashboardLayout>
        <div />
      </DashboardLayout>,
      { wrapper: makeWrapper(queryClient) },
    );

    // Per-item permission gates would have allowed these. Section-level
    // role gate must prevent them.
    expect(screen.queryByText("Members")).not.toBeInTheDocument();
    expect(screen.queryByText("Billing")).not.toBeInTheDocument();
    expect(screen.queryByText("Organization")).not.toBeInTheDocument();
    // The section heading itself must also be hidden.
    expect(screen.queryByText("Org Admin")).not.toBeInTheDocument();
    expect(screen.queryByText("Platform Admin")).not.toBeInTheDocument();
  });

  it("Option C: regular user never sees the Org Admin / Platform Admin section headings", () => {
    // A regular user with workspace permissions only (the default
    // mock state). The section headings should be hidden entirely,
    // not just empty.
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <DashboardLayout>
        <div />
      </DashboardLayout>,
      { wrapper: makeWrapper(queryClient) },
    );

    expect(screen.queryByText("Org Admin")).not.toBeInTheDocument();
    expect(screen.queryByText("Platform Admin")).not.toBeInTheDocument();
    // But the workspace heading is always visible.
    expect(screen.getByText("Workspace")).toBeInTheDocument();
  });

  it("Option C: org admin sees the Org Admin section heading but not Platform Admin", () => {
    mockUseUserPermissions.mockReturnValue({
      isPlatformAdmin: false,
      isOrgAdmin: true,
      canUpdateOrganization: true,
      canDeleteOrganization: true,
      canViewOrganization: true,
      canManageMembers: true,
      canViewMembers: true,
      canInviteMembers: true,
      canRemoveMembers: true,
      canUpdateSettings: true,
      canViewSettings: true,
      canManageBilling: true,
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <DashboardLayout>
        <div />
      </DashboardLayout>,
      { wrapper: makeWrapper(queryClient) },
    );

    expect(screen.getByText("Org Admin")).toBeInTheDocument();
    expect(screen.queryByText("Platform Admin")).not.toBeInTheDocument();
  });

  it("Option C: platform admin sees all three section headings", () => {
    mockUseUserPermissions.mockReturnValue({
      isPlatformAdmin: true,
      isOrgAdmin: true, // platform_admin also sees Org Admin section
      canUpdateOrganization: true,
      canDeleteOrganization: true,
      canViewOrganization: true,
      canManageMembers: true,
      canViewMembers: true,
      canInviteMembers: true,
      canRemoveMembers: true,
      canUpdateSettings: true,
      canViewSettings: true,
      canManageBilling: true,
    });
    mockUseMyPermissions.mockReturnValue({
      permissions: { "*": ["*"] },
      isLoading: false,
      currentOrganizationId: null,
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <DashboardLayout>
        <div />
      </DashboardLayout>,
      { wrapper: makeWrapper(queryClient) },
    );

    expect(screen.getByText("Workspace")).toBeInTheDocument();
    expect(screen.getByText("Org Admin")).toBeInTheDocument();
    expect(screen.getByText("Platform Admin")).toBeInTheDocument();
  });

  it("renders children inside the main content area", () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <DashboardLayout>
        <div data-testid="page-content">Page Body</div>
      </DashboardLayout>,
      { wrapper: makeWrapper(queryClient) },
    );

    const main = screen.getByRole("main");
    expect(within(main).getByTestId("page-content")).toBeInTheDocument();
  });

  describe("breadcrumb header", () => {
    // The breadcrumb region doubles as the page header title. Each platform-
    // admin route must resolve to its own title (not fall through to the
    // "Dashboard" default). `/platform/skills` already resolves; the
    // `/platform/tools` nav item was added without a breadcrumb case, so it
    // fell through to "Dashboard".
    function renderAsPlatformAdmin() {
      mockUseAuth.mockReturnValue({
        user: { ...defaultUser(), hasRole: (r: string) => r === "platform_admin" },
        isAuthenticated: true,
        signOut: vi.fn().mockResolvedValue({ error: null }),
      });
      mockUseOrganization.mockReturnValue({
        organizations: [defaultOrg()],
        currentOrganization: defaultOrg(),
      });
      mockUseMyPermissions.mockReturnValue({
        permissions: { "*": ["*"] },
        isLoading: false,
        currentOrganizationId: null,
      });
      mockUseUserPermissions.mockReturnValue({
        isPlatformAdmin: true,
        isOrgAdmin: false,
        canUpdateOrganization: true,
        canDeleteOrganization: true,
        canViewOrganization: true,
        canManageMembers: true,
        canViewMembers: true,
        canInviteMembers: true,
        canRemoveMembers: true,
        canUpdateSettings: true,
        canViewSettings: true,
        canManageBilling: true,
      });
      const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false } },
      });
      render(
        <DashboardLayout>
          <div />
        </DashboardLayout>,
        { wrapper: makeWrapper(queryClient) },
      );
    }

    it("shows 'Platform Skills' for /platform/skills (parity baseline)", () => {
      mockUsePathname.mockReturnValue("/platform/skills");
      renderAsPlatformAdmin();
      const breadcrumb = screen.getByRole("navigation", { name: /breadcrumb/i });
      expect(within(breadcrumb).getByText("Platform Skills")).toBeInTheDocument();
    });

    it("shows 'Platform Tools' for /platform/tools (not 'Dashboard')", () => {
      mockUsePathname.mockReturnValue("/platform/tools");
      renderAsPlatformAdmin();
      const breadcrumb = screen.getByRole("navigation", { name: /breadcrumb/i });
      expect(within(breadcrumb).getByText("Platform Tools")).toBeInTheDocument();
      expect(within(breadcrumb).queryByText("Dashboard")).not.toBeInTheDocument();
    });
  });
});
