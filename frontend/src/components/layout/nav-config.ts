/**
 * Navigation config for the dashboard layout.
 *
 * The single source of truth for the left-rail nav (N1). The layout
 * renders three sections, in this order:
 *
 *   1. **workspace** - items every signed-in user with a current org can
 *      see. Phone Numbers and Skills are first-class routes (no longer
 *      org-page tabs).
 *   2. **org_admin** - items only org admins (or platform admins) see.
 *   3. **platform_admin** - items only platform admins see. The section
 *      header is hidden entirely if no items in it pass the permission
 *      filter, so non-admins never see an empty heading.
 *
 * Section visibility is decided by SECTION_ROLES (the role gate). A
 * section is rendered only if the current user holds the section's
 * required role: WORKSPACE is always visible, ORG_ADMIN requires
 * `org_admin` (or `platform_admin` which inherits), PLATFORM_ADMIN
 * requires `platform_admin` only.
 *
 * Item visibility is decided by `requiredPermission` plus
 * `useHasPermission()` (see `frontend/src/hooks/use-has-permission.ts`).
 * An item with `requiredPermission: null` is visible to every
 * signed-in user; an item with a string is only rendered when the
 * user holds that permission on the current org context. The
 * wildcard `*:*` (granted to platform admins via the Phase 1 RBAC
 * seed) makes every item render.
 *
 * Adding a new item: append to the appropriate section array. The
 * test suite (`__tests__/nav-config.test.ts`) enforces invariants
 * on every entry, so a malformed `requiredPermission` will fail CI
 * rather than silently hide a nav item.
 */
import type { LucideIcon } from "lucide-react";
import {
  BookOpen,
  Building2,
  LayoutDashboard,
  Layers,
  Phone,
  PhoneCall,
  SlidersHorizontal,
  Users,
  UsersRound,
  Wallet,
  Wrench,
  Bell,
  Package,
  FileText,
} from "lucide-react";
import {
  PERMISSION_ACTIONS,
  PERMISSION_RESOURCES,
  type PermissionString,
} from "@/lib/permissions";

export type { PermissionString };
export { PERMISSION_ACTIONS, PERMISSION_RESOURCES };

/** Logical nav section. Rendered in the order declared in `NAV_SECTIONS`. */
export type NavSection = "workspace" | "org_admin" | "platform_admin";

/** A single nav item. */
export interface NavItem {
  /** Human-readable label rendered next to the icon. */
  name: string;
  /** Target route. */
  href: string;
  /** Stable key used by the product walkthrough to spotlight this item. */
  tourId: string;
  /** Icon shown in the collapsed and expanded sidebar. */
  icon: LucideIcon;
  /**
   * The permission the user must hold on the current org to see this
   * item. `null` means "visible to every signed-in user". The wildcard
   * `*:*` (granted to platform admins) makes every item visible.
   */
  requiredPermission: PermissionString | null;
  /**
   * Which section the item belongs to. Determines order and styling.
   * Order is fixed: workspace -> org_admin -> platform_admin.
   */
  section: NavSection;
  /**
   * Whether the active match is exact. Defaults to `true`. Set to `false`
   * for items that should be highlighted for any sub-path (e.g. an
   * "agents" item that stays highlighted on `/agents/123`).
   */
  exact?: boolean;
}

