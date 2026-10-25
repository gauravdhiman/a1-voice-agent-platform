import type { Metadata } from "next";
import { createMarketingMetadata } from "@/lib/marketing-seo";
import { PublicThemeRoot } from "@/components/public-theme/public-theme-root";
import { PublicHeader } from "@/components/public-theme/public-header";
import { SiteFooter } from "@/components/public-theme/site-footer";
import { BlogFaq } from "@/components/blog/blog-faq";
import { BlogCTA } from "@/components/blog/blog-cta";
import { SavingsCalculator } from "./calculator";
import { NewsletterForm } from "./newsletter-form";

export const metadata: Metadata = createMarketingMetadata({
  path: "/ai-tools/savings-calculator",
  title: "AI Savings Calculator: What Missed Calls and Busywork Cost You",
  description:
    "A free, honest calculator for small businesses: see what missed calls, scheduling back-and-forth, and repeat questions cost you each month, and which AI tools to fix first.",
  keywords: [
    "AI savings calculator",
    "cost of missed calls calculator",
    "small business AI ROI",
    "AI tools for small business",
    "receptionist cost calculator",
  ],
});

const faqItems = [
  {
    q: "How does this calculator work?",
    a: "You enter rough numbers about your week: missed calls, hours on scheduling, repeat questions, and chasing reviews. We turn them into a monthly dollar figure using your close rate and an hourly cost for your time. Every line of the math is shown on the page so you can check it.",
  },
  {
    q: "Where do the close rate and hourly cost come from?",
    a: "They are conservative averages. Solo owners tend to close a higher share of callers (we use 25%) than larger teams (10% at 50+), and we value time at $30 an hour for small teams and $40 for larger ones. Adjust your business size and the math follows.",
  },
  {
    q: "Is this a quote for what I will save?",
    a: "No. It is an estimate to help you size the problem. Real results depend on your callers, your market, and how you use the tools. The point is to see which leak is biggest so you fix that first.",
  },
  {
    q: "Which tool should I try first?",
    a: "Start with whatever line is biggest in your results. The starter stack on this page ranks three tools by your own numbers, with an honest review linked for each. Fix the biggest leak first, then move down the list.",
  },
];

export default function SavingsCalculatorPage() {
  return (
    <PublicThemeRoot>
      <PublicHeader />
      <main className="mx-auto w-full max-w-5xl px-4 py-16 md:py-24">
        <p className="text-sm font-medium uppercase tracking-widest text-muted-foreground">
          The Small Business AI Toolbox · Curated by 24x7 AI
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-foreground md:text-4xl">
          How much is busywork costing you?
        </h1>
        <p className="mt-4 max-w-2xl text-lg text-muted-foreground">
          Missed calls, scheduling back-and-forth, and answering the same
          questions all week add up. Put in rough numbers and see the monthly
          cost, then get a starter stack of AI tools aimed at your biggest
          leak.
        </p>

        <div className="mt-12">
          <SavingsCalculator />
        </div>

        <section
          aria-label="Newsletter signup"
          className="mt-16 rounded-xl border border-border bg-card p-6 shadow-sm"
        >
          <h2 className="text-2xl font-semibold tracking-tight text-foreground">
            Get one AI tip in your inbox every week
          </h2>
          <p className="mt-2 max-w-2xl text-muted-foreground">
            Join AI for Business Owners: one plain-English tool pick and one
            practical tip each week, no hype.
          </p>
          <div className="mt-4">
            <NewsletterForm />
          </div>
        </section>

        <section aria-label="Common questions" className="mt-16">
          <h2 className="text-2xl font-semibold tracking-tight text-foreground">
            Common questions
          </h2>
          <BlogFaq items={faqItems} />
        </section>

        <div className="mt-16">
          <BlogCTA
            title="Stop the biggest leak first"
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
