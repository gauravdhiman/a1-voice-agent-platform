import { describe, expect, it } from "vitest";
import {
  PRODUCT_TOUR_VERSION,
  clearProductTourStatus,
  getProductTourStorageKey,
  getProductTourRole,
  getProductTourBranchRoute,
  getProductTourBranchSteps,
  getProductTourBranchForPath,
  getProductTourSteps,
  readProductTourStatus,
  writeProductTourStatus,
} from "@/lib/product-tour";

describe("product tour role resolution", () => {
  it("prioritizes platform admin over organization admin", () => {
    expect(
      getProductTourRole({ isPlatformAdmin: true, isOrgAdmin: true }),
    ).toBe("platform_admin");
    expect(
      getProductTourRole({ isPlatformAdmin: false, isOrgAdmin: true }),
    ).toBe("org_admin");
    expect(
      getProductTourRole({ isPlatformAdmin: false, isOrgAdmin: false }),
    ).toBe("member");
  });
});

describe("product tour step definitions", () => {
  it("keeps the regular-user walkthrough focused on workspace capabilities", () => {
    const steps = getProductTourSteps("member");

    expect(steps.map((step) => step.id)).toEqual([
      "welcome",
      "organization-switcher",
      "agents",
      "phone-numbers",
      "skills",
      "calls",
      "user-menu",
    ]);
    expect(steps.every((step) => step.target && step.content)).toBe(true);
  });

  it("adds organization management steps for org admins", () => {
    const ids = getProductTourSteps("org_admin").map((step) => step.id);

    expect(ids).toEqual([
      "welcome",
      "organization-switcher",
      "agents",
      "phone-numbers",
      "skills",
      "calls",
      "members",
      "billing",
      "organization",
      "user-menu",
    ]);
  });

  it("adds the complete platform catalog for platform users", () => {
    const ids = getProductTourSteps("platform_admin").map((step) => step.id);

    expect(ids).toEqual([
      "welcome",
      "organization-switcher",
      "agents",
      "phone-numbers",
      "skills",
      "calls",
      "members",
      "billing",
      "organization",
      "organizations",
      "all-users",
      "platform-skills",
      "platform-tools",
      "voice-presets",
      "notifications",
      "platform-phone-numbers",
      "plan-catalog",
      "user-menu",
    ]);
  });

  it("uses stable, unique selectors so steps can be inserted safely", () => {
    for (const role of ["member", "org_admin", "platform_admin"] as const) {
      const steps = getProductTourSteps(role);
      const ids = steps.map((step) => step.id);
      const targets = steps.map((step) => step.target);

      expect(new Set(ids).size).toBe(ids.length);
      expect(new Set(targets).size).toBe(targets.length);
      expect(
        steps.every((step) => step.target.startsWith("[data-tour=")),
      ).toBe(true);
    }
  });

  it("provides role-aware in-context branches for agents, calls, and skills", () => {
    expect(getProductTourBranchRoute("agents")).toBe("/agents");
    expect(getProductTourBranchRoute("calls")).toBe("/calls");
    expect(getProductTourBranchRoute("skills")).toBe("/skills");

    expect(getProductTourBranchSteps("agents", "member").map((step) => step.id)).toEqual([
      "agents-overview",
      "agents-view-toggle",
      "agents-filters",
      "agents-results",
    ]);
    expect(getProductTourBranchSteps("agents", "org_admin").map((step) => step.id)).toContain(
      "agents-create",
    );
    expect(getProductTourBranchSteps("skills", "member").map((step) => step.id)).not.toContain(
      "skills-add",
    );
  });

  it("resolves contextual walkthroughs from the current page", () => {
    expect(getProductTourBranchForPath("/agents")).toBe("agents");
    expect(getProductTourBranchForPath("/calls")).toBe("calls");
    expect(getProductTourBranchForPath("/skills")).toBe("skills");
    expect(getProductTourBranchForPath("/agents/agent-123")).toBe(
      "agent-details",
    );
    expect(getProductTourBranchForPath("/agents/create")).toBeNull();
    expect(getProductTourBranchForPath("/settings")).toBeNull();
  });
});

describe("product tour persistence", () => {
  it("scopes the status key to the user and tour version", () => {
    expect(getProductTourStorageKey("user-123")).toBe(
      `24x7-ai.product-tour.${PRODUCT_TOUR_VERSION}.member.user-123`,
    );
    expect(getProductTourStorageKey("user-123", "platform_admin")).not.toBe(
      getProductTourStorageKey("user-123"),
    );
    expect(getProductTourStorageKey("user-123", "member", "agents")).toBe(
      `24x7-ai.product-tour.${PRODUCT_TOUR_VERSION}.member.user-123.agents`,
    );
  });

  it("reads and writes a user's completion state", () => {
    const values = new Map<string, string>();
    const storage = {
      getItem: (key: string) => values.get(key) ?? null,
      removeItem: (key: string) => values.delete(key),
      setItem: (key: string, value: string) => values.set(key, value),
    };

    expect(readProductTourStatus(storage, "user-123")).toBeNull();

    writeProductTourStatus(storage, "user-123", "skipped");
    expect(readProductTourStatus(storage, "user-123")).toBe("skipped");

    expect(readProductTourStatus(storage, "user-123", "org_admin")).toBeNull();

    writeProductTourStatus(storage, "user-123", "completed");
    expect(readProductTourStatus(storage, "user-123")).toBe("completed");

    clearProductTourStatus(storage, "user-123");
    expect(readProductTourStatus(storage, "user-123")).toBeNull();
  });

  it("ignores invalid stored statuses", () => {
    const storage = {
      getItem: () => "not-a-status",
      setItem: () => undefined,
    };

    expect(readProductTourStatus(storage, "user-123")).toBeNull();
  });
});
