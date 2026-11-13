import { describe, expect, it } from "vitest";
import sitemap from "@/app/sitemap";
import { SITE_URL } from "@/lib/site-config";
import { TOOL_CATEGORIES, TOOLS } from "@/content/ai-tools/tools";

describe("sitemap", () => {
  it("lists the launch funnel, vertical, blog, and ai-tools pages", () => {
    const urls = sitemap().map((entry) => entry.url);
    expect(urls).toEqual([
      `${SITE_URL}`,
      `${SITE_URL}/request-demo`,
      `${SITE_URL}/how-it-works`,
      `${SITE_URL}/dental-appointment-booking`,
      `${SITE_URL}/hvac-service-call-answering`,
      `${SITE_URL}/restaurant-order-taking`,
      `${SITE_URL}/plumbing-service-requests`,
      `${SITE_URL}/auto-repair-service-booking`,
      `${SITE_URL}/veterinary-appointment-booking`,
      `${SITE_URL}/salon-appointment-booking`,
      `${SITE_URL}/real-estate-lead-capture`,
      `${SITE_URL}/terms`,
      `${SITE_URL}/privacy`,
      `${SITE_URL}/blog`,
      `${SITE_URL}/blog/how-much-does-one-missed-call-cost`,
      `${SITE_URL}/blog/ai-receptionist-vs-answering-service`,
      `${SITE_URL}/blog/ai-receptionist-explained`,
      `${SITE_URL}/blog/how-much-does-a-missed-call-cost`,
      `${SITE_URL}/blog/how-much-does-an-ai-receptionist-cost`,
      `${SITE_URL}/blog/why-voice-ai-sounds-robotic`,
      `${SITE_URL}/blog/can-ai-receptionist-book-appointments`,
      `${SITE_URL}/blog/ai-receptionist-for-dental-offices`,
      `${SITE_URL}/blog/ai-receptionist-for-hvac`,
      `${SITE_URL}/blog/ai-phone-answering-for-restaurants`,
      `${SITE_URL}/blog/do-customers-hang-up-on-ai`,
      `${SITE_URL}/ai-tools`,
      `${SITE_URL}/ai-tools/savings-calculator`,
      ...TOOL_CATEGORIES.map(
        (category) => `${SITE_URL}/ai-tools/${category.slug}`,
      ),
      ...TOOLS.map(
        (tool) => `${SITE_URL}/ai-tools/${tool.category}/${tool.slug}`,
      ),
    ]);
  });

  it("includes every tool category and tool exactly once", () => {
    const urls = sitemap().map((entry) => entry.url);
    for (const category of TOOL_CATEGORIES) {
      const matches = urls.filter(
        (url) => url === `${SITE_URL}/ai-tools/${category.slug}`,
      );
      expect(matches).toHaveLength(1);
    }
    for (const tool of TOOLS) {
      const matches = urls.filter(
        (url) => url === `${SITE_URL}/ai-tools/${tool.category}/${tool.slug}`,
      );
      expect(matches).toHaveLength(1);
    }
  });
});

