import { describe, expect, it, vi, beforeEach } from "vitest";
import {
  getPublicAccessTokenKey,
  publicOrgPageService,
  readStoredAccessToken,
  storeAccessToken,
} from "@/services/public-org-page-service";

describe("publicOrgPageService", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    sessionStorage.clear();
  });

  it("stores and reads access token per slug", () => {
    storeAccessToken("acme", "token-abc");
    expect(readStoredAccessToken("acme")).toBe("token-abc");
    expect(getPublicAccessTokenKey("acme")).toBe("public-org-access:acme");
  });

  it("fetches org summary", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          id: "org-1",
          name: "Acme",
          description: null,
          slug: "acme",
          passphrase_required: false,
        }),
        { status: 200 },
      ),
    );

    const summary = await publicOrgPageService.getOrgSummary("acme");
    expect(summary.name).toBe("Acme");
    expect(summary.passphrase_required).toBe(false);
  });

  it("sends access token header when listing agents", async () => {
    const fetchMock = vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ agents: [] }), { status: 200 }),
    );

    await publicOrgPageService.listAgents("acme", "secret-token");

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/public/orgs/acme/agents"),
      expect.objectContaining({
        headers: expect.objectContaining({
          "X-Public-Access-Token": "secret-token",
        }),
      }),
    );
  });
});
