import { describe, expect, it } from "vitest";

import robots from "../robots";
import sitemap from "../sitemap";
import { metadata as dentalMetadata } from "../dental-appointment-booking/page";
import { metadata as hvacMetadata } from "../hvac-service-call-answering/page";
import { metadata as restaurantMetadata } from "../restaurant-order-taking/page";
import { metadata as plumbingMetadata } from "../plumbing-service-requests/page";
import { metadata as autoRepairMetadata } from "../auto-repair-service-booking/page";
import { metadata as veterinaryMetadata } from "../veterinary-appointment-booking/page";
import { metadata as salonMetadata } from "../salon-appointment-booking/page";
import { metadata as realEstateMetadata } from "../real-estate-lead-capture/page";
import {
  SITE_SHARE_IMAGE,
  SITE_SHARE_IMAGE_ALT,
  SITE_URL,
} from "@/lib/site-config";

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
        url: "https://www.247ai.live/how-it-works",
        changeFrequency: "monthly",
        priority: 0.9,
      },
      {
        url: "https://www.247ai.live/dental-appointment-booking",
        changeFrequency: "monthly",
        priority: 0.8,
      },
      {
        url: "https://www.247ai.live/hvac-service-call-answering",
        changeFrequency: "monthly",
        priority: 0.8,
      },
      {
        url: "https://www.247ai.live/restaurant-order-taking",
        changeFrequency: "monthly",
        priority: 0.8,
      },
      {
        url: "https://www.247ai.live/plumbing-service-requests",
        changeFrequency: "monthly",
        priority: 0.8,
      },
      {
        url: "https://www.247ai.live/auto-repair-service-booking",
        changeFrequency: "monthly",
        priority: 0.8,
      },
      {
        url: "https://www.247ai.live/veterinary-appointment-booking",
        changeFrequency: "monthly",
        priority: 0.8,
      },
      {
        url: "https://www.247ai.live/salon-appointment-booking",
        changeFrequency: "monthly",
        priority: 0.8,
      },
      {
        url: "https://www.247ai.live/real-estate-lead-capture",
        changeFrequency: "monthly",
        priority: 0.8,
      },
      {
        url: "https://www.247ai.live/terms",
        changeFrequency: "monthly",
        priority: 0.5,
      },
      {
        url: "https://www.247ai.live/privacy",
        changeFrequency: "monthly",
        priority: 0.5,
      },
      { url: `${SITE_URL}/blog`, changeFrequency: "weekly", priority: 0.7 },
      { url: `${SITE_URL}/blog/how-much-does-one-missed-call-cost`, changeFrequency: "monthly", priority: 0.6 },
      { url: `${SITE_URL}/blog/ai-receptionist-vs-answering-service`, changeFrequency: "monthly", priority: 0.6 },
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

  it("gives every industry page a descriptive canonical URL and keyword metadata", () => {
    const pages = [
      [dentalMetadata, "/dental-appointment-booking"],
      [hvacMetadata, "/hvac-service-call-answering"],
      [restaurantMetadata, "/restaurant-order-taking"],
      [plumbingMetadata, "/plumbing-service-requests"],
      [autoRepairMetadata, "/auto-repair-service-booking"],
      [veterinaryMetadata, "/veterinary-appointment-booking"],
      [salonMetadata, "/salon-appointment-booking"],
      [realEstateMetadata, "/real-estate-lead-capture"],
    ] as const;

    for (const [metadata, path] of pages) {
      expect(metadata.alternates?.canonical).toBe(`${SITE_URL}${path}`);
      expect(metadata.description).toBeTruthy();
      expect(metadata.keywords).toBeTruthy();
      expect(metadata.openGraph?.images).toEqual([
        {
          url: SITE_SHARE_IMAGE,
          width: 1200,
          height: 630,
          alt: SITE_SHARE_IMAGE_ALT,
        },
      ]);
      expect(metadata.twitter).toMatchObject({
        card: "summary_large_image",
        images: [SITE_SHARE_IMAGE],
      });
    }
  });
});
