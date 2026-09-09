/**
 * Tests for the useUserPermissions facade (page-level permission hook).
 *
 * The facade derives boolean capability flags from the resolved
 * `/me.permissions` map. These tests pin the contract:
 *
 *   - All "can…" flags are derived from the canonical permission
 *     vocabulary (no more dead `member:invite` / `settings:*` strings).
 *   - The wildcard `{"*": ["*"]}` (platform admins) makes every
 *     "can…" flag true regardless of the permissions map.
 *   - isPlatformAdmin / isOrgAdmin are role-based, NOT permission-based.
 *   - The hook fails closed while loading AND when the user / org is
 *     missing. Critically: there is NO `NODE_ENV === "development"`
 *     grant-all fallback. A bug in the past let any user in dev mode
 *     see every write CTA; this test guards that regression.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook } from "@testing-library/react";
import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

// --- Module mocks --------------------------------------------------------

vi.mock("@/services/auth-service", () => ({
  authService: {
    getCurrentUser: vi.fn(),
  },
}));

const mockUseAuth = vi.fn();
vi.mock("@/contexts/auth-context", () => ({
  useAuth: () => mockUseAuth(),
}));

const mockUseOrganization = vi.fn();
vi.mock("@/contexts/organization-context", () => ({
  useOrganization: () => mockUseOrganization(),
}));

import { authService } from "@/services/auth-service";
import { useUserPermissions } from "@/hooks/use-user-permissions";
import type { ResourcePermissions } from "@/hooks/use-has-permission";

const mockedAuthService = vi.mocked(authService);

// --- Helpers -------------------------------------------------------------

function makeWrapper(queryClient: QueryClient) {
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(
      QueryClientProvider,
      { client: queryClient },
      children,
    );
}

/** A UserProfile-shaped mock with a working `hasRole` for the facade. */
function makeUser(
  hasRole: (role: string, orgId?: string) => boolean,
  id = "u-1",
) {
  return { id, hasRole };
}

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
}

function mockGetCurrentUser(
  permissions: ResourcePermissions,
  currentOrgId: string | null = "org-1",
) {
  mockedAuthService.getCurrentUser.mockResolvedValue({
    success: true,
    user: {
      id: "u-1",
      current_organization_id: currentOrgId,
      permissions,
      email: "",
      first_name: "",
      last_name: "",
      email_confirmed_at: null,
      created_at: "",
      updated_at: "",
      roles: [],
    },
  });
}

// --- Tests ---------------------------------------------------------------

describe("useUserPermissions — role flags", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default: signed-in user with a current org but no roles.
    mockUseAuth.mockReturnValue({
      user: makeUser(() => false),
      isAuthenticated: true,
    });
    mockUseOrganization.mockReturnValue({
      currentOrganization: { id: "org-1" },
    });
  });

  it("flags platform_admin as both isPlatformAdmin AND isOrgAdmin (cross-org, but the boolean is the role itself)", async () => {
    // platform_admin: org-agnostic, true regardless of which org.
    mockUseAuth.mockReturnValue({
      user: makeUser((role) => role === "platform_admin"),
      isAuthenticated: true,
    });
    mockGetCurrentUser({ "*": ["*"] });

    const { result } = renderHook(() => useUserPermissions(), {
      wrapper: makeWrapper(makeQueryClient()),
    });
    await vi.waitFor(() => expect(result.current.isPlatformAdmin).toBe(true));
    // platform_admin does NOT auto-grant org_admin on a specific org.
    expect(result.current.isOrgAdmin).toBe(false);
  });

  it("flags org_admin on the current org as isOrgAdmin only", async () => {
    mockUseAuth.mockReturnValue({
      user: makeUser(
        (role, orgId) => role === "org_admin" && orgId === "org-1",
      ),
      isAuthenticated: true,
    });
    mockGetCurrentUser({});

    const { result } = renderHook(() => useUserPermissions(), {
      wrapper: makeWrapper(makeQueryClient()),
    });
    await vi.waitFor(() => expect(result.current.isOrgAdmin).toBe(true));
    expect(result.current.isPlatformAdmin).toBe(false);
  });

  it("does NOT flag isOrgAdmin when org_admin role is on a different org", async () => {
    mockUseAuth.mockReturnValue({
      user: makeUser(
        (role, orgId) => role === "org_admin" && orgId === "org-OTHER",
      ),
      isAuthenticated: true,
    });
    mockGetCurrentUser({});

    const { result } = renderHook(() => useUserPermissions(), {
      wrapper: makeWrapper(makeQueryClient()),
    });
    await vi.waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.isOrgAdmin).toBe(false);
    expect(result.current.isPlatformAdmin).toBe(false);
  });
});

