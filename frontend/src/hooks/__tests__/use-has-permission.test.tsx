/**
 * Tests for the useHasPermission hook.
 *
 * Contract (mirrors docs/tw-drafts/navigation-redesign.md Section 6.1):
 * - useHasPermission(perm) returns true if the user has the perm on the
 *   current org context, false if not, null while loading.
 * - useHasAnyPermission(perms) returns true if ANY is granted, false if
 *   NONE are granted, null while loading.
 * - The wildcard {"*": ["*"]} (granted to platform admins) means EVERY
 *   permission check returns true.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook } from "@testing-library/react";
import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

// Mock the auth service at the module level so the hook doesn't depend on
// the real HTTP client.
vi.mock("@/services/auth-service", () => ({
  authService: {
    getCurrentUser: vi.fn(),
  },
}));

// Mock the auth context so useMyPermissions knows the current org.
const mockUseAuth = vi.fn();
vi.mock("@/contexts/auth-context", () => ({
  useAuth: () => mockUseAuth(),
}));

// Mock the organization context so the hook knows the current org id.
const mockUseOrganization = vi.fn();
vi.mock("@/contexts/organization-context", () => ({
  useOrganization: () => mockUseOrganization(),
}));

import { authService } from "@/services/auth-service";
import {
  useHasAnyPermission,
  useHasPermission,
  useMyPermissions,
} from "../use-has-permission";

const mockedAuthService = vi.mocked(authService);

function makeWrapper(queryClient: QueryClient) {
  // React Query provider required for the hook's internal useQuery call.
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(
      QueryClientProvider,
      { client: queryClient },
      children,
    );
}

describe("useHasPermission", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default: signed-in user with a current org. Individual tests may override.
    mockUseAuth.mockReturnValue({ user: { id: "u-1" }, isAuthenticated: true });
    mockUseOrganization.mockReturnValue({
      currentOrganization: { id: "org-1" },
    });
  });

  it("returns true when the permission is granted on the current org", async () => {
    mockedAuthService.getCurrentUser.mockResolvedValue({
      success: true,
      user: {
        id: "u-1",
        current_organization_id: "org-1",
        permissions: { agent: ["read", "create"] },
        // other UserProfile fields are not exercised by this hook
        email: "",
        first_name: "",
        last_name: "",
        email_confirmed_at: null,
        created_at: "",
        updated_at: "",
        roles: [],
      },
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const { result } = renderHook(
      () => useHasPermission("agent:read"),
      { wrapper: makeWrapper(queryClient) },
    );

    // While loading, the hook returns null.
    expect(result.current).toBeNull();
    // Wait for the query to settle.
    await vi.waitFor(() => expect(result.current).toBe(true));
  });

  it("returns false when the permission is not granted", async () => {
    mockUseAuth.mockReturnValue({ user: { id: "u-1" }, isAuthenticated: true });
    mockedAuthService.getCurrentUser.mockResolvedValue({
      success: true,
      user: {
        id: "u-1",
        current_organization_id: "org-1",
        permissions: { agent: ["read"] },
        email: "",
        first_name: "",
        last_name: "",
        email_confirmed_at: null,
        created_at: "",
        updated_at: "",
        roles: [],
      },
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const { result } = renderHook(
      () => useHasPermission("agent:create"),
      { wrapper: makeWrapper(queryClient) },
    );

    await vi.waitFor(() => expect(result.current).toBe(false));
  });

  it("returns true for ANY permission when the wildcard is present", async () => {
    // Platform admin: the response carries {"*": ["*"}.
    mockUseAuth.mockReturnValue({ user: { id: "u-admin" }, isAuthenticated: true });
    mockedAuthService.getCurrentUser.mockResolvedValue({
      success: true,
      user: {
        id: "u-admin",
        current_organization_id: null,
        permissions: { "*": ["*"] },
        email: "",
        first_name: "",
        last_name: "",
        email_confirmed_at: null,
        created_at: "",
        updated_at: "",
        roles: [],
      },
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const { result } = renderHook(
      () => useHasPermission("billing:manage"),
      { wrapper: makeWrapper(queryClient) },
    );

    await vi.waitFor(() => expect(result.current).toBe(true));
  });

  it("returns null while the query is still loading", () => {
    mockUseAuth.mockReturnValue({ user: { id: "u-1" }, isAuthenticated: true });
    // The promise never resolves -> query stays in loading state.
    mockedAuthService.getCurrentUser.mockReturnValue(new Promise(() => {}));

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const { result } = renderHook(
      () => useHasPermission("agent:read"),
      { wrapper: makeWrapper(queryClient) },
    );

    expect(result.current).toBeNull();
  });

  it("returns false when there is no signed-in user", async () => {
    mockUseAuth.mockReturnValue({ user: null });
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const { result } = renderHook(
      () => useHasPermission("agent:read"),
      { wrapper: makeWrapper(queryClient) },
    );

    // No user -> no query, no permissions -> false.
    await vi.waitFor(() => expect(result.current).toBe(false));
  });

  it("returns true for null permission when the user is signed in", async () => {
    // null is the "always visible" marker used by nav items that don't
    // gate on a specific resource+action. Any signed-in user should see
    // them, regardless of what the /me response contains.
    mockUseAuth.mockReturnValue({ user: { id: "u-1" }, isAuthenticated: true });
    mockedAuthService.getCurrentUser.mockResolvedValue({
      success: true,
      user: {
        id: "u-1",
        current_organization_id: "org-1",
        // No permissions at all - the user is on a fresh org.
        permissions: {},
        email: "",
        first_name: "",
        last_name: "",
        email_confirmed_at: null,
        created_at: "",
        updated_at: "",
        roles: [],
      },
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const { result } = renderHook(
      // Cast through unknown because the public type still requires a
      // permission string; we want to test the null-passthrough
      // behaviour explicitly.
      () => useHasPermission(null as unknown as `${string}:${string}`),
      { wrapper: makeWrapper(queryClient) },
    );

    await vi.waitFor(() => expect(result.current).toBe(true));
  });
});

describe("useHasAnyPermission", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue({ user: { id: "u-1" }, isAuthenticated: true });
    mockUseOrganization.mockReturnValue({
      currentOrganization: { id: "org-1" },
    });
  });

  it("returns true if ANY of the perms is granted", async () => {
    mockUseAuth.mockReturnValue({ user: { id: "u-1" }, isAuthenticated: true });
    mockedAuthService.getCurrentUser.mockResolvedValue({
      success: true,
      user: {
        id: "u-1",
        current_organization_id: "org-1",
        permissions: { agent: ["read"] },
        email: "",
        first_name: "",
        last_name: "",
        email_confirmed_at: null,
        created_at: "",
        updated_at: "",
        roles: [],
      },
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const { result } = renderHook(
      () => useHasAnyPermission(["billing:manage", "agent:read"]),
      { wrapper: makeWrapper(queryClient) },
    );

    await vi.waitFor(() => expect(result.current).toBe(true));
  });

  it("returns false if NONE of the perms are granted", async () => {
    mockUseAuth.mockReturnValue({ user: { id: "u-1" }, isAuthenticated: true });
    mockedAuthService.getCurrentUser.mockResolvedValue({
      success: true,
      user: {
        id: "u-1",
        current_organization_id: "org-1",
        permissions: { agent: ["read"] },
        email: "",
        first_name: "",
        last_name: "",
        email_confirmed_at: null,
        created_at: "",
        updated_at: "",
        roles: [],
      },
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const { result } = renderHook(
      () => useHasAnyPermission(["billing:manage", "organization:delete"]),
      { wrapper: makeWrapper(queryClient) },
    );

    await vi.waitFor(() => expect(result.current).toBe(false));
  });

  it("returns null while loading", () => {
    mockUseAuth.mockReturnValue({ user: { id: "u-1" }, isAuthenticated: true });
    mockedAuthService.getCurrentUser.mockReturnValue(new Promise(() => {}));

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const { result } = renderHook(
      () => useHasAnyPermission(["agent:read"]),
      { wrapper: makeWrapper(queryClient) },
    );

    expect(result.current).toBeNull();
  });
});

describe("useMyPermissions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue({ user: { id: "u-1" }, isAuthenticated: true });
    mockUseOrganization.mockReturnValue({
      currentOrganization: { id: "org-1" },
    });
  });

  it("exposes the resolved permissions object", async () => {
    mockUseAuth.mockReturnValue({ user: { id: "u-1" }, isAuthenticated: true });
    mockedAuthService.getCurrentUser.mockResolvedValue({
      success: true,
      user: {
        id: "u-1",
        current_organization_id: "org-1",
        permissions: { agent: ["read", "create"], skill: ["read"] },
        email: "",
        first_name: "",
        last_name: "",
        email_confirmed_at: null,
        created_at: "",
        updated_at: "",
        roles: [],
      },
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const { result } = renderHook(() => useMyPermissions(), {
      wrapper: makeWrapper(queryClient),
    });

    await vi.waitFor(() =>
      expect(result.current.permissions).toEqual({
        agent: ["read", "create"],
        skill: ["read"],
      }),
    );
    expect(result.current.currentOrganizationId).toBe("org-1");
  });
});
