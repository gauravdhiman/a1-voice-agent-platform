/**
 * Tests for the OrganizationSwitcher sidebar widget.
 *
 * Contract (mirrors docs/tw-drafts/navigation-redesign.md Section 6.4):
 *   - Renders the current org name.
 *   - Renders the current org role badge (when one is provided).
 *   - Clicking the trigger opens a popover listing every org the user
 *     belongs to, with a "Switch" action per row.
 *   - The popover renders a "Create organization" entry at the bottom.
 *   - The switcher hides itself when the user has no orgs (the avatar
 *     dropdown handles that case).
 */
import React from "react";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

// radix popover relies on portal positioning; stub it to render inline.
vi.mock("@/components/ui/popover", () => ({
  Popover: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  PopoverTrigger: ({ children }: { children: React.ReactNode }) => (
    <>{children}</>
  ),
  PopoverContent: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="popover-content">{children}</div>
  ),
}));

const mockSetCurrentOrganization = vi.fn();
const mockUseOrganization = vi.fn();
vi.mock("@/contexts/organization-context", () => ({
  useOrganization: () => mockUseOrganization(),
}));

import { OrganizationSwitcher } from "../organization-switcher";

const ORG_A = {
  id: "org-a",
  name: "Acme",
  slug: "acme",
  description: null,
  website: null,
  is_active: true,
  onboarding_completed: true,
  created_at: "",
  updated_at: "",
};

const ORG_B = {
  id: "org-b",
  name: "Beta",
  slug: "beta",
  description: null,
  website: null,
  is_active: true,
  onboarding_completed: true,
  created_at: "",
  updated_at: "",
};

describe("OrganizationSwitcher", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the current org name", () => {
    mockUseOrganization.mockReturnValue({
      organizations: [ORG_A, ORG_B],
      currentOrganization: ORG_A,
      setCurrentOrganization: mockSetCurrentOrganization,
    });

    render(<OrganizationSwitcher currentRole="org_admin" />);

    // The current org name shows in the trigger AND the popover; assert
    // it appears at least once.
    const matches = screen.getAllByText("Acme");
    expect(matches.length).toBeGreaterThan(0);
  });

  it("renders the current org role badge when one is provided", () => {
    mockUseOrganization.mockReturnValue({
      organizations: [ORG_A, ORG_B],
      currentOrganization: ORG_A,
      setCurrentOrganization: mockSetCurrentOrganization,
    });

    render(<OrganizationSwitcher currentRole="org_admin" />);

    // The role name is rendered as a badge in the trigger and the popover.
    const all = screen.getAllByText(/org admin/i);
    expect(all.length).toBeGreaterThan(0);
  });

  it("renders nothing when the user has no current org", () => {
    mockUseOrganization.mockReturnValue({
      organizations: [],
      currentOrganization: null,
      setCurrentOrganization: mockSetCurrentOrganization,
    });

    const { container } = render(
      <OrganizationSwitcher currentRole="member" />,
    );

    // No current org -> nothing to switch to. The component renders an
    // empty fragment, so the wrapper is empty.
    expect(container).toBeEmptyDOMElement();
  });

  it("lists every org the user belongs to in the popover content", async () => {
    const user = userEvent.setup();
    mockUseOrganization.mockReturnValue({
      organizations: [ORG_A, ORG_B],
      currentOrganization: ORG_A,
      setCurrentOrganization: mockSetCurrentOrganization,
    });

    render(<OrganizationSwitcher currentRole="org_admin" />);

    // The popover content is always rendered (mocked as inline).
    const popover = screen.getByTestId("popover-content");
    expect(within(popover).getByText("Acme")).toBeInTheDocument();
    expect(within(popover).getByText("Beta")).toBeInTheDocument();
  });

  it("renders a 'Create organization' entry in the popover", () => {
    mockUseOrganization.mockReturnValue({
      organizations: [ORG_A],
      currentOrganization: ORG_A,
      setCurrentOrganization: mockSetCurrentOrganization,
    });

    render(<OrganizationSwitcher currentRole="org_admin" />);

    const popover = screen.getByTestId("popover-content");
    expect(
      within(popover).getByText(/create organization/i),
    ).toBeInTheDocument();
  });

  it("clicking the 'Switch' action on a row calls setCurrentOrganization", async () => {
    const user = userEvent.setup();
    mockUseOrganization.mockReturnValue({
      organizations: [ORG_A, ORG_B],
      currentOrganization: ORG_A,
      setCurrentOrganization: mockSetCurrentOrganization,
    });

    render(<OrganizationSwitcher currentRole="org_admin" />);

    // Find the row for ORG_B and click its switch action.
    const popover = screen.getByTestId("popover-content");
    const rowB = within(popover).getByText("Beta").closest("[data-row]");
    if (!rowB) {
      throw new Error("expected the ORG_B row to be wrapped in [data-row]");
    }
    const switchButton = within(rowB as HTMLElement).getByRole("button", {
      name: /switch/i,
    });
    await user.click(switchButton);

    expect(mockSetCurrentOrganization).toHaveBeenCalledWith(ORG_B);
  });

  it("marks the current org row as active (no Switch button on it)", () => {
    mockUseOrganization.mockReturnValue({
      organizations: [ORG_A, ORG_B],
      currentOrganization: ORG_A,
      setCurrentOrganization: mockSetCurrentOrganization,
    });

    render(<OrganizationSwitcher currentRole="org_admin" />);

    const popover = screen.getByTestId("popover-content");
    const rowA = within(popover).getByText("Acme").closest("[data-row]");
    if (!rowA) {
      throw new Error("expected the ORG_A row to be wrapped in [data-row]");
    }
    // The active row is the current org; it should not offer a Switch
    // action (you can't switch to the org you're already on).
    expect(
      within(rowA as HTMLElement).queryByRole("button", { name: /switch/i }),
    ).not.toBeInTheDocument();
  });
});
