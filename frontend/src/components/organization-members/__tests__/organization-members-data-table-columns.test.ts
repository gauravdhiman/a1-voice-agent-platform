/**
 * Tests for the organization members data table columns factory
 * (N1 follow-up #1 — per-row Actions gate).
 *
 * Contract:
 *   - The factory is now `organizationMembersColumns(canManage: boolean)`
 *     (it used to be a static array).
 *   - When `canManage=true`: the columns include the "actions" column
 *     with the DropdownMenu (Edit Roles / View Profile / Remove Member).
 *   - When `canManage=false`: the columns DO NOT include the "actions"
 *     column. A regular org member must not see any per-row Actions UI.
 *
 * The page-level wire-up is tested in
 * `frontend/src/app/(dashboard)/organization/members/__tests__/page.test.tsx`.
 */
import { describe, expect, it } from "vitest";
import { organizationMembersColumns } from "../organization-members-data-table-columns";

describe("organizationMembersColumns (N1 #1 — per-row Actions gate)", () => {
  it("includes the 'actions' column when canManage=true", () => {
    const cols = organizationMembersColumns(true);
    const ids = cols.map((c) => c.id);
    expect(ids).toContain("actions");
  });

  it("OMITS the 'actions' column when canManage=false (CRIT — read-only user)", () => {
    const cols = organizationMembersColumns(false);
    const ids = cols.map((c) => c.id);
    expect(
      ids,
      "regular member must not see per-row Actions column (no Edit Roles / Remove Member UI)",
    ).not.toContain("actions");
  });

  it("keeps the read-only columns (select, member, role, status, joined) regardless of canManage", () => {
    const cols = organizationMembersColumns(false);
    const ids = cols.map((c) => c.id);
    expect(ids).toContain("select");
    expect(ids).toContain("member");
    expect(ids).toContain("status");
    // The Role column has accessorKey: "roles" (no explicit id).
    // `accessorKey` only exists on data-column variants of ColumnDef,
    // so narrow with `in` before reading it.
    expect(cols.some((c) => "accessorKey" in c && c.accessorKey === "roles")).toBe(true);
    // The Joined column has accessorKey: "created_at".
    expect(cols.some((c) => "accessorKey" in c && c.accessorKey === "created_at")).toBe(true);
  });
});
