import { NextRequest } from "next/server";
import { describe, expect, it } from "vitest";

import { middleware, shouldRedirectToCanonicalHost } from "./middleware";

describe("canonical host middleware", () => {
  it.each(["247ai.live", "247ai.live:443", "247ai.live.", "APP.RUN.APP"])(
    "redirects non-canonical host %s",
    (host) => {
      expect(shouldRedirectToCanonicalHost(host)).toBe(true);
    },
  );

  it.each(["www.247ai.live", "api.247ai.live", "localhost:3000", ""])(
    "keeps host %s on its own origin",
    (host) => {
      expect(shouldRedirectToCanonicalHost(host)).toBe(false);
    },
  );

  it("redirects the apex host permanently while preserving path and query", () => {
    const request = new NextRequest(
      "https://247ai.live/auth/signin?next=%2Fdashboard",
      { headers: { host: "247ai.live" } },
    );

    const response = middleware(request);

    expect(response.status).toBe(308);
    expect(response.headers.get("location")).toBe(
      "https://www.247ai.live/auth/signin?next=%2Fdashboard",
    );
  });

  it("redirects Cloud Run's generated host to the same canonical origin", () => {
    const request = new NextRequest(
      "https://frontend-abc-uc.a.run.app/demo/x",
      { headers: { host: "frontend-abc-uc.a.run.app" } },
    );

    const response = middleware(request);

    expect(response.status).toBe(308);
    expect(response.headers.get("location")).toBe(
      "https://www.247ai.live/demo/x",
    );
  });
});
