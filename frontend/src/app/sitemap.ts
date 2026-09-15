import type { MetadataRoute } from "next";

import { SITE_URL } from "@/lib/site-config";

/** Return the canonical public URLs that search engines should crawl. */
export default function sitemap(): MetadataRoute.Sitemap {
  const pages: Array<{
    path: string;
    changeFrequency: MetadataRoute.Sitemap[number]["changeFrequency"];
    priority: number;
  }> = [
    { path: "", changeFrequency: "weekly", priority: 1 },
    { path: "/request-demo", changeFrequency: "monthly", priority: 0.9 },
    { path: "/dental", changeFrequency: "monthly", priority: 0.8 },
    { path: "/hvac", changeFrequency: "monthly", priority: 0.8 },
    { path: "/restaurants", changeFrequency: "monthly", priority: 0.8 },
    { path: "/salons", changeFrequency: "monthly", priority: 0.8 },
    { path: "/real-estate", changeFrequency: "monthly", priority: 0.8 },
  ];
  return pages.map((page) => ({
    url: `${SITE_URL}${page.path}`,
    changeFrequency: page.changeFrequency,
    priority: page.priority,
  }));
}
