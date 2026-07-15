/**
 * Permission hooks for the navigation redesign (N1).
 *
 * Contract (mirrors docs/tw-drafts/navigation-redesign.md Section 6.1):
 *   - useHasPermission(perm) -> true if granted, false if not, null while loading.
 *   - useHasAnyPermission(perms) -> true if ANY is granted, false otherwise, null while loading.
 *   - The wildcard {"*": ["*"]} (granted to platform admins) means EVERY
 *     permission check returns true.
 *
 * The hooks read from `GET /me?org_id=<current>`, which the backend
 * resolves server-side via `permissions_service.resolve_permissions`.
 * The result is cached per `user_id` + `org_id` in TanStack Query and
 * invalidated on org switch (see `useMyPermissions` queryKey).
 *
 * The hooks MUST be safe to call during SSR / before auth loads: when
 * there is no signed-in user, the query is disabled and the helpers
 * return `false` (not `null`) to keep nav rendering deterministic.
 */
"use client";

import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/contexts/auth-context";
import { useOrganization } from "@/contexts/organization-context";
import { authService } from "@/services/auth-service";
import type { UserProfile } from "@/types/auth";

/** A permission string in the contract: `<resource>:<action>`. */
export type PermissionString = `${string}:${string}`;

/** Resource -> actions map returned by the backend. */
export type ResourcePermissions = Record<string, string[]>;

/** Result of useMyPermissions. */
export interface MyPermissionsResult {
  /** True while the query is in flight (no cached data yet). */
  isLoading: boolean;
  /** The org id the permissions are scoped to, or null. */
  currentOrganizationId: string | null | undefined;
  /** The resolved permissions map. Empty object when nothing is granted. */
  permissions: ResourcePermissions;
}

/** Cache key factory for the /me permissions query. */
export const myPermissionsQueryKey = (userId: string, orgId: string | null) =>
  ["me", "permissions", userId, orgId ?? "none"] as const;

/**
 * Fetches the current user's effective permissions for the current org.
 *
 * Returns `{ permissions, currentOrganizationId, isLoading }`. Disabled
 * (and returns an empty result) when the user is not authenticated.
 */
export function useMyPermissions(): MyPermissionsResult {
  const { user, isAuthenticated } = useAuth();
  const { currentOrganization } = useOrganization();

  const orgId = currentOrganization?.id ?? null;
  const userId = user?.id ?? null;

  const query = useQuery({
    queryKey: userId
      ? myPermissionsQueryKey(userId, orgId)
      : ["me", "permissions", "disabled"],
    queryFn: async () => {
      const result = await authService.getCurrentUser(orgId);
      if (!result.success || !result.user) {
        // Surface a typed error so the query is marked as failed (and
        // callers see isError instead of pretending loading finished).
        throw new Error(result.error ?? "Failed to load current user");
      }
      return result.user;
    },
    enabled: Boolean(isAuthenticated && userId),
    // Permissions are read on every nav render; cache them for 60s but
    // refetch in the background to keep them fresh on tab focus.
    staleTime: 60 * 1000,
    refetchOnWindowFocus: true,
  });

  const data = query.data as UserProfile | undefined;

  return {
    isLoading: query.isLoading,
    currentOrganizationId: data?.current_organization_id,
    permissions: data?.permissions ?? {},
  };
}

/**
 * Returns true if the current user has the given permission on the
 * current org. Wildcard `{"*": ["*"]}` (platform admins) makes every
 * check return true. Pass `null` to check "is the user signed in?"
 * (useful for nav items that should be visible to every signed-in user
 * regardless of org permissions).
 *
 * @returns
 *   - `null` while the query is loading.
 *   - `true` / `false` once the query resolves.
 *   - `false` (not `null`) when the user is signed out, so that nav
 *     components can render without special-casing the signed-out case.
 */
export function useHasPermission(perm: PermissionString | null): boolean | null {
  const { isAuthenticated } = useAuth();
  const { permissions, isLoading } = useMyPermissions();

  if (!isAuthenticated) return false;
  if (isLoading) return null;
  // No permission requirement -> visible to every signed-in user.
  if (perm === null) return true;

  return hasPermission(permissions, perm);
}

/**
 * Returns true if the current user has ANY of the given permissions.
 * Same null/false semantics as `useHasPermission`.
 */
export function useHasAnyPermission(
  perms: readonly PermissionString[],
): boolean | null {
  const { isAuthenticated } = useAuth();
  const { permissions, isLoading } = useMyPermissions();

  if (!isAuthenticated) return false;
  if (isLoading) return null;
  if (perms.length === 0) return false;

  return perms.some((p) => hasPermission(permissions, p));
}

// --- Pure helpers (exported for unit tests and direct use) ---

/** Check a single permission against a permissions map. */
export function hasPermission(
  permissions: ResourcePermissions,
  perm: PermissionString,
): boolean {
  if (!permissions) return false;
  // Wildcard: every permission is granted.
  if (permissions["*"]?.includes("*")) return true;
  const [resource, action] = perm.split(":", 2);
  if (!resource || !action) return false;
  return Boolean(permissions[resource]?.includes(action));
}