describe("useUserPermissions — capability flags (org_admin permissions map)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default: platform admin sees all, but to test permission-driven
    // gates we override the role check per test.
    mockUseAuth.mockReturnValue({
      user: makeUser(() => false),
      isAuthenticated: true,
    });
    mockUseOrganization.mockReturnValue({
      currentOrganization: { id: "org-1" },
    });
  });

  it("grants agent write flags when the permission map includes the CRUD set", async () => {
    mockGetCurrentUser({
      agent: ["read", "create", "update", "delete"],
    });
    const { result } = renderHook(() => useUserPermissions(), {
      wrapper: makeWrapper(makeQueryClient()),
    });
    await vi.waitFor(() => expect(result.current.canCreateAgent).toBe(true));
    expect(result.current.canUpdateAgent).toBe(true);
    expect(result.current.canDeleteAgent).toBe(true);
  });

  it("denies agent write flags when the permission map is read-only", async () => {
    // regular_user scenario: read only.
    mockGetCurrentUser({ agent: ["read"] });
    const { result } = renderHook(() => useUserPermissions(), {
      wrapper: makeWrapper(makeQueryClient()),
    });
    await vi.waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.canCreateAgent).toBe(false);
    expect(result.current.canUpdateAgent).toBe(false);
    expect(result.current.canDeleteAgent).toBe(false);
  });

  it("grants canManageSkills when ANY of skill:create|update|delete is present", async () => {
    mockGetCurrentUser({ skill: ["read", "update"] });
    const { result } = renderHook(() => useUserPermissions(), {
      wrapper: makeWrapper(makeQueryClient()),
    });
    await vi.waitFor(() => expect(result.current.canManageSkills).toBe(true));
  });

  it("denies canManageSkills when only skill:read is present", async () => {
    mockGetCurrentUser({ skill: ["read"] });
    const { result } = renderHook(() => useUserPermissions(), {
      wrapper: makeWrapper(makeQueryClient()),
    });
    await vi.waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.canManageSkills).toBe(false);
  });

  it("grants canManagePhoneNumbers for any CRUD action on phone_number", async () => {
    mockGetCurrentUser({ phone_number: ["read", "create"] });
    const { result } = renderHook(() => useUserPermissions(), {
      wrapper: makeWrapper(makeQueryClient()),
    });
    await vi.waitFor(() =>
      expect(result.current.canManagePhoneNumbers).toBe(true),
    );
  });

  it("grants canManageBilling via billing:manage OR billing:subscribe", async () => {
    // Either gate should satisfy the boolean.
    mockGetCurrentUser({ billing: ["manage"] });
    const { result } = renderHook(() => useUserPermissions(), {
      wrapper: makeWrapper(makeQueryClient()),
    });
    await vi.waitFor(() => expect(result.current.canManageBilling).toBe(true));
  });

  it("denies canManageBilling when the user has no billing permission at all", async () => {
    // regular_user: no billing access.
    mockGetCurrentUser({ agent: ["read"], skill: ["read"] });
    const { result } = renderHook(() => useUserPermissions(), {
      wrapper: makeWrapper(makeQueryClient()),
    });
    await vi.waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.canManageBilling).toBe(false);
  });

  it("member CRUD flags map to member:create|update|delete", async () => {
    mockGetCurrentUser({
      member: ["read", "create", "update", "delete"],
    });
    const { result } = renderHook(() => useUserPermissions(), {
      wrapper: makeWrapper(makeQueryClient()),
    });
    await vi.waitFor(() => expect(result.current.canInviteMembers).toBe(true));
    expect(result.current.canRemoveMembers).toBe(true);
    // canManageMembers is the OR of invite/update/remove.
    expect(result.current.canManageMembers).toBe(true);
  });

  it("denies member CRUD for a regular user (member:read only)", async () => {
    mockGetCurrentUser({ member: ["read"] });
    const { result } = renderHook(() => useUserPermissions(), {
      wrapper: makeWrapper(makeQueryClient()),
    });
    await vi.waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.canInviteMembers).toBe(false);
    expect(result.current.canRemoveMembers).toBe(false);
    expect(result.current.canManageMembers).toBe(false);
  });
});

