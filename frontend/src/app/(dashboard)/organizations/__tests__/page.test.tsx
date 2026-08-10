/**
 * Tests for the platform-admin organization directory.
 *
 * The directory is the entry point for organization-scoped platform
 * operations. It must be unavailable to org admins even when they navigate
 * to the route directly.
 */
import React from "react";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockUseOrganization = vi.fn();
const mockUseUserPermissions = vi.fn();

vi.mock("@/contexts/organization-context", () => ({
  useOrganization: () => mockUseOrganization(),
}));

vi.mock("@/hooks/use-user-permissions", () => ({
  useUserPermissions: () => mockUseUserPermissions(),
}));

vi.mock("@/components/ui/access-denied", () => ({
  AccessDenied: ({
    title,
    description,
  }: {
    title: string;
    description: string;
  }) => (
    <div data-testid="access-denied">
      <span>{title}</span>
      <span>{description}</span>
    </div>
  ),
}));

vi.mock("@/components/organizations/organization-create-dialog", () => ({
  OrganizationCreateDialog: () => null,
}));

vi.mock("@/components/organizations/organization-edit-dialog", () => ({
  OrganizationEditDialog: () => null,
}));

vi.mock("@/components/organizations/organization-delete-dialog", () => ({
  OrganizationDeleteDialog: () => null,
}));

vi.mock("@/components/data-table/data-table", () => ({
  DataTable: () => <div data-testid="organizations-table" />,
}));

vi.mock("@/components/organizations/organizations-data-table-columns", () => ({
  organizationsColumns: [],
}));

import OrganizationsPage from "../page";

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

describe("/organizations page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseOrganization.mockReturnValue({
      organizations: [ORGANIZATION],
      loading: false,
      error: null,
      refreshOrganizations: vi.fn(),
    });
  });

  it("renders the organization directory for a platform admin", () => {
    mockUseUserPermissions.mockReturnValue({ isPlatformAdmin: true });

    render(<OrganizationsPage />);

    expect(
      screen.getByRole("heading", { name: "Organizations" }),
    ).toBeInTheDocument();
    expect(screen.getByTestId("organizations-table")).toBeInTheDocument();
    expect(screen.queryByTestId("access-denied")).not.toBeInTheDocument();
  });

  it("denies an org admin even when the route is opened directly", () => {
    mockUseUserPermissions.mockReturnValue({ isPlatformAdmin: false });

    render(<OrganizationsPage />);

    expect(screen.getByTestId("access-denied")).toBeInTheDocument();
    expect(screen.queryByTestId("organizations-table")).not.toBeInTheDocument();
  });
});
