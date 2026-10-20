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
import { BlogTable } from "@/components/blog/blog-table";

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
    reviewBody: data.verdictBox ?? data.verdict,
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
          <div className="mt-4 rounded-xl border border-border bg-muted/50 p-5">
            <p className="text-foreground">{data.verdictBox ?? data.verdict}</p>
          </div>
          <p className="mt-3 text-sm text-muted-foreground">
            <span className="font-medium text-foreground">Best for: </span>
            {data.bestFor}
          </p>
        </section>

        {data.quickFacts ? (
          <section aria-label="Quick facts" className="mt-10">
            <h2 className="text-2xl font-semibold tracking-tight text-foreground">
              Quick facts
            </h2>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <div className="rounded-xl border border-border p-5">
                <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                  Price
                </h3>
                <p className="mt-2 text-sm text-foreground">
                  {data.quickFacts.price}
                </p>
              </div>
              <div className="rounded-xl border border-border p-5">
                <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                  Free trial
                </h3>
                <p className="mt-2 text-sm text-foreground">
                  {data.quickFacts.freeTier}
                </p>
              </div>
              <div className="rounded-xl border border-border p-5">
                <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                  Setup
                </h3>
                <p className="mt-2 text-sm text-foreground">
                  {data.quickFacts.setup}
                </p>
              </div>
              <div className="rounded-xl border border-border p-5">
                <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                  Best for
                </h3>
                <p className="mt-2 text-sm text-foreground">{data.bestFor}</p>
              </div>
            </div>
          </section>
        ) : null}

        {data.whatIsIt ? (
          <section aria-label="What it is" className="mt-10">
            <h2 className="text-2xl font-semibold tracking-tight text-foreground">
              What is {data.name}, in plain English
            </h2>
            {data.whatIsIt.map((para, i) => (
              <p key={i} className="mt-3 text-muted-foreground">
                {para}
              </p>
            ))}
          </section>
        ) : null}

        {data.businessScenarios ? (
          <section aria-label="What it will do for your business" className="mt-10">
            <h2 className="text-2xl font-semibold tracking-tight text-foreground">
              What will it actually do for your business
            </h2>
            <div className="mt-4 space-y-4">
              {data.businessScenarios.map((scenario, i) => (
                <div
                  key={i}
                  className="rounded-xl border border-border p-5"
                >
                  <h3 className="font-semibold text-foreground">
                    {scenario.title}
                  </h3>
                  <p className="mt-2 text-sm text-muted-foreground">
                    {scenario.description}
                  </p>
                </div>
              ))}
            </div>
          </section>
        ) : null}

        {data.howItWorks ? (
          <section aria-label="How it works" className="mt-10">
            <h2 className="text-2xl font-semibold tracking-tight text-foreground">
              How it works
            </h2>
            <ol className="mt-4 space-y-4">
              {data.howItWorks.map((step, i) => (
                <li key={i} className="flex items-start gap-4">
                  <span
                    className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-sm font-bold text-primary-foreground"
                    aria-hidden="true"
                  >
                    {i + 1}
                  </span>
                  <p className="pt-1 text-muted-foreground">{step}</p>
                </li>
              ))}
            </ol>
          </section>
        ) : null}

        {data.pricingExplained ? (
          <section aria-label="Pricing explained" className="mt-10">
            <h2 className="text-2xl font-semibold tracking-tight text-foreground">
              Pricing, explained honestly
            </h2>
            {data.pricingExplained.map((para, i) => (
              <p key={i} className="mt-3 text-muted-foreground">
                {para}
              </p>
            ))}
            {data.pricingCatches ? (
              <div className="mt-4 rounded-xl border border-border bg-muted/50 p-5">
                <h3 className="font-semibold text-foreground">
                  Catches worth knowing
                </h3>
                <ul className="mt-3 space-y-2">
                  {data.pricingCatches.map((catchItem, i) => (
                    <li
                      key={i}
                      className="flex items-start gap-2 text-sm text-muted-foreground"
                    >
                      <X
                        className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground"
                        aria-hidden="true"
                      />
                      {catchItem}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </section>
        ) : null}

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

        {data.whoShouldGet || data.whoShouldSkip ? (
          <section aria-label="Who should get it" className="mt-10">
            <h2 className="text-2xl font-semibold tracking-tight text-foreground">
              Should you get it
            </h2>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              {data.whoShouldGet ? (
                <div className="rounded-xl border border-border p-5">
                  <h3 className="font-semibold text-foreground">
                    Get it if you are
                  </h3>
                  <ul className="mt-3 space-y-2">
                    {data.whoShouldGet.map((item, i) => (
                      <li
                        key={i}
                        className="flex items-start gap-2 text-sm text-muted-foreground"
                      >
                        <Check
                          className="mt-0.5 h-4 w-4 shrink-0 text-primary"
                          aria-hidden="true"
                        />
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {data.whoShouldSkip ? (
                <div className="rounded-xl border border-border p-5">
                  <h3 className="font-semibold text-foreground">
                    Skip it if you are
                  </h3>
                  <ul className="mt-3 space-y-2">
                    {data.whoShouldSkip.map((item, i) => (
                      <li
                        key={i}
                        className="flex items-start gap-2 text-sm text-muted-foreground"
                      >
                        <X
                          className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground"
                          aria-hidden="true"
                        />
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </div>
          </section>
        ) : null}

        {data.comparison ? (
          <section aria-label="Comparison" className="mt-10">
            <h2 className="text-2xl font-semibold tracking-tight text-foreground">
              How {data.name} compares
            </h2>
            <div className="mt-4">
              <BlogTable
                headers={["", "Starts at", "The key difference"]}
                rows={data.comparison.map((row) => [
                  row.tool,
                  row.price,
                  row.difference,
                ])}
                caption={`${data.name} vs alternatives, pricing researched October 2026`}
              />
            </div>
          </section>
        ) : null}

        <section aria-label="Frequently asked questions" className="mt-10">
          <h2 className="text-2xl font-semibold tracking-tight text-foreground">
            Frequently asked questions
          </h2>
          <BlogFaq items={data.faqs} />
        </section>

        {data.goingDeeper ? (
          <section aria-label="Going deeper" className="mt-10">
            <h2 className="text-2xl font-semibold tracking-tight text-foreground">
              Going deeper
            </h2>
            <p className="mt-3 text-muted-foreground">
              For the tech-curious: what {data.name} connects to, and what
              happens to your data.
            </p>
            <h3 className="mt-6 text-lg font-semibold text-foreground">
              Integrations
            </h3>
            <ul className="mt-3 space-y-2">
              {data.goingDeeper.integrations.map((item, i) => (
                <li
                  key={i}
                  className="flex items-start gap-2 text-sm text-muted-foreground"
                >
                  <Check
                    className="mt-0.5 h-4 w-4 shrink-0 text-primary"
                    aria-hidden="true"
                  />
                  {item}
                </li>
              ))}
            </ul>
            {data.goingDeeper.api ? (
              <>
                <h3 className="mt-6 text-lg font-semibold text-foreground">
                  Developer API
                </h3>
                <p className="mt-3 text-sm text-muted-foreground">
                  {data.goingDeeper.api}
                </p>
              </>
            ) : null}
            <h3 className="mt-6 text-lg font-semibold text-foreground">
              Data and privacy
            </h3>
            <ul className="mt-3 space-y-2">
              {data.goingDeeper.privacy.map((item, i) => (
                <li
                  key={i}
                  className="flex items-start gap-2 text-sm text-muted-foreground"
                >
                  <Check
                    className="mt-0.5 h-4 w-4 shrink-0 text-primary"
                    aria-hidden="true"
                  />
                  {item}
                </li>
              ))}
            </ul>
            <div className="mt-6 rounded-xl border border-border bg-muted/50 p-5">
              <h3 className="font-semibold text-foreground">
                Advanced workflow: {data.goingDeeper.advancedWorkflowTitle}
              </h3>
              <p className="mt-2 text-sm text-muted-foreground">
                {data.goingDeeper.advancedWorkflow}
              </p>
            </div>
          </section>
        ) : null}

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
