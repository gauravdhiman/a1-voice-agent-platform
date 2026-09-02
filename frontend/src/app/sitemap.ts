import type { MetadataRoute } from "next";

import { SITE_URL } from "@/lib/site-config";

/** Return the canonical public URLs that search engines should crawl. */
export default function sitemap(): MetadataRoute.Sitemap {
  return [
    {
      url: SITE_URL,
      changeFrequency: "weekly",
      priority: 1,
    },
  ];
}
