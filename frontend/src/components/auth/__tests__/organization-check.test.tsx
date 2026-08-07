import React from "react";
import { render, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMockOrganization } from "../../../../tests/utils/data-factories";

const replaceMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: replaceMock }),
}));

const useAuthMock = vi.fn();
const useOrganizationMock = vi.fn();

vi.mock("@/contexts/auth-context", () => ({
  useAuth: () => useAuthMock(),
}));

vi.mock("@/contexts/organization-context", () => ({
  useOrganization: () => useOrganizationMock(),
}));

import { OrganizationCheck } from "@/components/auth/organization-check";

describe("OrganizationCheck", () => {
  beforeEach(() => {
    replaceMock.mockReset();
  });

  it("sends org admins of an unfinished org to onboarding", async () => {
    const unfinished = createMockOrganization({
      id: "org-1",
      onboarding_completed: false,
      slug: "adas-organization",
      description: null,
    });

    useAuthMock.mockReturnValue({
      user: {
        id: "user-1",
        hasRole: (role: string, orgId?: string) =>
          role === "org_admin" && orgId === "org-1",
      },
      loading: false,
    });
    useOrganizationMock.mockReturnValue({
      organizations: [unfinished],
      currentOrganization: unfinished,
      loading: false,
      error: null,
      refreshOrganizations: vi.fn(),
    });

    render(
      <OrganizationCheck>
        <div>dashboard</div>
      </OrganizationCheck>,
    );

    await waitFor(() => {
      expect(replaceMock).toHaveBeenCalledWith("/onboarding");
    });
  });

  it("does not send invited regular users to onboarding", async () => {
    const invitedOrg = createMockOrganization({
      id: "org-invited",
      name: "Acme Plumbing",
      slug: "acme-plumbing",
      description: "Real org",
      onboarding_completed: false,
    });

    useAuthMock.mockReturnValue({
      user: {
        id: "user-invitee",
        hasRole: (role: string) => role === "regular_user",
      },
      loading: false,
    });
    useOrganizationMock.mockReturnValue({
      organizations: [invitedOrg],
      currentOrganization: invitedOrg,
      loading: false,
      error: null,
      refreshOrganizations: vi.fn(),
    });

    const { findByText } = render(
      <OrganizationCheck>
        <div>dashboard</div>
      </OrganizationCheck>,
    );

    expect(await findByText("dashboard")).toBeTruthy();
    expect(replaceMock).not.toHaveBeenCalledWith("/onboarding");
  });

  it("allows access when the current org has completed onboarding", async () => {
    const onboarded = createMockOrganization({
      id: "org-ready",
      onboarding_completed: true,
      slug: "acme-plumbing",
      description: "Real org",
    });

    useAuthMock.mockReturnValue({
      user: {
        id: "user-1",
        hasRole: (role: string, orgId?: string) =>
          role === "org_admin" && orgId === "org-ready",
      },
      loading: false,
    });
    useOrganizationMock.mockReturnValue({
      organizations: [onboarded],
      currentOrganization: onboarded,
      loading: false,
      error: null,
      refreshOrganizations: vi.fn(),
    });

    const { findByText } = render(
      <OrganizationCheck>
        <div>dashboard</div>
      </OrganizationCheck>,
    );

    expect(await findByText("dashboard")).toBeTruthy();
    expect(replaceMock).not.toHaveBeenCalledWith("/onboarding");
  });
});
