import { describe, expect, it } from "vitest";

import robots from "../robots";
import sitemap from "../sitemap";

describe("public SEO routes", () => {
  it("publishes only the canonical marketing origin in the sitemap", () => {
    expect(sitemap()).toEqual([
      {
        url: "https://www.247ai.live",
        changeFrequency: "weekly",
        priority: 1,
      },
    ]);
  });

  it("points crawlers at the canonical sitemap and excludes app routes", () => {
    expect(robots()).toEqual({
      rules: {
        userAgent: "*",
        allow: "/",
        disallow: expect.arrayContaining(["/auth", "/dashboard", "/api"]),
      },
      sitemap: "https://www.247ai.live/sitemap.xml",
    });
  });
});