/** Per-section nav entries. Order within a section is render order. */
export const NAV_SECTIONS: Readonly<Record<NavSection, readonly NavItem[]>> = {
  workspace: [
    {
      name: "Home",
      href: "/dashboard",
      tourId: "home",
      icon: LayoutDashboard,
      // Visible to every signed-in user; no permission gate.
      requiredPermission: null,
      section: "workspace",
      exact: true,
    },
    {
      name: "Agents",
      href: "/agents",
      tourId: "agents",
      icon: UsersRound,
      requiredPermission: "agent:read",
      section: "workspace",
    },
    {
      name: "Phone Numbers",
      href: "/phone-numbers",
      tourId: "phone-numbers",
      icon: Phone,
      requiredPermission: "phone_number:read",
      section: "workspace",
    },
    {
      name: "Skills",
      href: "/skills",
      tourId: "skills",
      icon: BookOpen,
      requiredPermission: "skill:read",
      section: "workspace",
    },
    {
      name: "Calls",
      href: "/calls",
      tourId: "calls",
      icon: PhoneCall,
      requiredPermission: "call_log:read",
      section: "workspace",
    },
  ],
  org_admin: [
    {
      name: "Members",
      href: "/organization/members",
      tourId: "members",
      icon: Users,
      requiredPermission: "member:read",
      section: "org_admin",
    },
    {
      name: "Billing",
      href: "/organization/billing",
      tourId: "billing",
      icon: Wallet,
      requiredPermission: "billing:manage",
      section: "org_admin",
    },
    {
      name: "Organization",
      href: "/organization",
      tourId: "organization",
      icon: Building2,
      requiredPermission: "organization:read",
      section: "org_admin",
      exact: true,
    },
  ],
  platform_admin: [
    {
      name: "Organizations",
      href: "/organizations",
      tourId: "organizations",
      icon: Building2,
      requiredPermission: "platform:admin",
      section: "platform_admin",
    },
    {
      name: "All Users",
      href: "/users",
      tourId: "all-users",
      icon: Users,
      requiredPermission: "platform:admin",
      section: "platform_admin",
    },
    {
      name: "Platform Skills",
      href: "/platform/skills",
      tourId: "platform-skills",
      icon: Layers,
      requiredPermission: "platform:admin",
      section: "platform_admin",
    },
    {
      name: "Use Case Templates",
      href: "/platform/templates",
      tourId: "voice-templates",
      icon: FileText,
      requiredPermission: "platform:admin",
      section: "platform_admin",
    },
    {
      name: "Platform Tools",
      href: "/platform/tools",
      tourId: "platform-tools",
      icon: Wrench,
      requiredPermission: "platform:admin",
      section: "platform_admin",
    },
    {
      name: "Voice Presets",
      href: "/platform/presets",
      tourId: "voice-presets",
      icon: SlidersHorizontal,
      requiredPermission: "platform:admin",
      section: "platform_admin",
    },
    {
      name: "Notifications",
      href: "/platform/notifications",
      tourId: "notifications",
      icon: Bell,
      requiredPermission: "platform:admin",
      section: "platform_admin",
    },
    {
      name: "Phone Number Settings",
      href: "/platform/phone-numbers",
      tourId: "platform-phone-numbers",
      icon: Phone,
      requiredPermission: "platform:admin",
      section: "platform_admin",
    },
    {
      name: "Plan Catalog",
      href: "/platform/plans",
      tourId: "plan-catalog",
      icon: Package,
      requiredPermission: "platform:admin",
      section: "platform_admin",
    },
  ],
} as const;

/**
 * Flatten the sections into a single ordered list. Layouts can iterate
 * this directly when they want to render all items with section breaks
 * driven by the items themselves.
 */
export const ALL_NAV_ITEMS: readonly NavItem[] = [
  ...NAV_SECTIONS.workspace,
  ...NAV_SECTIONS.org_admin,
  ...NAV_SECTIONS.platform_admin,
];

/**
 * Required role for each section. The layout uses this to gate the
 * section heading (and the items inside it) by role rather than
 * purely by permission, so a regular user with the underlying
 * permissions never sees an "Org Admin" / "Platform Admin" heading
 * they can't actually use.
 *
 * Mapping (Option C in the N1 design doc):
 *   - workspace: visible to every signed-in user with a current org.
 *   - org_admin: visible to `org_admin` OR `platform_admin` (platform
 *     admins inherit the org_admin section because they can do
 *     anything an org admin can do).
 *   - platform_admin: visible to `platform_admin` only.
 *
 * `null` means "no role requirement".
 */
export const SECTION_ROLES: Readonly<
  Record<NavSection, "platform_admin" | "org_admin" | null>
> = {
  workspace: null,
  org_admin: "org_admin",
  platform_admin: "platform_admin",
} as const;
