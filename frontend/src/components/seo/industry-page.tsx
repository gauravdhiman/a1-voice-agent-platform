import Link from "next/link";
import { ArrowRight, ArrowUpRight, CheckCircle2 } from "lucide-react";
import { PublicThemeRoot } from "@/components/public-theme/public-theme-root";
import { PublicHeader } from "@/components/public-theme/public-header";
import { PublicFooter } from "@/components/public-theme/public-footer";
import { SITE_AI_SERVICES_URL } from "@/lib/site-config";
import pt from "@/components/public-theme/public-theme.module.css";
import { ScrollCue } from "@/components/public-theme/scroll-cue";

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

/** A research source linked from the proof section. */
export interface IndustrySource {
  /** Human-readable source name. */
  label: string;
  /** Public URL for the underlying research. */
  href: string;
}

/** One benchmark card shown between the pain and solution sections. */
export interface IndustryProofPoint {
  /** The large number, such as `43%` or `Up to 85%`. */
  value: string;
  /** What the number measures, written for a business owner. */
  label: string;
}

/** Evidence that gives a vertical landing page a credible reason to act. */
export interface IndustryProof {
  /** Small section label. */
  eyebrow: string;
  /** Conversion-oriented heading for the evidence. */
  title: string;
  /** Short explanation of why the benchmark matters. */
  description: string;
  /** Usually three points; keep this compact on the page. */
  points: IndustryProofPoint[];
  /** Plain-language qualification for the research. */
  sourceNote: string;
  /** Source links shown below the cards. */
  sources: IndustrySource[];
}

