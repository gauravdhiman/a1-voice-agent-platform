import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowUpRight, Check, X } from "lucide-react";
import { createMarketingMetadata } from "@/lib/marketing-seo";
import { SITE_URL } from "@/lib/site-config";
import { getCategory, getAllTools, getTool } from "@/lib/ai-tools";
import { PublicThemeRoot } from "@/components/public-theme/public-theme-root";
import { PublicHeader } from "@/components/public-theme/public-header";
import { SiteFooter } from "@/components/public-theme/site-footer";
import { Badge } from "@/components/ui/badge";
import { BlogFaq } from "@/components/blog/blog-faq";
import { BlogCTA } from "@/components/blog/blog-cta";

export async function generateStaticParams() {
  return getAllTools().map((tool) => ({
    category: tool.category,
    tool: tool.slug,
  }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ category: string; tool: string }>;
}): Promise<Metadata> {
  const { category, tool } = await params;
  const data = getTool(category, tool);
  if (!data) {
    return { title: "Tool not found - 24x7 AI" };
  }
  const categoryData = getCategory(category);
  return createMarketingMetadata({
    path: `/ai-tools/${category}/${data.slug}`,
    title: `${data.name} Review: Pricing, Pros and Cons for Small Business`,
    description: `${data.tagline} ${data.pricing}. Honest ${data.name} review for small businesses, curated by 24x7 AI.`,
    keywords: [
      `${data.name} review`,
      `${data.name} pricing`,
      `${data.name} for small business`,
      categoryData ? categoryData.name.toLowerCase() : "AI tools",
      "AI tools for small business",
    ],
  });
}

export default async function AiToolReviewPage({
  params,
}: {
  params: Promise<{ category: string; tool: string }>;
}) {
  const { category, tool } = await params;
  const data = getTool(category, tool);
  if (!data) {
    notFound();
  }
  const categoryData = getCategory(category);

  const reviewJsonLd = {
    "@context": "https://schema.org",
    "@type": "Review",
    itemReviewed: {
      "@type": "SoftwareApplication",
      name: data.name,
      url: data.url,
      applicationCategory: "BusinessApplication",
    },
    author: {
      "@type": "Organization",
      name: "24x7 AI",
      url: SITE_URL,
    },
    reviewBody: data.verdict,
  };

  return (
    <PublicThemeRoot>
      <PublicHeader />
      <main className="mx-auto w-full max-w-3xl px-4 py-16 md:py-24">
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(reviewJsonLd) }}
        />
        <Link
          href={`/ai-tools/${category}`}
          className="text-sm font-medium text-primary hover:underline"
        >
          Back to {categoryData ? categoryData.name : "the AI toolbox"}
        </Link>
        <p className="mt-6 text-sm font-medium uppercase tracking-widest text-muted-foreground">
          The Small Business AI Toolbox · Curated by 24x7 AI
        </p>
        <div className="mt-2 flex flex-wrap items-center gap-3">
          <h1 className="text-3xl font-bold tracking-tight text-foreground md:text-4xl">
            {data.name}
          </h1>
          {data.featured ? <Badge>Our pick</Badge> : null}
        </div>
        <p className="mt-4 text-lg text-muted-foreground">{data.tagline}</p>
        <div className="mt-6 flex flex-wrap items-center gap-4">
          <p className="text-base font-semibold text-foreground">
            {data.pricing}
          </p>
          <a
            href={data.url}
            target="_blank"
            rel="noopener"
            className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline"
          >
            Visit {data.name}{" "}
            <ArrowUpRight className="h-4 w-4" aria-hidden="true" />
          </a>
        </div>

        <section aria-label="Verdict" className="mt-10">
          <h2 className="text-2xl font-semibold tracking-tight text-foreground">
            Our take
          </h2>
          <p className="mt-3 text-muted-foreground">{data.verdict}</p>
          <p className="mt-3 text-sm text-muted-foreground">
            <span className="font-medium text-foreground">Best for: </span>
            {data.bestFor}
          </p>
        </section>

        <section aria-label="Pros and cons" className="mt-10">
          <h2 className="text-2xl font-semibold tracking-tight text-foreground">
            Pros and cons
          </h2>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <div className="rounded-xl border border-border p-5">
              <h3 className="font-semibold text-foreground">What we like</h3>
              <ul className="mt-3 space-y-2">
                {data.pros.map((pro, i) => (
                  <li
                    key={i}
                    className="flex items-start gap-2 text-sm text-muted-foreground"
                  >
                    <Check
                      className="mt-0.5 h-4 w-4 shrink-0 text-primary"
                      aria-hidden="true"
                    />
                    {pro}
                  </li>
                ))}
              </ul>
            </div>
            <div className="rounded-xl border border-border p-5">
              <h3 className="font-semibold text-foreground">Where it falls short</h3>
              <ul className="mt-3 space-y-2">
                {data.cons.map((con, i) => (
                  <li
                    key={i}
                    className="flex items-start gap-2 text-sm text-muted-foreground"
                  >
                    <X
                      className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground"
                      aria-hidden="true"
                    />
                    {con}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>

        <section aria-label="Frequently asked questions" className="mt-10">
          <h2 className="text-2xl font-semibold tracking-tight text-foreground">
            Frequently asked questions
          </h2>
          <BlogFaq items={data.faqs} />
        </section>

        <p className="mt-8 text-xs text-muted-foreground">
          Pricing researched October 2026 and summarized here — vendors change
          pricing often, so confirm on the official site before you buy. No
          vendor paid for this placement.
        </p>

        <div className="mt-8">
          <BlogCTA
            title="Your phones could be next"
            description="24x7 AI answers every call on your business line, books appointments, and captures leads around the clock. Concierge setup, live in 48 hours, plans from $49/month."
            buttonText="See 24x7 AI in action"
            href="/request-demo"
          />
        </div>
      </main>
      <SiteFooter />
    </PublicThemeRoot>
  );
}
