import { describe, expect, it } from "vitest";

import { buildTabHref, resolveTab } from "../tab-state";

const tabs = ["plans", "entitlements", "usage"] as const;

describe("tab navigation state", () => {
  it("resolves a supported URL tab and falls back for missing or unknown values", () => {
    expect(resolveTab("usage", tabs, "plans")).toBe("usage");
    expect(resolveTab(null, tabs, "plans")).toBe("plans");
    expect(resolveTab("unknown", tabs, "plans")).toBe("plans");
  });

  it("builds a deep link while preserving unrelated query parameters", () => {
    expect(
      buildTabHref(
        "/platform/plans",
        "org_id=org-123&tab=plans",
        "usage",
        "plans",
      ),
    ).toBe("/platform/plans?org_id=org-123&tab=usage");
  });

  it("omits the default tab from the URL", () => {
    expect(
      buildTabHref("/platform/plans", "org_id=org-123&tab=usage", "plans", "plans"),
    ).toBe("/platform/plans?org_id=org-123");
  });
});