/** All copy for a vertical landing page. */
export interface IndustryPageContent {
  /** URL slug (dental, hvac, restaurants). */
  slug: string;
  /** Human-readable label shown in the public page eyebrow. */
  label?: string;
  /** H1 headline. */
  headline: string;
  /** Hero sub-copy. */
  subhead: string;
  /** Missed-call pains this vertical feels. */
  pains: string[];
  /** What the AI handles, as outcome blocks. */
  outcomes: IndustryOutcome[];
  /** Demo agent slug to try live, when this vertical has a public demo. */
  demoSlug?: string;
  /** One-line demo pitch or a transparent no-demo note. */
  demoBlurb?: string;
  /** Optional benchmark evidence for this vertical. */
  proof?: IndustryProof;
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
 * Same skeleton every time (pain → proof → live demo or request → concierge setup →
 * outcomes → pricing anchor → FAQ), unique copy per vertical so each
 * page earns its own search intent.
 */
export function IndustryPage({ content }: IndustryPageProps) {
  const handledOutcomes = [
    ...content.outcomes,
    {
      title: "Your existing business tools",
      description:
        "We connect the workflow to the calendar, CRM, dispatch system, spreadsheet, or other tools your team already uses. Custom integrations are welcome.",
    },
  ];
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
          <section className={pt.industryHero}>
            <div
              style={{
                maxWidth: 760,
                margin: "0 auto",
                textAlign: "center",
                width: "100%",
              }}
            >
              <p className={pt.eyebrow} style={{ justifyContent: "center" }}>
                <span className={pt.statusDot} />
                AI FRONT DESK FOR{" "}
                {(content.label ?? content.slug).toUpperCase()}
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
              <div className={pt.industryHeroActions}>
                {content.demoSlug ? (
                  <Link
                    className={pt.primary}
                    href={`/demo/${content.demoSlug}`}
                  >
                    Try the live demo
                    <ArrowRight size={16} />
                  </Link>
                ) : (
                  <Link className={pt.primary} href="/request-demo">
                    Request this workflow <ArrowRight size={16} />
                  </Link>
                )}
                {content.demoSlug ? (
                  <Link className={pt.secondaryOutline} href="/request-demo">
                    Request a Demo <ArrowUpRight size={16} />
                  </Link>
                ) : null}
              </div>
              <p
                className={pt.lede}
                style={{
                  maxWidth: 620,
                  margin: "18px auto 0",
                  fontSize: 13,
                }}
              >
                No press-1 menus or hold music. Your 24x7 AI assistant answers
                right away, follows your instructions, and records callback
                requests when a caller needs your team.
              </p>
              <p
                className={pt.smallDetail}
                style={{ marginTop: 14, fontSize: 10 }}
              >
                {content.demoBlurb ??
                  "No public demo yet - tell us what your calls need and we will shape the first workflow with you."}
              </p>
            </div>
            <ScrollCue
              href="#industry-pain-points"
              label="Scroll to explore"
              className={pt.heroScrollCue}
            />
          </section>

          <section
            id="industry-pain-points"
            className={pt.scrollTarget}
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
                      style={{ color: "var(--public-accent)", flexShrink: 0 }}
                    />
                    <span
                      style={{ color: "var(--public-muted)", lineHeight: 1.8 }}
                    >
                      {pain}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </section>

          {content.proof ? (
            <section
              className={pt.proofSection}
              aria-labelledby="proof-heading"
            >
              <div className={pt.proofInner}>
                <div className={pt.proofHeader}>
                  <div>
                    <p className={pt.eyebrow}>{content.proof.eyebrow}</p>
                    <h2
                      className={`${pt.title} ${pt.proofTitle}`}
                      id="proof-heading"
                    >
                      {content.proof.title}
                    </h2>
                  </div>
                  <p className={pt.proofDescription}>
                    {content.proof.description}
                  </p>
                </div>
                <div className={pt.proofGrid}>
                  {content.proof.points.map((point) => (
                    <div
                      className={pt.proofPoint}
                      key={point.value + point.label}
                    >
                      <strong className={pt.proofValue}>{point.value}</strong>
                      <p>{point.label}</p>
                    </div>
                  ))}
                </div>
                <p className={pt.proofSource}>
                  {content.proof.sourceNote}{" "}
                  {content.proof.sources.map((source, index) => (
                    <span key={source.href}>
                      {index > 0 ? " · " : ""}
                      <a href={source.href} target="_blank" rel="noreferrer">
                        {source.label}
                        <ArrowUpRight size={12} aria-hidden="true" />
                      </a>
                    </span>
                  ))}
                </p>
              </div>
            </section>
          ) : null}

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
                className={pt.outcomeGrid}
                style={{
                  marginTop: 40,
                  display: "grid",
                  gap: 24,
                  gridTemplateColumns:
                    "repeat(auto-fit, minmax(min(100%, 320px), 1fr))",
                }}
              >
                {handledOutcomes.map((outcome) => (
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
                        color: "var(--public-muted)",
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
                Request a demo, we configure your number, calendar or scheduling
                system, and test calls around your business. You test and
                approve before it goes live. Plans start at $49/month and
                include up to 250 call minutes.
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
                        color: "var(--public-muted)",
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

          <section
            className={pt.secondaryCta}
            aria-labelledby="broader-ai-heading"
          >
            <div className={pt.secondaryCtaInner}>
              <div>
                <p className={pt.eyebrow}>BEYOND THE FRONT DESK</p>
                <h2
                  id="broader-ai-heading"
                  className={`${pt.title} ${pt.secondaryCtaTitle}`}
                >
                  Need more than voice?{" "}
                  <span>We can build the workflow too.</span>
                </h2>
              </div>
              <div>
                <p className={pt.secondaryCtaCopy}>
                  We also design custom AI solutions that automate the daily
                  workflows around your business. Explore the broader practice
                  when your needs go beyond phone calls.
                </p>
                <a
                  className={pt.secondaryCtaLink}
                  href={SITE_AI_SERVICES_URL}
                  target="_blank"
                  rel="noreferrer"
                >
                  Explore custom AI solutions <ArrowUpRight size={15} />
                </a>
              </div>
            </div>
          </section>
        </main>

        <PublicFooter />
      </div>
    </PublicThemeRoot>
  );
}
