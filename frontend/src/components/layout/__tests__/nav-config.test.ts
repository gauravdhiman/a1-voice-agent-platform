/**
 * Tests for the navigation config.
 *
 * Contract (mirrors docs/tw-drafts/navigation-redesign.md Section 6.2):
 *   - Every entry has a `requiredPermission` field (`null` is allowed for
 *     workspace-agnostic items like the home page and settings).
 *   - Every `requiredPermission` is either `null` or one of the strings
 *     declared in the permission contract.
 *   - Sections appear in the order: workspace -> org_admin -> platform_admin.
 *   - The `*` wildcard is reserved for platform admins and MUST NOT appear
 *     as a `requiredPermission` on a nav item (use the explicit resource
 *     + action for clarity in the nav).
 */
import { describe, expect, it } from "vitest";

import {
  NAV_SECTIONS,
  PERMISSION_ACTIONS,
  PERMISSION_RESOURCES,
  SECTION_ROLES,
  type NavItem,
  type NavSection,
} from "../nav-config";

// All valid permission strings, in the form `${resource}:${action}`.
const VALID_PERMISSIONS: ReadonlySet<string> = new Set(
  PERMISSION_RESOURCES.flatMap((resource) =>
    resource === "*"
      ? PERMISSION_ACTIONS.map((action) => `${resource}:${action}`)
      : PERMISSION_ACTIONS.map((action) => `${resource}:${action}`),
  ),
);

function isWellFormedPermission(value: string): boolean {
  // The contract format is `<resource>:<action>`. Two non-empty parts.
  const [resource, action] = value.split(":", 2);
  if (!resource || !action) return false;
  return (
    (PERMISSION_RESOURCES as readonly string[]).includes(resource) &&
    (PERMISSION_ACTIONS as readonly string[]).includes(action)
  );
}

