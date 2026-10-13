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
    { path: "/how-it-works", changeFrequency: "monthly", priority: 0.9 },
    {
      path: "/dental-appointment-booking",
      changeFrequency: "monthly",
      priority: 0.8,
    },
    {
      path: "/hvac-service-call-answering",
      changeFrequency: "monthly",
      priority: 0.8,
    },
    {
      path: "/restaurant-order-taking",
      changeFrequency: "monthly",
      priority: 0.8,
    },
    {
      path: "/plumbing-service-requests",
      changeFrequency: "monthly",
      priority: 0.8,
    },
    {
      path: "/auto-repair-service-booking",
      changeFrequency: "monthly",
      priority: 0.8,
    },
    {
      path: "/veterinary-appointment-booking",
      changeFrequency: "monthly",
      priority: 0.8,
    },
    {
      path: "/salon-appointment-booking",
      changeFrequency: "monthly",
      priority: 0.8,
    },
    {
      path: "/real-estate-lead-capture",
      changeFrequency: "monthly",
      priority: 0.8,
    },
    { path: "/terms", changeFrequency: "monthly", priority: 0.5 },
    { path: "/privacy", changeFrequency: "monthly", priority: 0.5 },
  ];
  return pages.map((page) => ({
    url: `${SITE_URL}${page.path}`,
    changeFrequency: page.changeFrequency,
    priority: page.priority,
  }));
}
