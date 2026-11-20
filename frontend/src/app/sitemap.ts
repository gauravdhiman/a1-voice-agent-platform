import type { MetadataRoute } from "next";

import { SITE_URL } from "@/lib/site-config";
import { TOOL_CATEGORIES, TOOLS } from "@/content/ai-tools/tools";

type SitemapPage = {
  path: string;
  changeFrequency: MetadataRoute.Sitemap[number]["changeFrequency"];
  priority: number;
};

/** Directory pages generated from the AI tools data. */
const aiToolsPages: SitemapPage[] = [
  { path: "/ai-tools", changeFrequency: "weekly", priority: 0.7 },
  {
    path: "/ai-tools/savings-calculator",
    changeFrequency: "monthly",
    priority: 0.7,
  },
  ...TOOL_CATEGORIES.map(
    (category): SitemapPage => ({
      path: `/ai-tools/${category.slug}`,
      changeFrequency: "weekly",
      priority: 0.6,
    }),
  ),
  ...TOOLS.map(
    (tool): SitemapPage => ({
      path: `/ai-tools/${tool.category}/${tool.slug}`,
      changeFrequency: "monthly",
      priority: 0.5,
    }),
  ),
];

/** Return the canonical public URLs that search engines should crawl. */
export default function sitemap(): MetadataRoute.Sitemap {
  const pages: SitemapPage[] = [
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
    { path: "/blog", changeFrequency: "weekly", priority: 0.7 },
    {
      path: "/blog/how-much-does-one-missed-call-cost",
      changeFrequency: "monthly",
      priority: 0.6,
    },
    {
      path: "/blog/ai-receptionist-vs-answering-service",
      changeFrequency: "monthly",
      priority: 0.6,
    },
    {
      path: "/blog/ai-receptionist-explained",
      changeFrequency: "monthly",
      priority: 0.6,
    },
    {
      path: "/blog/how-much-does-a-missed-call-cost",
      changeFrequency: "monthly",
      priority: 0.6,
    },
    {
      path: "/blog/how-much-does-an-ai-receptionist-cost",
      changeFrequency: "monthly",
      priority: 0.6,
    },
    {
      path: "/blog/why-voice-ai-sounds-robotic",
      changeFrequency: "monthly",
      priority: 0.6,
    },
    {
      path: "/blog/can-ai-receptionist-book-appointments",
      changeFrequency: "monthly",
      priority: 0.6,
    },
    {
      path: "/blog/ai-receptionist-for-dental-offices",
      changeFrequency: "monthly",
      priority: 0.6,
    },
    {
      path: "/blog/ai-receptionist-for-hvac",
      changeFrequency: "monthly",
      priority: 0.6,
    },
    {
      path: "/blog/ai-phone-answering-for-restaurants",
      changeFrequency: "monthly",
      priority: 0.6,
    },
    {
      path: "/blog/do-customers-hang-up-on-ai",
      changeFrequency: "monthly",
      priority: 0.6,
    },
    {
      path: "/blog/ai-receptionist-vs-front-desk-employee",
      changeFrequency: "monthly",
      priority: 0.6,
    },
    {
      path: "/blog/how-long-to-set-up-ai-receptionist",
      changeFrequency: "monthly",
      priority: 0.6,
    },
    ...aiToolsPages,
  ];
  return pages.map((page) => ({
    url: `${SITE_URL}${page.path}`,
    changeFrequency: page.changeFrequency,
    priority: page.priority,
  }));
}

