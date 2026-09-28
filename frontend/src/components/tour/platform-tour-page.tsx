"use client";

import Link from "next/link";
import { ArrowDown, ArrowUpRight, Check, Play } from "lucide-react";
import { SITE_SALES_EMAIL } from "@/lib/site-config";
import { PublicThemeRoot } from "@/components/public-theme/public-theme-root";
import { PublicHeader } from "@/components/public-theme/public-header";
import { PublicFooter } from "@/components/public-theme/public-footer";
import pt from "@/components/public-theme/public-theme.module.css";
import { TourSections } from "./tour-sections";
import styles from "./platform-tour.module.css";

const setupSteps = [
  {
    n: "01",
    title: "Tell us how you work.",
    body: "Your services, prices, hours, and the calls you want handled. Start with a 30-second brief.",
  },
  {
    n: "02",
    title: "We build it with you.",
    body: "Test calls until it sounds like your front desk. Nothing reaches customers until you say so.",
  },
  {
    n: "03",
    title: "Approve it. Live in about 48 hours.",
    body: "You test and approve before it goes live. Then every call gets answered.",
  },
];

/**
 * Public guided tour of the 24x7 AI platform, written for non-technical
 * business owners: five chapters (create, answer everywhere, connect tools,
 * teach skills, review calls), each pairing plain-language steps with a
 * stylized preview of the real product screen. Demo content is fictional
 * and every preview is tagged as an illustration.
 */
export function PlatformTourPage() {
  return (
    <PublicThemeRoot>
      <div className={`${pt.page} ${styles.tourPage}`}>
        <a className={styles.skip} href="#tour-chapters">
          Skip to the tour
        </a>
        <PublicHeader />
        <main>
          <section className={pt.industryHero} aria-labelledby="tour-heading">
            <div style={{ maxWidth: 780, margin: "0 auto", textAlign: "center", width: "100%" }}>
              <p className={pt.eyebrow} style={{ justifyContent: "center" }}>
                <span className={pt.statusDot} />
                HOW IT WORKS · NO CODING REQUIRED
              </p>
              <h1
                id="tour-heading"
                className={pt.title}
                style={{ fontSize: "clamp(44px, 5.4vw, 76px)", margin: "28px 0 20px" }}
              >
                From hello to booked, <span>on every call.</span>
              </h1>
              <p className={pt.lede} style={{ maxWidth: 640, margin: "0 auto" }}>
                Create your agent in plain words, answer on your number and
                website, connect the tools you already use, and review every
                call — live in about 48 hours.
              </p>
              <div className={pt.industryHeroActions}>
                <Link className={pt.primary} href="/request-demo">
                  Request a demo <ArrowUpRight size={16} />
                </Link>
                <Link
                  className={pt.secondaryOutline}
                  href="/demo/pleasant-pediatric-appointments"
                  aria-label="Hear Alex handle a live demo call"
                >
                  <span className={styles.playCircle}>
                    <Play size={11} fill="currentColor" />
                  </span>{" "}
                  Hear a live demo
                </Link>
              </div>
              <p className={pt.smallDetail} style={{ marginTop: 22, fontSize: 10 }}>
                WE SET IT UP · YOU TEST AND APPROVE · THEN IT GOES LIVE
              </p>
            </div>
          </section>

          <section
            id="tour-chapters"
            aria-labelledby="tour-chapters-heading"
            className={styles.chapters}
          >
            <div className={styles.contain}>
              <p className={pt.eyebrow}>THE PLATFORM, CHAPTER BY CHAPTER</p>
              <h2 id="tour-chapters-heading" className={styles.chaptersTitle}>
                Five minutes. <span>Five superpowers.</span>
              </h2>
              <TourSections />
            </div>
          </section>

          <section aria-labelledby="tour-setup-heading" className={styles.setup}>
            <div className={styles.contain}>
              <p className={pt.eyebrow}>LIVE IN ABOUT 48 HOURS</p>
              <h2 id="tour-setup-heading" className={styles.chaptersTitle}>
                Easy to set up. <span>Easy to run.</span>
              </h2>
              <ol className={styles.setupList}>
                {setupSteps.map((item) => (
                  <li key={item.n}>
                    <span className={styles.setupNumber}>{item.n}</span>
                    <div>
                      <h3>{item.title}</h3>
                      <p>{item.body}</p>
                    </div>
                  </li>
                ))}
              </ol>
            </div>
          </section>

          <section aria-labelledby="tour-closing-heading" className={styles.closing}>
            <div className={styles.contain}>
              <p className={pt.eyebrow}>
                <span className={pt.statusDot} /> YOUR PHONES, COVERED.
              </p>
              <h2 id="tour-closing-heading" className={styles.chaptersTitle}>
                Stop losing work <span>to voicemail.</span>
              </h2>
              <p className={styles.closingCopy}>
                Start with a concierge pilot, built around you.
                <br />
                Monthly plans from $79 as you grow.
              </p>
              <div className={pt.industryHeroActions} style={{ justifyContent: "flex-start" }}>
                <Link className={pt.primary} href="/request-demo">
                  Request a demo <ArrowUpRight size={16} />
                </Link>
                <a className={pt.textLink} href={`mailto:${SITE_SALES_EMAIL}`}>
                  Talk to sales <ArrowUpRight size={16} />
                </a>
              </div>
              <p className={styles.scrollHint}>
                <a href="#tour-chapters">
                  <ArrowDown size={14} /> BACK TO THE TOUR
                </a>
                <span>
                  <Check size={12} aria-hidden="true" /> NO CODING · TEST BEFORE IT GOES LIVE
                </span>
              </p>
            </div>
          </section>
        </main>
        <PublicFooter />
      </div>
    </PublicThemeRoot>
  );
}
