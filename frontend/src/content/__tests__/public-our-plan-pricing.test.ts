import { existsSync, readFileSync, readdirSync } from "fs";
import path from "path";
import { describe, expect, it } from "vitest";
import { TOOLS } from "@/content/ai-tools/tools";
import {
  formatMonthlyPriceCompact,
  formatPriceUSD,
  getPlansStartAtCopy,
  getStandardPricingCopy,
  PLANS,
} from "@/lib/pricing/plans";

const FRONTEND_ROOT = path.resolve(__dirname, "../../..");
const BLOG_DIR = path.join(FRONTEND_ROOT, "src/content/blog");

/** Leftover our-plan claims that must not reappear after the $79 catalog lock. */
const OUR_PLAN_49_CLAIMS = [
  "Plans start at $49",
  "Our plans start at $49",
  "From $49/mo (250 call minutes)",
  "monthly plans from $49/month",
  "$49-a-month receptionist",
];

function readPublicFile(relativePath: string): string {
  return readFileSync(path.join(FRONTEND_ROOT, relativePath), "utf8");
}

describe("public our-plan pricing leftovers", () => {
  it("locks blog and public catalog copy to the Starter catalog amount", () => {
    expect(getPlansStartAtCopy()).toBe(
      `Plans start at ${formatPriceUSD(PLANS.STARTER.monthlyUSD)} a month`,
    );
    expect(getStandardPricingCopy()).toContain(
      formatPriceUSD(PLANS.STARTER.monthlyUSD),
    );

    const blogFiles = readdirSync(BLOG_DIR)
      .filter((file) => file.endsWith(".mdx"))
      .map((file) => path.join("src/content/blog", file));

    const publicFiles = [
      ...blogFiles,
      "public/llms.txt",
      "public/ai-tools-catalog.json",
      "public/ai-tools-catalog.md",
      "src/content/ai-tools/tools.ts",
    ];

    for (const relativePath of publicFiles) {
      const text = readPublicFile(relativePath);
      for (const claim of OUR_PLAN_49_CLAIMS) {
        expect(text, `${relativePath} still claims ${claim}`).not.toContain(
          claim,
        );
      }
    }
  });

  it("keeps the 24x7 AI catalog snapshot on the shared Starter price", () => {
    const ours = TOOLS.find((tool) => tool.slug === "24x7-ai");
    expect(ours?.pricing).toBe(
      `From ${formatMonthlyPriceCompact(PLANS.STARTER.monthlyUSD)} (${PLANS.STARTER.approximateMinutes} call minutes); free plan available`,
    );

    const catalog = JSON.parse(readPublicFile("public/ai-tools-catalog.json")) as {
      tools: Array<{ slug: string; pricing: string }>;
    };
    const catalogOurs = catalog.tools.find((tool) => tool.slug === "24x7-ai");
    expect(catalogOurs?.pricing).toBe(ours?.pricing);
    expect(readPublicFile("public/ai-tools-catalog.md")).toContain(
      `- Pricing: ${ours?.pricing}`,
    );
    expect(readPublicFile("public/llms.txt")).toContain(
      `monthly plans from ${formatPriceUSD(PLANS.STARTER.monthlyUSD)}/month`,
    );
  });

  it("leaves researched competitor $49 prices alone", () => {
    const toolsSource = readPublicFile("src/content/ai-tools/tools.ts");
    expect(toolsSource).toContain("Rosie $49");
    expect(toolsSource).toContain('pricing: "From $49/mo (250 minutes included)"');

    const catalog = readPublicFile("public/ai-tools-catalog.json");
    expect(catalog).toContain("Rosie");
    expect(catalog).toContain("From $49/mo (250 minutes included)");

    const costBlog = path.join(BLOG_DIR, "how-much-does-an-ai-receptionist-cost.mdx");
    expect(existsSync(costBlog)).toBe(true);
    const costBlogText = readFileSync(costBlog, "utf8");
    expect(costBlogText).toContain("$49 to $349");
    expect(costBlogText).toContain("cheap $49 plan");
  });
});
