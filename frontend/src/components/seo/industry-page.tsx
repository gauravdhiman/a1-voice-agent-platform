import Link from "next/link";
import { ArrowRight, ArrowUpRight, CheckCircle2 } from "lucide-react";
import { PublicThemeRoot } from "@/components/public-theme/public-theme-root";
import { PublicHeader } from "@/components/public-theme/public-header";
import { PublicFooter } from "@/components/public-theme/public-footer";
import pt from "@/components/public-theme/public-theme.module.css";

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
 * Shared template for vertical SEO landing pages, styled with the public
 * atmosphere theme (same header, tokens, and day/night choice as the
 * homepage).
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
    <PublicThemeRoot>
      <div className={pt.page}>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(faqJsonLd) }}
        />
        <div className={pt.glow} aria-hidden="true" />
        <PublicHeader />

        <main style={{ position: "relative" }}>
          <section style={{ padding: "88px 6.5% 72px" }}>
            <div
              style={{ maxWidth: 760, margin: "0 auto", textAlign: "center" }}
            >
              <p className={pt.eyebrow} style={{ justifyContent: "center" }}>
                <span className={pt.statusDot} />
                AI FRONT DESK FOR {content.slug.toUpperCase()}
              </p>
              <h1
                className={pt.title}
                style={{
                  fontSize: "clamp(40px, 5vw, 68px)",
                  margin: "28px 0 20px",
                }}
              >
                {content.headline}
              </h1>
              <p
                className={pt.lede}
                style={{ maxWidth: 620, margin: "0 auto" }}
              >
                {content.subhead}
              </p>
              <div
                style={{
                  marginTop: 36,
                  display: "flex",
                  gap: 22,
                  justifyContent: "center",
                  flexWrap: "wrap",
                  alignItems: "center",
                }}
              >
                <Link className={pt.primary} href={`/demo/${content.demoSlug}`}>
                  Talk to {content.demoName} now
                  <ArrowRight size={16} />
                </Link>
                <Link className={pt.textLink} href="/request-demo">
                  Request a Demo <ArrowUpRight size={16} />
                </Link>
              </div>
              <p
                className={pt.smallDetail}
                style={{ marginTop: 22, fontSize: 10 }}
              >
                {content.demoBlurb}
              </p>
            </div>
          </section>

          <section
            style={{ borderTop: "1px solid var(--line)", padding: "64px 6.5%" }}
          >
            <div style={{ maxWidth: 680, margin: "0 auto" }}>
              <h2
                className={pt.title}
                style={{
                  fontSize: "clamp(28px, 3vw, 40px)",
                  textAlign: "center",
                }}
              >
                Sound <span>familiar?</span>
              </h2>
              <ul
                style={{
                  marginTop: 32,
                  display: "flex",
                  flexDirection: "column",
                  gap: 18,
                  padding: 0,
                  listStyle: "none",
                }}
              >
                {content.pains.map((pain) => (
                  <li
                    key={pain}
                    style={{
                      display: "flex",
                      gap: 14,
                      alignItems: "flex-start",
                    }}
                  >
                    <CheckCircle2
                      size={20}
                      style={{ color: "var(--accent)", flexShrink: 0 }}
                    />
                    <span style={{ color: "var(--muted)", lineHeight: 1.8 }}>
                      {pain}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </section>

          <section
            style={{ borderTop: "1px solid var(--line)", padding: "64px 6.5%" }}
          >
            <div style={{ maxWidth: 960, margin: "0 auto" }}>
              <h2
                className={pt.title}
                style={{
                  fontSize: "clamp(28px, 3vw, 40px)",
                  textAlign: "center",
                }}
              >
                What your AI front desk <span>handles</span>
              </h2>
              <div
                style={{
                  marginTop: 40,
                  display: "grid",
                  gap: 24,
                  gridTemplateColumns:
                    "repeat(auto-fit, minmax(min(100%, 320px), 1fr))",
                }}
              >
                {content.outcomes.map((outcome) => (
                  <div
                    key={outcome.title}
                    className={pt.panel}
                    style={{ padding: 30 }}
                  >
                    <h3
                      style={{
                        fontSize: 20,
                        fontWeight: 400,
                        letterSpacing: "-0.03em",
                      }}
                    >
                      {outcome.title}
                    </h3>
                    <p
                      style={{
                        marginTop: 10,
                        fontSize: 13,
                        lineHeight: 1.8,
                        color: "var(--muted)",
                      }}
                    >
                      {outcome.description}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </section>

          <section
            style={{
              borderTop: "1px solid var(--line)",
              padding: "64px 6.5%",
              textAlign: "center",
            }}
          >
            <div style={{ maxWidth: 640, margin: "0 auto" }}>
              <p className={pt.eyebrow} style={{ justifyContent: "center" }}>
                LIVE IN 48 HOURS
              </p>
              <h2
                className={pt.title}
                style={{ fontSize: "clamp(28px, 3vw, 40px)", marginTop: 20 }}
              >
                We set it up <span>with you</span>
              </h2>
              <p className={pt.lede} style={{ marginTop: 16 }}>
                Request a demo, we configure your number, calendar, and test
                calls around your business, and you approve every word before it
                answers. Pilot plans from $79/mo as you grow.
              </p>
              <div style={{ marginTop: 32 }}>
                <Link className={pt.primary} href="/request-demo">
                  Request a Demo <ArrowRight size={16} />
                </Link>
              </div>
            </div>
          </section>

          <section
            style={{ borderTop: "1px solid var(--line)", padding: "64px 6.5%" }}
          >
            <div style={{ maxWidth: 680, margin: "0 auto" }}>
              <h2
                className={pt.title}
                style={{
                  fontSize: "clamp(28px, 3vw, 40px)",
                  textAlign: "center",
                }}
              >
                Common <span>questions</span>
              </h2>
              <div
                style={{
                  marginTop: 32,
                  display: "flex",
                  flexDirection: "column",
                  gap: 28,
                }}
              >
                {content.faqs.map((faq) => (
                  <div key={faq.question}>
                    <h3 style={{ fontSize: 17 }}>{faq.question}</h3>
                    <p
                      style={{
                        marginTop: 8,
                        color: "var(--muted)",
                        lineHeight: 1.8,
                        fontSize: 14,
                      }}
                    >
                      {faq.answer}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </section>
        </main>

        <PublicFooter />
      </div>
    </PublicThemeRoot>
  );
}