describe("nav-config", () => {
  it("declares at least one item per section", () => {
    // Every section has at least one entry, otherwise the section header
    // would render but be empty.
    const sections: NavSection[] = ["workspace", "org_admin", "platform_admin"];
    for (const section of sections) {
      const items = NAV_SECTIONS[section];
      expect(
        items.length,
        `section ${section} should have items`,
      ).toBeGreaterThan(0);
    }
  });

  it("every nav item has a requiredPermission field (null allowed)", () => {
    const all: NavItem[] = [
      ...NAV_SECTIONS.workspace,
      ...NAV_SECTIONS.org_admin,
      ...NAV_SECTIONS.platform_admin,
    ];
    for (const item of all) {
      // null is the documented value for items visible to every signed-in user.
      // Anything else must be a non-empty string.
      expect(
        item.requiredPermission === null ||
          (typeof item.requiredPermission === "string" &&
            item.requiredPermission.length > 0),
        `${item.name} must declare requiredPermission as null or a non-empty string`,
      ).toBe(true);
    }
  });

  it("every requiredPermission is null or a valid `<resource>:<action>` string", () => {
    const all: NavItem[] = [
      ...NAV_SECTIONS.workspace,
      ...NAV_SECTIONS.org_admin,
      ...NAV_SECTIONS.platform_admin,
    ];
    for (const item of all) {
      if (item.requiredPermission === null) continue;
      expect(
        isWellFormedPermission(item.requiredPermission),
        `${item.name} has invalid permission: ${item.requiredPermission}`,
      ).toBe(true);
      expect(
        VALID_PERMISSIONS.has(item.requiredPermission),
        `${item.name} permission ${item.requiredPermission} must come from the contract`,
      ).toBe(true);
    }
  });

  it("the wildcard `*` is not used as a requiredPermission on any nav item", () => {
    // The wildcard means "every permission" - using it as a gate on a
    // single nav item would be misleading. The hook already grants the
    // wildcard to platform admins, so the `platform:admin` permission
    // string is the correct gate for platform-admin-only items.
    const all: NavItem[] = [
      ...NAV_SECTIONS.workspace,
      ...NAV_SECTIONS.org_admin,
      ...NAV_SECTIONS.platform_admin,
    ];
    for (const item of all) {
      if (item.requiredPermission === null) continue;
      expect(
        !item.requiredPermission.startsWith("*:"),
        `${item.name} uses the wildcard as a permission gate; use the explicit resource/action instead`,
      ).toBe(true);
    }
  });

  it("sections are in the order: workspace, org_admin, platform_admin", () => {
    // Order is enforced by the literal object key order. We assert it
    // here so a future re-sort cannot silently break the layout.
    expect(Object.keys(NAV_SECTIONS)).toEqual([
      "workspace",
      "org_admin",
      "platform_admin",
    ]);
  });

  it("each item has a unique href within its section", () => {
    for (const section of [
      "workspace",
      "org_admin",
      "platform_admin",
    ] as const) {
      const hrefs = NAV_SECTIONS[section].map((i) => i.href);
      expect(new Set(hrefs).size, `duplicate href in ${section}`).toBe(
        hrefs.length,
      );
    }
  });

  it("workspace section contains the canonical top-level items", () => {
    const names = NAV_SECTIONS.workspace.map((i) => i.name);
    // These are the items the design doc calls out as workspace-agnostic.
    expect(names).toContain("Home");
    expect(names).toContain("Agents");
    expect(names).toContain("Phone Numbers");
    expect(names).toContain("Skills");
    expect(names).toContain("Calls");
    expect(names).toContain("Callbacks");
  });

  it("org_admin section contains Members, Billing, Organization", () => {
    const names = NAV_SECTIONS.org_admin.map((i) => i.name);
    expect(names).toContain("Members");
    expect(names).toContain("Billing");
    expect(names).toContain("Organization");
  });

  it("platform_admin section contains Organizations and the platform catalogs", () => {
    const names = NAV_SECTIONS.platform_admin.map((i) => i.name);
    expect(names).toContain("Organizations");
    expect(names).toContain("All Users");
    expect(names).toContain("Platform Skills");
    expect(names).toContain("Platform Tools");
    expect(names).toContain("Voice Presets");
    expect(names).toContain("Use Case Templates");
    expect(names).toContain("Notifications");
    expect(names).toContain("Plan Catalog");
    expect(names).not.toContain("Entitlements");
  });

  it("SECTION_ROLES maps every nav section to a role or null", () => {
    // Every section key declared in NAV_SECTIONS must have a
    // corresponding entry in SECTION_ROLES. A missing key would
    // mean the layout falls back to showing the section to every
    // signed-in user, which is exactly what Option C is trying
    // to prevent.
    const navSectionKeys = Object.keys(NAV_SECTIONS) as NavSection[];
    const roleKeys = Object.keys(SECTION_ROLES) as NavSection[];
    expect(new Set(roleKeys)).toEqual(new Set(navSectionKeys));
  });

  it("SECTION_ROLES.platform_admin is strictly platform_admin", () => {
    // The platform_admin section is the most privileged; granting
    // it a less-restrictive role here would silently give every
    // org_admin access to /users and /platform/skills (which are
    // hard role-gated on the backend, so they'd just see Access
    // Denied). Lock the contract: only platform_admin sees it.
    expect(SECTION_ROLES.platform_admin).toBe("platform_admin");
  });

  it("SECTION_ROLES.org_admin is org_admin (platform_admin inherits)", () => {
    // The org_admin section is shown to org_admin. The layout
    // also grants it to platform_admin via the inheritance rule
    // in `NavSectionGroup` (a platform admin can do anything an
    // org admin can do, so they see the section too). This test
    // pins the base required role; the inheritance is tested
    // in the dashboard-layout suite.
    expect(SECTION_ROLES.org_admin).toBe("org_admin");
  });

  it("SECTION_ROLES.workspace is null (no role requirement)", () => {
    // The workspace section is the always-visible base layer.
    // If this ever becomes non-null, every signed-in user
    // would lose the workspace nav, which is a regression.
    expect(SECTION_ROLES.workspace).toBeNull();
  });
});
