/**
 * Canonical permission vocabulary for the platform (N1 contract).
 *
 * Source of truth for string names: the grants migration
 * `backend/alembic/versions/20260705000001_extend_org_admin_and_regular_user_grants.py`
 * plus the initial RBAC seed (`organization:*`, `billing:subscribe`, etc.).
 *
 * Format: `<resource>:<action>` (REST-style actions: read | create | update | delete).
 * Composite gates used by the nav:
 *   - `billing:manage` — org billing UI
 *   - `platform:admin` — platform admin section
 *   - `*:*` — platform admin wildcard (resolver only)
 *
 * Do NOT invent parallel names (`agent:write`, `member:invite`, `member:manage`,
 * `settings:*`). Those strings are not granted by the seed and will never pass
 * a real permission check.
 *
 * @see docs/tw-drafts/n1-architecture-review.md
 * @see docs/02_features/authentication_rbac/permission-matrix.md
 */

/** Resource names allowed by the permission contract. */
export const PERMISSION_RESOURCES = [
  "agent",
  "phone_number",
  "skill",
  "call_log",
  "member",
  "billing",
  "organization",
  "platform",
  "*",
] as const;

/** Action names allowed by the permission contract. */
export const PERMISSION_ACTIONS = [
  "read",
  "create",
  "update",
  "delete",
  "manage",
  "admin",
  "subscribe",
  "*",
] as const;

export type PermissionResource = (typeof PERMISSION_RESOURCES)[number];
export type PermissionAction = (typeof PERMISSION_ACTIONS)[number];

/** A permission string in the contract: `<resource>:<action>`. */
export type PermissionString = `${string}:${string}`;

/** Named constants for call sites (autocomplete + typo resistance). */
export const P = {
  agent: {
    read: "agent:read",
    create: "agent:create",
    update: "agent:update",
    delete: "agent:delete",
  },
  phoneNumber: {
    read: "phone_number:read",
    create: "phone_number:create",
    update: "phone_number:update",
    delete: "phone_number:delete",
  },
  skill: {
    read: "skill:read",
    create: "skill:create",
    update: "skill:update",
    delete: "skill:delete",
  },
  callLog: {
    read: "call_log:read",
  },
  member: {
    read: "member:read",
    create: "member:create",
    update: "member:update",
    delete: "member:delete",
  },
  billing: {
    manage: "billing:manage",
    subscribe: "billing:subscribe",
    read: "billing:read",
  },
  organization: {
    read: "organization:read",
    create: "organization:create",
    update: "organization:update",
    delete: "organization:delete",
  },
  platform: {
    admin: "platform:admin",
  },
  wildcard: "*:*",
} as const satisfies Record<string, Record<string, PermissionString> | PermissionString>;

/**
 * Returns true if `perm` is a well-formed contract string whose resource
 * and action are both in the allow-lists.
 */
export function isCanonicalPermission(perm: string): boolean {
  const [resource, action] = perm.split(":", 2);
  if (!resource || !action) return false;
  return (
    (PERMISSION_RESOURCES as readonly string[]).includes(resource) &&
    (PERMISSION_ACTIONS as readonly string[]).includes(action)
  );
}