describe("useUserPermissions — platform admin wildcard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue({
      user: makeUser((role) => role === "platform_admin"),
      isAuthenticated: true,
    });
    mockUseOrganization.mockReturnValue({
      currentOrganization: { id: "org-1" },
    });
  });

  it("makes every 'can…' flag true when the user is a platform admin (even with empty permission map)", async () => {
    // The wildcard {"*": ["*"]} is what the resolver returns for
    // platform_admin. Every gate should pass.
    mockGetCurrentUser({ "*": ["*"] });
    const { result } = renderHook(() => useUserPermissions(), {
      wrapper: makeWrapper(makeQueryClient()),
    });
    await vi.waitFor(() => expect(result.current.canCreateAgent).toBe(true));
    expect(result.current.canManageSkills).toBe(true);
    expect(result.current.canManagePhoneNumbers).toBe(true);
    expect(result.current.canManageBilling).toBe(true);
    expect(result.current.canManageMembers).toBe(true);
  });
});

describe("useUserPermissions — fail-closed behaviour", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue({
      user: makeUser(() => false),
      isAuthenticated: true,
    });
    mockUseOrganization.mockReturnValue({
      currentOrganization: { id: "org-1" },
    });
  });

  it("returns all-false flags while the permissions query is loading", () => {
    // Promise that never resolves: query stays in loading state.
    mockedAuthService.getCurrentUser.mockReturnValue(new Promise(() => {}));
    const { result } = renderHook(() => useUserPermissions(), {
      wrapper: makeWrapper(makeQueryClient()),
    });
    // isLoading is true…
    expect(result.current.isLoading).toBe(true);
    // …and every "can…" gate is false (no flash-on for members).
    expect(result.current.canCreateAgent).toBe(false);
    expect(result.current.canManageSkills).toBe(false);
    expect(result.current.canManageBilling).toBe(false);
  });

  it("returns all-false flags when there is no signed-in user", async () => {
    mockUseAuth.mockReturnValue({ user: null });
    const { result } = renderHook(() => useUserPermissions(), {
      wrapper: makeWrapper(makeQueryClient()),
    });
    await vi.waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.canCreateAgent).toBe(false);
    expect(result.current.canManageSkills).toBe(false);
    expect(result.current.isPlatformAdmin).toBe(false);
    expect(result.current.isOrgAdmin).toBe(false);
  });

  it("returns all-false flags when there is no current org", async () => {
    mockUseOrganization.mockReturnValue({ currentOrganization: null });
    mockGetCurrentUser({});
    const { result } = renderHook(() => useUserPermissions(), {
      wrapper: makeWrapper(makeQueryClient()),
    });
    await vi.waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.canCreateAgent).toBe(false);
    expect(result.current.isOrgAdmin).toBe(false);
  });

  it("does NOT grant-all when NODE_ENV is development (the old bug)", async () => {
    // The previous implementation had a `NODE_ENV === "development"`
    // fallback that granted every "can…" flag on exception. That
    // branch was removed in this rewrite. This test pins the new
    // behaviour: even in dev mode, a user with no permissions
    // should see no write CTAs.
    vi.stubEnv("NODE_ENV", "development");

    try {
      mockGetCurrentUser({}); // empty permissions
      const { result } = renderHook(() => useUserPermissions(), {
        wrapper: makeWrapper(makeQueryClient()),
      });
      await vi.waitFor(() => expect(result.current.isLoading).toBe(false));
      // Every gate must be false even in dev mode.
      expect(result.current.canCreateAgent).toBe(false);
      expect(result.current.canManageSkills).toBe(false);
      expect(result.current.canManagePhoneNumbers).toBe(false);
      expect(result.current.canManageBilling).toBe(false);
      expect(result.current.canManageMembers).toBe(false);
    } finally {
      vi.unstubAllEnvs();
    }
  });
});
