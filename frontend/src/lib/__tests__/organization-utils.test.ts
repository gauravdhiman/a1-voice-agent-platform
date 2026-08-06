import { describe, expect, it } from "vitest";
import { selectPreferredOrganization } from "@/lib/organization-utils";
import { createMockOrganization } from "../../../tests/utils/data-factories";

describe("selectPreferredOrganization", () => {
  const personalOrg = createMockOrganization({
    id: "personal-1",
    name: "Ada's Organization",
    slug: "adas-organization",
    onboarding_completed: false,
  });

  const invitedOrg = createMockOrganization({
    id: "invited-1",
    name: "Acme Plumbing",
    slug: "acme-plumbing",
    onboarding_completed: true,
  });

  it("returns null for an empty list", () => {
    expect(selectPreferredOrganization([])).toBeNull();
  });

  it("prefers the invited organization over a saved selection", () => {
    const preferred = selectPreferredOrganization(
      [personalOrg, invitedOrg],
      "personal-1",
      { preferredOrganizationId: "invited-1" },
    );
    expect(preferred?.id).toBe("invited-1");
  });

  it("honors a saved selection when no invite preference is set", () => {
    const preferred = selectPreferredOrganization(
      [personalOrg, invitedOrg],
      "personal-1",
    );
    expect(preferred?.id).toBe("personal-1");
  });

  it("falls back to the first organization", () => {
    const preferred = selectPreferredOrganization([personalOrg, invitedOrg]);
    expect(preferred?.id).toBe("personal-1");
  });

  it("ignores an invite preference that is not in the membership list", () => {
    const preferred = selectPreferredOrganization([personalOrg], null, {
      preferredOrganizationId: "missing-org",
    });
    expect(preferred?.id).toBe("personal-1");
  });
});
