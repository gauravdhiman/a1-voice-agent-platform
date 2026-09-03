import Link from "next/link";
import { ArrowRight, CheckCircle2, Phone } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { SITE_NAME } from "@/lib/site-config";

/** One outcome block: what the AI handles for this vertical. */
export interface IndustryOutcome {
  /** Short outcome headline. */
  title: string;
  /** One-line business explanation. */
  description: string;
}

/** One FAQ entry, also emitted as JSON-LD. */
export interface IndustryFaq {
  question: string;
  answer: string;
}

/** All copy for a vertical landing page. */
export interface IndustryPageContent {
  /** URL slug (dental, hvac, restaurants). */
  slug: string;
  /** H1 headline. */
  headline: string;
  /** Hero sub-copy. */
  subhead: string;
  /** Missed-call pains this vertical feels. */
  pains: string[];
  /** What the AI handles, as outcome blocks. */
  outcomes: IndustryOutcome[];
  /** Demo agent slug to try live. */
  demoSlug: string;
  /** Demo agent display name. */
  demoName: string;
  /** One-line demo pitch. */
  demoBlurb: string;
  /** FAQs (rendered + JSON-LD). */
  faqs: IndustryFaq[];
}

interface IndustryPageProps {
  content: IndustryPageContent;
}

/**
 * Shared template for vertical SEO landing pages.
 *
 * Same skeleton every time (pain → live demo → concierge setup →
 * outcomes → pricing anchor → FAQ), unique copy per vertical so each
 * page earns its own search intent.
 */
export function IndustryPage({ content }: IndustryPageProps) {
  const faqJsonLd = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: content.faqs.map((faq) => ({
      "@type": "Question",
      name: faq.question,
      acceptedAnswer: { "@type": "Answer", text: faq.answer },
    })),
  };

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col font-sans">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqJsonLd) }}
      />
      <header className="w-full border-b border-border/40">
        <div className="container flex h-16 items-center justify-between max-w-5xl mx-auto px-4">
          <Link href="/" className="flex items-center gap-3">
            <div className="bg-gradient-to-br from-blue-600 to-cyan-600 w-10 h-10 rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/20">
              <Phone className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-bold tracking-tight">
              {SITE_NAME}
            </span>
          </Link>
          <Link href="/request-demo">
            <Button size="sm" className="bg-blue-600 hover:bg-blue-700">
              Request a Demo
            </Button>
          </Link>
        </div>
      </header>

      <main className="flex-1">
        <section className="py-16 md:py-24">
          <div className="container max-w-3xl mx-auto px-4 text-center">
            <h1 className="text-4xl font-bold tracking-tighter sm:text-5xl">
              {content.headline}
            </h1>
            <p className="mt-4 text-muted-foreground md:text-xl leading-relaxed">
              {content.subhead}
            </p>
            <div className="mt-8 flex flex-col sm:flex-row gap-3 justify-center">
              <Link href={`/demo/${content.demoSlug}`}>
                <Button
                  size="lg"
                  className="bg-blue-600 hover:bg-blue-700 px-8 h-12 text-base"
                >
                  Talk to {content.demoName} now
                  <ArrowRight className="ml-2 w-4 h-4" />
                </Button>
              </Link>
              <Link href="/request-demo">
                <Button
                  size="lg"
                  variant="outline"
                  className="px-8 h-12 text-base"
                >
                  Request a Demo
                </Button>
              </Link>
            </div>
            <p className="mt-4 text-sm text-muted-foreground">
              {content.demoBlurb}
            </p>
          </div>
        </section>

        <section className="py-12 md:py-16 bg-muted/30 border-y border-border/40">
          <div className="container max-w-3xl mx-auto px-4">
            <h2 className="text-2xl font-bold tracking-tight text-center">
              Sound familiar?
            </h2>
            <ul className="mt-6 space-y-3">
              {content.pains.map((pain) => (
                <li key={pain} className="flex items-start gap-3">
                  <CheckCircle2 className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
                  <span className="text-muted-foreground leading-relaxed">
                    {pain}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section className="py-12 md:py-16">
          <div className="container max-w-5xl mx-auto px-4">
            <h2 className="text-2xl font-bold tracking-tight text-center md:text-3xl">
              What your AI front desk handles
            </h2>
            <div className="mt-8 grid gap-6 md:grid-cols-2">
              {content.outcomes.map((outcome) => (
                <Card key={outcome.title}>
                  <CardContent className="pt-6">
                    <h3 className="text-lg font-bold">{outcome.title}</h3>
                    <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
                      {outcome.description}
                    </p>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        </section>

        <section className="py-12 md:py-16 bg-muted/30 border-y border-border/40">
          <div className="container max-w-3xl mx-auto px-4 text-center">
            <h2 className="text-2xl font-bold tracking-tight md:text-3xl">
              Live in 48 hours — we set it up with you
            </h2>
            <p className="mt-4 text-muted-foreground md:text-lg leading-relaxed">
              Request a demo, we configure your number, calendar, and test
              calls around your business, and you approve every word before
              it answers. Pilot plans from $79/mo as you grow.
            </p>
            <Link href="/request-demo" className="inline-block mt-6">
              <Button
                size="lg"
                className="bg-blue-600 hover:bg-blue-700 px-8 h-12 text-base"
              >
                Request a Demo
                <ArrowRight className="ml-2 w-4 h-4" />
              </Button>
            </Link>
          </div>
        </section>

        <section className="py-12 md:py-16">
          <div className="container max-w-3xl mx-auto px-4">
            <h2 className="text-2xl font-bold tracking-tight text-center">
              Common questions
            </h2>
            <div className="mt-8 space-y-6">
              {content.faqs.map((faq) => (
                <div key={faq.question}>
                  <h3 className="font-bold">{faq.question}</h3>
                  <p className="mt-1 text-muted-foreground leading-relaxed">
                    {faq.answer}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
