import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { createMarketingMetadata } from "@/lib/marketing-seo";
import { getCategories, getAllTools } from "@/lib/ai-tools";
import { PublicThemeRoot } from "@/components/public-theme/public-theme-root";
import { PublicHeader } from "@/components/public-theme/public-header";
import { SiteFooter } from "@/components/public-theme/site-footer";
import { ToolCard } from "@/components/ai-tools/tool-card";
import { BlogCTA } from "@/components/blog/blog-cta";

export const metadata: Metadata = createMarketingMetadata({
  path: "/ai-tools",
  title: "AI Tools for Small Business: The 24x7 AI Toolbox",
  description:
    "Curated, honestly reviewed AI tools for small businesses: AI receptionists, chatbots, scheduling, review management, and marketing. No vendor paid for placement.",
  keywords: [
    "AI tools for small business",
    "best AI tools 2026",
    "AI receptionist comparison",
    "small business AI software",
    "AI tools directory",
  ],
});

export default function AiToolsIndexPage() {
  const categories = getCategories();
  const featured = getAllTools().filter((tool) => tool.featured);

  return (
    <PublicThemeRoot>
      <PublicHeader />
      <main className="mx-auto w-full max-w-5xl px-4 py-16 md:py-24">
        <p className="text-sm font-medium uppercase tracking-widest text-muted-foreground">
          The Small Business AI Toolbox · Curated by 24x7 AI
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-foreground md:text-4xl">
          AI tools for small business, honestly reviewed
        </h1>
        <p className="mt-4 max-w-2xl text-lg text-muted-foreground">
          We test the AI tools small businesses actually ask us about — what
          they cost, where they shine, and where they fall short. No vendor
          paid for placement, and every review links to the official pricing
          page so you can verify.
        </p>

        <section aria-label="Tool categories" className="mt-12">
          <h2 className="text-2xl font-semibold tracking-tight text-foreground">
            Browse by category
          </h2>
          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {categories.map((category) => (
              <Link
                key={category.slug}
                href={`/ai-tools/${category.slug}`}
                className="group rounded-xl border border-border bg-card p-6 shadow-sm transition hover:border-primary/50"
              >
                <h3 className="text-lg font-semibold text-foreground group-hover:underline">
                  {category.name}
                </h3>
                <p className="mt-1 text-sm text-muted-foreground">
                  {category.tagline}
                </p>
                <span className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-primary">
                  Compare tools{" "}
                  <ArrowRight
                    className="h-4 w-4 transition-transform group-hover:translate-x-0.5"
                    aria-hidden="true"
                  />
                </span>
              </Link>
            ))}
          </div>
        </section>

        {featured.length > 0 ? (
          <section aria-label="Featured tools" className="mt-16">
            <h2 className="text-2xl font-semibold tracking-tight text-foreground">
              Featured
            </h2>
            <div className="mt-6 grid gap-4 sm:grid-cols-2">
              {featured.map((tool) => (
                <ToolCard key={tool.slug} tool={tool} />
              ))}
            </div>
          </section>
        ) : null}

        <div className="mt-16">
          <BlogCTA
            title="Your phones could be next"
            description="24x7 AI answers every call on your business line, books appointments, and captures leads around the clock. Concierge setup, live in 48 hours, plans from $79/month."
            buttonText="See 24x7 AI in action"
            href="/request-demo"
          />
        </div>
      </main>
      <SiteFooter />
    </PublicThemeRoot>
  );
}
