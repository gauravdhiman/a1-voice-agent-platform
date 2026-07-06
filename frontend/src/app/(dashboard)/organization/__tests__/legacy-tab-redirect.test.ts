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

  it("encodes the org id in the redirect URL", () => {
    // org ids can contain unusual characters; the URL must be safe.
    expect(legacyTabRedirect("skills", "org with space")).toBe(
      "/skills?org_id=org%20with%20space",
    );
  });
});
