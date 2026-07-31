/**
 * Tests for the org page tab-redirect helper.
 *
 * Contract (mirrors docs/tw-drafts/navigation-redesign.md Section 6.5):
 *   - /organization?tab=phone-numbers -> /phone-numbers?org_id=<id>
 *   - /organization?tab=skills -> /skills?org_id=<id>
 *   - /organization?tab=ai-agent -> /agents?org_id=<id>
 *   - /organization?tab=overview (or no tab) renders the org page as
 *     before (no redirect).
 *   - When orgId is missing the page renders AccessDenied and the
 *     redirect must NOT fire.
 *
 * The redirect is performed client-side via the page's existing
 * searchParam useEffect so the change is self-contained (no
 * next.config.js redirect rule). The pure helper below is the
 * authoritative decision; the page just calls it.
 */
import { describe, expect, it } from "vitest";

import { legacyTabRedirect } from "../legacy-tab-redirect";

describe("legacyTabRedirect", () => {
  it("redirects ?tab=phone-numbers to /phone-numbers with org_id", () => {
    expect(legacyTabRedirect("phone-numbers", "org-1")).toBe(
      "/phone-numbers?org_id=org-1",
    );
  });

  it("redirects ?tab=skills to /skills with org_id", () => {
    expect(legacyTabRedirect("skills", "org-1")).toBe(
      "/skills?org_id=org-1",
    );
  });

  it("redirects ?tab=ai-agent to /agents with org_id", () => {
    expect(legacyTabRedirect("ai-agent", "org-1")).toBe(
      "/agents?org_id=org-1",
    );
  });

  it("does NOT redirect when tab=overview", () => {
    expect(legacyTabRedirect("overview", "org-1")).toBeNull();
  });

  it("does NOT redirect when tab is absent", () => {
    expect(legacyTabRedirect(null, "org-1")).toBeNull();
  });

  it("does NOT redirect when org_id is missing", () => {
    // AccessDenied handles this; we must not push to a new URL.
    expect(legacyTabRedirect("phone-numbers", null)).toBeNull();
  });

  it("does NOT redirect for the info tab (renders the org page)", () => {
    // `?tab=info` selects the Organization Info tab in-page — not a legacy
    // top-level route, so no redirect.
    expect(legacyTabRedirect("info", "org-1")).toBeNull();
  });

  it("does NOT redirect for the credentials tab (renders the org page)", () => {
    // `?tab=credentials` selects the Third-party API Credentials tab in-page.
    expect(legacyTabRedirect("credentials", "org-1")).toBeNull();
  });

  it("encodes the org id in the redirect URL", () => {
    // org ids can contain unusual characters; the URL must be safe.
    expect(legacyTabRedirect("skills", "org with space")).toBe(
      "/skills?org_id=org%20with%20space",
    );
  });

  it("forwards deep-link params (skill, file) through the skills redirect", () => {
    // N1 regression guard: a deep link like
    // /organization?tab=skills&skill=appointment-booking&file=references/faq.md
    // must land on /skills with skill+file preserved, so the SkillEditor can
    // restore the selected file. The `tab` param is consumed (not forwarded);
    // org_id is always re-emitted.
    const sp = new URLSearchParams("org_id=org-1&skill=appointment-booking&file=references/faq.md");
    expect(legacyTabRedirect("skills", "org-1", sp)).toBe(
      "/skills?org_id=org-1&skill=appointment-booking&file=references%2Ffaq.md",
    );
  });

  it("does not forward the consumed `tab` param", () => {
    const sp = new URLSearchParams("org_id=org-1&tab=skills&skill=x");
    expect(legacyTabRedirect("skills", "org-1", sp)).toBe(
      "/skills?org_id=org-1&skill=x",
    );
  });

  it("forwards deep-link params even when org_id is missing from searchParams", () => {
    // org_id comes from the page's own searchParams.get("org_id"); the helper
    // re-emits it from the `orgId` arg so the redirect is valid.
    const sp = new URLSearchParams("skill=x");
    expect(legacyTabRedirect("skills", "org-1", sp)).toBe(
      "/skills?org_id=org-1&skill=x",
    );
  });
});
