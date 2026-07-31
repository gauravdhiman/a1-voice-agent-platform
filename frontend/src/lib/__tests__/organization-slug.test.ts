import { describe, expect, it } from "vitest";
import {
  normalizeOrganizationSlug,
  publicOrgPagePath,
  suggestOrganizationSlugFromName,
  validateOrganizationSlug,
} from "@/lib/organization-slug";

describe("organization-slug helpers", () => {
  it("normalizes names into kebab-case", () => {
    expect(normalizeOrganizationSlug("  Acme Corp!  ")).toBe("acme-corp");
  });

  it("suggests slug from organization name", () => {
    expect(suggestOrganizationSlugFromName("Acme Support")).toBe("acme-support");
  });

  it("validates slug format", () => {
    expect(validateOrganizationSlug("acme-support")).toBeNull();
    expect(validateOrganizationSlug("Bad Slug")).not.toBeNull();
    expect(validateOrganizationSlug("api")).not.toBeNull();
  });

  it("builds public page path", () => {
    expect(publicOrgPagePath("acme")).toBe("/o/acme");
  });
});
