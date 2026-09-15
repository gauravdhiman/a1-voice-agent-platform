import { describe, expect, it } from "vitest";

import robots from "../robots";
import sitemap from "../sitemap";

describe("public SEO routes", () => {
  it("publishes the canonical marketing origin plus funnel and vertical pages", () => {
    expect(sitemap()).toEqual([
      {
        url: "https://www.247ai.live",
        changeFrequency: "weekly",
        priority: 1,
      },
      {
        url: "https://www.247ai.live/request-demo",
        changeFrequency: "monthly",
        priority: 0.9,
      },
      {
        url: "https://www.247ai.live/dental",
        changeFrequency: "monthly",
        priority: 0.8,
      },
      {
        url: "https://www.247ai.live/hvac",
        changeFrequency: "monthly",
        priority: 0.8,
      },
      {
        url: "https://www.247ai.live/restaurants",
        changeFrequency: "monthly",
        priority: 0.8,
      },
      {
        url: "https://www.247ai.live/salons",
        changeFrequency: "monthly",
        priority: 0.8,
      },
      {
        url: "https://www.247ai.live/real-estate",
        changeFrequency: "monthly",
        priority: 0.8,
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
