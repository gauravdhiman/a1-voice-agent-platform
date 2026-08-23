/**
 * Page-level permission facade over the N1 `/me.permissions` contract.
 *
 * Historically this hook OR'd hardcoded role checks with ad-hoc permission
 * strings (`member:invite`, `member:manage`, `settings:*`) that were never
 * granted by the DB seed. That made the permission branch dead code and
 * blocked Phase 2 custom roles from driving the UI.
 *
 * Current contract:
 *   - Boolean flags are derived from `useMyPermissions()` via the canonical
 *     vocabulary in `frontend/src/lib/permissions.ts`.
 *   - `isPlatformAdmin` / `isOrgAdmin` remain role-based (nav section gates
 *     and cross-org card actions still need roles).
 *   - Fail closed on error or while permissions are loading (no
 *     `NODE_ENV === "development"` grant-all fallback).
 *
 * @see docs/02_features/authentication_rbac/permission-matrix.md
 */
"use client";

import { useMemo } from "react";
import { useAuth } from "@/contexts/auth-context";
import { useOrganization } from "@/contexts/organization-context";
import {
  hasPermission,
  useMyPermissions,
  type PermissionString,
} from "@/hooks/use-has-permission";
import { P } from "@/lib/permissions";

export interface UserPermissions {
  // Organization-level
  canUpdateOrganization: boolean;
  canDeleteOrganization: boolean;
  canViewOrganization: boolean;

  // Member management
  canManageMembers: boolean;
  canViewMembers: boolean;
  canInviteMembers: boolean;
  canRemoveMembers: boolean;

  // Settings (mapped to organization:* — there is no settings resource)
  canUpdateSettings: boolean;
  canViewSettings: boolean;
  canManageBilling: boolean;

  // Workspace write gates (current org only)
  canCreateAgent: boolean;
  canUpdateAgent: boolean;
  canDeleteAgent: boolean;
  canManageSkills: boolean;
  canManagePhoneNumbers: boolean;

  // Call recordings (org admins; audio only, call log rows kept)
  canDeleteRecordings: boolean;

  // Role flags
  isPlatformAdmin: boolean;
  isOrgAdmin: boolean;

  /** True while the `/me` permissions query has no data yet. */
  isLoading: boolean;
}

const DENIED: UserPermissions = {
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
  canCreateAgent: false,
  canUpdateAgent: false,
  canDeleteAgent: false,
  canManageSkills: false,
  canManagePhoneNumbers: false,
  canDeleteRecordings: false,
  isPlatformAdmin: false,
  isOrgAdmin: false,
  isLoading: false,
};

/**
 * Derive boolean capability flags for the current org from the resolved
 * permissions map and role flags.
 */
export function useUserPermissions(): UserPermissions {
  const { user } = useAuth();
  const { currentOrganization } = useOrganization();
  const { permissions, isLoading } = useMyPermissions();

  return useMemo(() => {
    if (!user || !currentOrganization) {
      return { ...DENIED, isLoading };
    }

    const isPlatformAdmin = Boolean(user.hasRole("platform_admin"));
    const isOrgAdmin = Boolean(
      user.hasRole("org_admin", currentOrganization.id),
    );

    const check = (perm: PermissionString): boolean => {
      if (isPlatformAdmin) return true;
      // Fail closed while loading so write CTAs do not flash on for members.
      if (isLoading) return false;
      return hasPermission(permissions, perm);
    };

    const canInvite = check(P.member.create);
    const canUpdateMember = check(P.member.update);
    const canRemove = check(P.member.delete);

    return {
      canUpdateOrganization: check(P.organization.update),
      canDeleteOrganization: check(P.organization.delete),
      canViewOrganization: check(P.organization.read),
      canManageMembers: canInvite || canUpdateMember || canRemove,
      canViewMembers: check(P.member.read),
      canInviteMembers: canInvite,
      canRemoveMembers: canRemove,
      canUpdateSettings: check(P.organization.update),
      canViewSettings: check(P.organization.read),
      // billing:manage (N1 nav) OR billing:subscribe (legacy API seed)
      canManageBilling:
        check(P.billing.manage) || check(P.billing.subscribe),
      canCreateAgent: check(P.agent.create),
      canUpdateAgent: check(P.agent.update),
      canDeleteAgent: check(P.agent.delete),
      canManageSkills:
        check(P.skill.create) ||
        check(P.skill.update) ||
        check(P.skill.delete),
      canManagePhoneNumbers:
        check(P.phoneNumber.create) ||
        check(P.phoneNumber.update) ||
        check(P.phoneNumber.delete),
      canDeleteRecordings: check(P.callLog.delete),
      isPlatformAdmin,
      isOrgAdmin,
      isLoading,
    };
  }, [user, currentOrganization, permissions, isLoading]);
}
