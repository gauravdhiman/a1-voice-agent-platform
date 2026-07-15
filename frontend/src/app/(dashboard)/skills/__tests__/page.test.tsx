/**
 * Tests for the top-level /skills page.
 *
 * Contract (mirrors docs/tw-drafts/navigation-redesign.md Section 6.5):
 *   - The page renders the existing OrganizationSkillsTab component.
 *   - The component receives the current orgId (from the `?org_id=...`
 *     search param, falling back to the currentOrganization from context).
 *   - canCreate/canEdit are derived from the user's permissions.
 */
import React from "react";
import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

declare global {
  // eslint-disable-next-line no-var
  var __skillsSearchParams: string | undefined;
}

const mockUseOrganization = vi.fn();
const mockUseUserPermissions = vi.fn();
const mockPush = vi.fn();
const mockReplace = vi.fn();

vi.mock("@/contexts/organization-context", () => ({
  useOrganization: () => mockUseOrganization(),
}));

vi.mock("@/hooks/use-user-permissions", () => ({
  useUserPermissions: () => mockUseUserPermissions(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
    replace: mockReplace,
    prefetch: vi.fn(),
    back: vi.fn(),
  }),
  useSearchParams: () => new URLSearchParams(globalThis.__skillsSearchParams ?? ""),
  usePathname: () => "/skills",
}));

// Stub OrganizationSkillsTab to a simple marker so the test can assert
// the props we pass.
vi.mock("@/components/skills/organization-skills-tab", () => ({
  OrganizationSkillsTab: ({
    orgId,
    canCreate,
    canEdit,
  }: {
    orgId: string;
    canCreate: boolean;
    canEdit: boolean;
  }) => (
    <div
      data-testid="org-skills-tab"
      data-org-id={orgId}
      data-can-create={canCreate ? "true" : "false"}
      data-can-edit={canEdit ? "true" : "false"}
    />
  ),
}));

import SkillsPage from "../page";

describe("/skills page (N1)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    globalThis.__skillsSearchParams = "org_id=org-1";
    mockUseOrganization.mockReturnValue({
      organizations: [],
      currentOrganization: null,
      setCurrentOrganization: vi.fn(),
    });
  });

  afterEach(() => {
    delete globalThis.__skillsSearchParams;
  });

  it("renders the OrganizationSkillsTab with the org id from the URL", () => {
    mockUseUserPermissions.mockReturnValue({
      canManageSkills: true,
      isPlatformAdmin: false,
      isOrgAdmin: true,
    });

    render(<SkillsPage />);

    const tab = screen.getByTestId("org-skills-tab");
    expect(tab.getAttribute("data-org-id")).toBe("org-1");
  });

  it("falls back to the currentOrganization from context when ?org_id is missing", () => {
    delete globalThis.__skillsSearchParams;
    mockUseOrganization.mockReturnValue({
      organizations: [],
      currentOrganization: {
        id: "org-from-ctx",
        name: "Acme",
        slug: "acme",
        description: null,
        website: null,
        is_active: true,
        onboarding_completed: true,
        created_at: "",
        updated_at: "",
      },
      setCurrentOrganization: vi.fn(),
    });
    mockUseUserPermissions.mockReturnValue({
      canManageSkills: true,
      isPlatformAdmin: false,
      isOrgAdmin: true,
    });

    render(<SkillsPage />);

    const tab = screen.getByTestId("org-skills-tab");
    expect(tab.getAttribute("data-org-id")).toBe("org-from-ctx");
  });

  it("grants create+edit to org admins", () => {
    mockUseUserPermissions.mockReturnValue({
      canManageSkills: true,
      isPlatformAdmin: false,
      isOrgAdmin: true,
    });

    render(<SkillsPage />);

    const tab = screen.getByTestId("org-skills-tab");
    expect(tab.getAttribute("data-can-create")).toBe("true");
    expect(tab.getAttribute("data-can-edit")).toBe("true");
  });

  it("grants create+edit to platform admins", () => {
    mockUseUserPermissions.mockReturnValue({
      canManageSkills: true,
      isPlatformAdmin: true,
      isOrgAdmin: false,
    });

    render(<SkillsPage />);

    const tab = screen.getByTestId("org-skills-tab");
    expect(tab.getAttribute("data-can-create")).toBe("true");
    expect(tab.getAttribute("data-can-edit")).toBe("true");
  });

  it("denies create+edit to regular members", () => {
    mockUseUserPermissions.mockReturnValue({
      canManageSkills: false,
      isPlatformAdmin: false,
      isOrgAdmin: false,
    });

    render(<SkillsPage />);

    const tab = screen.getByTestId("org-skills-tab");
    expect(tab.getAttribute("data-can-create")).toBe("false");
    expect(tab.getAttribute("data-can-edit")).toBe("false");
  });

  it("renders a 'select an organization' state when no org is in scope", () => {
    delete globalThis.__skillsSearchParams;
    mockUseUserPermissions.mockReturnValue({
      canManageSkills: true,
      isPlatformAdmin: false,
      isOrgAdmin: true,
    });
    mockUseOrganization.mockReturnValue({
      organizations: [],
      currentOrganization: null,
      setCurrentOrganization: vi.fn(),
    });

    render(<SkillsPage />);

    expect(
      screen.getByText(/select an organization/i),
    ).toBeInTheDocument();
  });
});
