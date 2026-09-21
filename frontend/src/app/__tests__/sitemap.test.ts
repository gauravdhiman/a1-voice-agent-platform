import { describe, expect, it } from "vitest";
import sitemap from "@/app/sitemap";
import { SITE_URL } from "@/lib/site-config";

describe("sitemap", () => {
  it("lists the launch funnel and vertical pages", () => {
    const urls = sitemap().map((entry) => entry.url);
    expect(urls).toEqual([
      `${SITE_URL}`,
      `${SITE_URL}/request-demo`,
      `${SITE_URL}/dental-appointment-booking`,
      `${SITE_URL}/hvac-service-call-answering`,
      `${SITE_URL}/restaurant-order-taking`,
      `${SITE_URL}/plumbing-service-requests`,
      `${SITE_URL}/auto-repair-service-booking`,
      `${SITE_URL}/veterinary-appointment-booking`,
      `${SITE_URL}/salon-appointment-booking`,
      `${SITE_URL}/real-estate-lead-capture`,
    ]);
  });
});
