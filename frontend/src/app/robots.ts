import type { MetadataRoute } from "next";

import { SITE_URL } from "@/lib/site-config";

const NON_PUBLIC_PATHS = [
  "/api",
  "/auth",
  "/dashboard",
  "/onboarding",
  "/organization",
  "/organizations",
  "/platform",
  "/settings",
  "/users",
  "/billing",
  "/calls",
  "/agents",
  "/phone-numbers",
  "/skills",
];

/** Keep authenticated application routes out of search-engine crawling. */
export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: NON_PUBLIC_PATHS,
    },
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
