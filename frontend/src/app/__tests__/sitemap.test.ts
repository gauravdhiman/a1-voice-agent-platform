import { describe, expect, it } from "vitest";
import sitemap from "@/app/sitemap";
import { SITE_URL } from "@/lib/site-config";

describe("sitemap", () => {
  it("lists the launch funnel and vertical pages", () => {
    const urls = sitemap().map((entry) => entry.url);
    expect(urls).toEqual([
      `${SITE_URL}`,
      `${SITE_URL}/request-demo`,
      `${SITE_URL}/dental`,
      `${SITE_URL}/hvac`,
      `${SITE_URL}/restaurants`,
      `${SITE_URL}/salons`,
      `${SITE_URL}/real-estate`,
    ]);
  });
});
