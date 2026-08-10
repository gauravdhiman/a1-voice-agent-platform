/**
 * Tests for platform-admin organization row actions.
 *
 * The credits action is deliberately attached to the platform organization
 * directory rather than the organization Billing page, where it could be
 * mistaken for an org-admin operation.
 */
import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/components/ui/dropdown-menu", () => ({
  DropdownMenu: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
  DropdownMenuContent: ({ children }: { children: React.ReactNode }) => (
    <div role="menu">{children}</div>
  ),
  DropdownMenuItem: ({ children }: { children: React.ReactNode }) => (
    <div role="menuitem">{children}</div>
  ),
  DropdownMenuLabel: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
  DropdownMenuSeparator: () => <hr />,
  DropdownMenuTrigger: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
}));

import { organizationsColumns } from "../organizations-data-table-columns";

const ORGANIZATION = {
  id: "org-1",
  name: "Acme",
  description: null,
  slug: "acme",
  website: null,
  is_active: true,
  onboarding_completed: true,
  created_at: "2026-08-01T00:00:00Z",
  updated_at: "2026-08-01T00:00:00Z",
};

describe("organizationsColumns platform actions", () => {
  it("links the organization row to platform credits and entitlements", () => {
    const actionsColumn = organizationsColumns.find(
      (column) => column.id === "actions",
    );

    if (!actionsColumn || typeof actionsColumn.cell !== "function") {
      throw new Error("Organization actions column is not configured");
    }

    const actionCell = actionsColumn.cell as (props: {
      row: { original: typeof ORGANIZATION };
    }) => React.ReactNode;

    render(actionCell({ row: { original: ORGANIZATION } }));

    expect(
      screen.getByRole("link", { name: /credits & entitlements/i }),
    ).toHaveAttribute("href", "/organizations/credits?org_id=org-1");
  });
});
