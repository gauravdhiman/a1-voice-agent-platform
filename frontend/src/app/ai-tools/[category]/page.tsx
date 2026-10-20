import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Check, X } from "lucide-react";
import { createMarketingMetadata } from "@/lib/marketing-seo";
import { SITE_URL } from "@/lib/site-config";
import { getCategories, getCategory, getToolsByCategory } from "@/lib/ai-tools";
import { PublicThemeRoot } from "@/components/public-theme/public-theme-root";
import { PublicHeader } from "@/components/public-theme/public-header";
import { SiteFooter } from "@/components/public-theme/site-footer";
import { ToolCard } from "@/components/ai-tools/tool-card";
import { BlogTable } from "@/components/blog/blog-table";
import { BlogFaq } from "@/components/blog/blog-faq";
import { BlogCTA } from "@/components/blog/blog-cta";

export async function generateStaticParams() {
  return getCategories().map((category) => ({ category: category.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ category: string }>;
}): Promise<Metadata> {
  const { category } = await params;
  const data = getCategory(category);
  if (!data) {
    return { title: "Category not found - 24x7 AI" };
  }
  return createMarketingMetadata({
    path: `/ai-tools/${data.slug}`,
    title: `${data.name} for Small Business: Compared`,
    description: data.description,
    keywords: [
      data.name.toLowerCase(),
      `best ${data.name.toLowerCase()} 2026`,
      "AI tools for small business",
      "small business software comparison",
    ],
  });
}

export default async function AiToolsCategoryPage({
  params,
}: {
  params: Promise<{ category: string }>;
}) {
  const { category } = await params;
  const data = getCategory(category);
  if (!data) {
    notFound();
  }
  const tools = getToolsByCategory(data.slug);

  const itemListJsonLd = {
    "@context": "https://schema.org",
    "@type": "ItemList",
    name: `${data.name} for small business`,
    description: data.description,
    itemListElement: tools.map((tool, index) => ({
      "@type": "ListItem",
      position: index + 1,
      name: tool.name,
      url: `${SITE_URL}/ai-tools/${data.slug}/${tool.slug}`,
    })),
  };

  return (
    <PublicThemeRoot>
      <PublicHeader />
      <main className="mx-auto w-full max-w-5xl px-4 py-16 md:py-24">
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(itemListJsonLd) }}
        />
        <Link
          href="/ai-tools"
          className="text-sm font-medium text-primary hover:underline"
        >
          Back to the AI toolbox
        </Link>
        <p className="mt-6 text-sm font-medium uppercase tracking-widest text-muted-foreground">
          The Small Business AI Toolbox · Curated by 24x7 AI
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-foreground md:text-4xl">
          {data.name} for small business
        </h1>
        <p className="mt-4 max-w-2xl text-lg text-muted-foreground">
          {data.tagline}
        </p>

        <div className="mt-8 max-w-3xl space-y-4 text-muted-foreground">
          {data.intro.map((paragraph, i) => (
            <p key={i}>{paragraph}</p>
          ))}
        </div>

        {data.decisionShortcuts && data.decisionShortcuts.length > 0 ? (
          <section aria-label="Our recommendations" className="mt-12">
            <h2 className="text-2xl font-semibold tracking-tight text-foreground">
              If you just want an answer
            </h2>
            <div className="mt-6 grid gap-4 sm:grid-cols-3">
              {data.decisionShortcuts.map((shortcut) => (
                <div
                  key={shortcut.label}
                  className="rounded-xl border border-border bg-card p-5"
                >
                  <p className="text-xs font-semibold uppercase tracking-widest text-primary">
                    {shortcut.label}
                  </p>
                  <p className="mt-2 text-lg font-semibold text-foreground">
                    {shortcut.tool}
                  </p>
                  <p className="mt-2 text-sm text-muted-foreground">
                    {shortcut.reason}
                  </p>
                </div>
              ))}
            </div>
          </section>
        ) : null}

        <section aria-label="Quick comparison" className="mt-12">
          <h2 className="text-2xl font-semibold tracking-tight text-foreground">
            Quick comparison
          </h2>
          <BlogTable
            headers={[
              "Tool",
              "What it does",
              "Free tier",
              "Starting price",
              "Best for",
            ]}
            rows={tools.map((tool) => [
              tool.name,
              tool.tagline,
              tool.quickFacts ? tool.quickFacts.freeTier : "See the full review",
              tool.pricing,
              tool.bestFor,
            ])}
            caption={`${data.name} compared for small business budgets. Pricing researched October 2026.`}
          />
        </section>

        <section aria-label="Tool reviews" className="mt-12">
          <h2 className="text-2xl font-semibold tracking-tight text-foreground">
            The shortlist
          </h2>
          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            {tools.map((tool) => (
              <ToolCard key={tool.slug} tool={tool} />
            ))}
          </div>
        </section>

        {data.howToChoose && data.howToChoose.length > 0 ? (
          <section aria-label="How to choose" className="mt-12">
            <h2 className="text-2xl font-semibold tracking-tight text-foreground">
              How to choose
            </h2>
            <p className="mt-2 max-w-3xl text-muted-foreground">
              Before you buy, ask yourself these questions. Your answers point
              straight at the right tool.
            </p>
            <ol className="mt-6 max-w-3xl list-decimal space-y-3 pl-6 text-muted-foreground marker:font-semibold marker:text-foreground">
              {data.howToChoose.map((question, i) => (
                <li key={i} className="pl-1">
                  {question}
                </li>
              ))}
            </ol>
          </section>
        ) : null}

        {data.expectations &&
        (data.expectations.will.length > 0 ||
          data.expectations.wont.length > 0) ? (
          <section aria-label="Honest expectations" className="mt-12">
            <h2 className="text-2xl font-semibold tracking-tight text-foreground">
              Set honest expectations
            </h2>
            <div className="mt-6 grid gap-4 md:grid-cols-2">
              <div className="rounded-xl border border-border bg-card p-5">
                <h3 className="text-lg font-semibold text-foreground">
                  What {data.name.toLowerCase().replace(/\bai\b/g, "AI")} will do
                </h3>
                <ul className="mt-4 space-y-3">
                  {data.expectations.will.map((item, i) => (
                    <li key={i} className="flex gap-2 text-sm text-muted-foreground">
                      <Check
                        className="mt-0.5 h-4 w-4 shrink-0 text-primary"
                        aria-hidden="true"
                      />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="rounded-xl border border-border bg-card p-5">
                <h3 className="text-lg font-semibold text-foreground">
                  What it will not do
                </h3>
                <ul className="mt-4 space-y-3">
                  {data.expectations.wont.map((item, i) => (
                    <li key={i} className="flex gap-2 text-sm text-muted-foreground">
                      <X
                        className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground"
                        aria-hidden="true"
                      />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </section>
        ) : null}

        <section aria-label="Frequently asked questions" className="mt-12">
          <h2 className="text-2xl font-semibold tracking-tight text-foreground">
            Frequently asked questions
          </h2>
          <BlogFaq items={data.faqs} />
        </section>

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
