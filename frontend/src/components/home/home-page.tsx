"use client";

import Link from "next/link";
import {
  ArrowRight,
  ArrowUpRight,
  AudioLines,
  CalendarCheck,
  CalendarDays,
  Check,
  Database,
  Globe,
  Mail,
  Moon,
  MoveUpRight,
  Phone,
  Play,
  Plug,
  Sun,
  UtensilsCrossed,
  Wrench,
} from "lucide-react";
import {
  SITE_AI_SERVICES_URL,
  SITE_NAME,
  SITE_SALES_EMAIL,
} from "@/lib/site-config";
import { usePublicTheme } from "@/components/public-theme/public-theme-context";
import { PublicHeader } from "@/components/public-theme/public-header";
import { ScrollCue } from "@/components/public-theme/scroll-cue";
import { AuroraField } from "./aurora-field";
import { ConcurrencyDiagram } from "./concurrency-diagram";
import { Reveal } from "./reveal";
import styles from "./home-page.module.css";

const industries = [
  {
    name: "Dental & medical",
    detail: "New-patient intake, cleanings and exams booked, even after hours.",
    href: "/dental-appointment-booking",
    number: "01",
  },
  {
    name: "HVAC, plumbing & roofing",
    detail: "Every service call captured while your crew is out on site.",
    href: "/hvac-service-call-answering",
    number: "02",
  },
  {
    name: "Restaurants & cafés",
    detail:
      "Reservations, party bookings and order questions, handled mid-rush.",
    href: "/restaurant-order-taking",
    number: "03",
  },
  {
    name: "Plumbing & emergency home services",
    detail:
      "Urgency, service area and job details captured while the crew is out.",
    href: "/plumbing-service-requests",
    number: "04",
  },
  {
    name: "Independent auto repair",
    detail:
      "Vehicle details captured and service appointments requested on the call.",
    href: "/auto-repair-service-booking",
    number: "05",
  },
  {
    name: "Veterinary clinics",
    detail: "Routine visits moving while your team cares for patients.",
    href: "/veterinary-appointment-booking",
    number: "06",
  },
  {
    name: "Salons, spas & clinics",
    detail: "Chairs filled with bookings while stylists stay with clients.",
    href: "/salon-appointment-booking",
    number: "07",
  },
  {
    name: "Real estate & local services",
    detail: "Every enquiry captured with the next human step clearly defined.",
    href: "/real-estate-lead-capture",
    number: "08",
  },
  {
    name: "Your kind of business",
    detail: "Tell us how you work. We build the front desk around it.",
    href: "/request-demo",
    number: "09",
  },
];

/** Homepage: a business-first introduction to 24x7 AI call answering,
 * bookings, lead capture, and callback follow-up. */
export function HomePage() {
  const { theme, toggleTheme } = usePublicTheme();

  return (
    <div
      className={styles.home}
      data-theme={theme}
    >
      <a className={styles.skip} href="#main-content">
        Skip to content
      </a>
      <PublicHeader />

      <main id="main-content">
        {/* ── Hero ─────────────────────────────────────────── */}
        <section
          className={styles.hero}
          data-aurora
          aria-labelledby="hero-heading"
        >
          <div className={styles.aurora} aria-hidden="true">
            <AuroraField theme={theme} paused={false} />
          </div>
          <div className={styles.heroGrid} aria-hidden="true" />
          <div className={styles.heroInner}>
            <div className={styles.heroCopy}>
              <p className={styles.eyebrow}>
                <span className={styles.statusDot} /> AI FRONT DESK FOR LOCAL
                BUSINESSES · LIVE IN 48 HOURS
              </p>
              <h1 id="hero-heading">
                Never miss a call.
                <br />
                <span>Never miss a customer.</span>
              </h1>
              <p className={styles.heroDescription}>
                Your 24x7 AI phone assistant answers right away on your business
                number and through a voice button on your website. It follows
                your instructions to answer questions, book appointments, take
                orders and capture callback requests. No press-1 menus or
                waiting on hold, even after you close.
              </p>
              <div className={styles.ctaRow}>
                <Link className={styles.primary} href="/request-demo">
                  Meet your AI front desk <ArrowUpRight size={18} />
                </Link>
                <a className={styles.secondaryBtn} href="#demos">
                  <span className={styles.playCircle}>
                    <Play size={11} fill="currentColor" />
                  </span>{" "}
                  Hear it handle a real call
                </a>
              </div>
              <p className={styles.heroNote}>
                Concierge setup with you · You test and approve before it goes
                live · No coding required. Plans from $49/month, including up to 250 call minutes.
              </p>
            </div>
            <div className={styles.heroVisual}>
              <ConcurrencyDiagram paused={false} />
            </div>
          </div>
          <div className={styles.heroBottom}>
            <ScrollCue
              href="#features"
              label="Scroll to see what’s possible"
              className={styles.homeScrollCue}
            />
            <span className={styles.heroBottomRight}>
              <span className={styles.heroBottomTag}>
                HUMAN CONNECTION. MEET ALWAYS ON.
              </span>
            </span>
          </div>
        </section>

        {/* ── Use cases ────────────────────────────────────── */}
        <section
          id="features"
          className={styles.features}
          aria-labelledby="answer-heading"
        >
          <Reveal>
            <p className={styles.eyebrow}>01 / ANSWERS ON THE SPOT</p>
            <h2 id="answer-heading">
              Routine questions?
              <br />
              <span>Resolved on the call.</span>
            </h2>
            <p className={styles.sectionSub}>
              Your AI assistant answers common questions about hours, prices,
              services, orders and directions using your business information.
              Customers get help right away without pulling you or your staff
              off the job.
            </p>
          </Reveal>
          <div className={styles.featureGrid}>
            <Reveal delay={60}>
              <article id="bookings" className={styles.featureCard}>
                <span className={styles.featureIcon}>
                  <Phone size={20} />
                </span>
                <p className={styles.featureKicker}>AN EVERYDAY MOMENT</p>
                <p className={styles.featureQuote}>
                  &ldquo;What are your prices for a deep cleaning?&rdquo;
                </p>
                <p className={styles.agentReply}>
                  &ldquo;Deep cleanings start at $149. Want me to hold a slot
                  for you?&rdquo;
                </p>
                <div className={styles.featureFoot}>
                  <AudioLines size={16} />
                  <span>
                    Zero interruptions to your day.{" "}
                    <span className={styles.illusTag}>
                      ILLUSTRATIVE CONVERSATION
                    </span>
                  </span>
                </div>
              </article>
            </Reveal>
            <Reveal delay={140}>
              <article className={styles.featureCard}>
                <span className={styles.featureIcon}>
                  <CalendarCheck size={20} />
                </span>
                <p className={styles.featureKicker}>02 / BOOKINGS THAT GROW REVENUE</p>
                <h3>
                  &ldquo;Can I book?&rdquo; becomes &ldquo;You&apos;re
                  booked.&rdquo;
                </h3>
                <p>
                  Checks your real availability, books and reschedules
                  appointments, and writes everything to your business calendar,
                  with confirmations that cut no-shows. Every open slot turns into
                  paying work.
                </p>
                <div className={styles.bookingChip}>
                  <span className={styles.smallDetail}>EXAMPLE OUTCOME</span>
                  <strong>Thu 2:00 PM · Maria G., booked</strong>
                  <span>Time confirmed · On your calendar · Reminder set</span>
                </div>
              </article>
            </Reveal>
            <Reveal delay={220}>
              <article id="connections" className={styles.featureCard}>
                <span className={styles.featureIcon}>
                  <Moon size={20} />
                </span>
                <p className={styles.featureKicker}>03 / LEADS CAPTURED AFTER HOURS</p>
                <h3>
                  Close up shop. <span>Keep winning work.</span>
                </h3>
                <p>
                  Evenings, weekends and holidays, your AI assistant answers
                  calls, captures the caller&apos;s name, number and reason, and
                  flags urgent requests. When a caller needs your team, it
                  records a callback request with the context needed to follow
                  up. No voicemail to sort through.
                </p>
                <ul className={styles.outcomeList}>
                  <li>
                    <Check size={15} /> Name, number &amp; reason captured on
                    every call
                  </li>
                  <li>
                    <Check size={15} /> Instant notification, straight to you in
                    seconds
                  </li>
                  <li>
                    <Check size={15} /> Urgent flagged, routine ready for the
                    morning. Nothing lost to voicemail
                  </li>
                </ul>
                <a className={styles.textLink} href="#how-it-works">
                  See the 48-hour setup <ArrowRight size={16} />
                </a>
              </article>
            </Reveal>
          </div>
          <p className={styles.smallDetail}>
            HOURS · PRICES · SERVICES · ORDER UPDATES, TRAINED IN. · YOUR BUSINESS
            CALENDAR · NO DOUBLE-BOOKING · FEWER NO-SHOWS
          </p>
        </section>

        {/* ── Proof ────────────────────────────────────────── */}
        <section
          id="proof"
          className={styles.proof}
          aria-labelledby="proof-heading"
        >
          <div className={styles.contain}>
          <Reveal>
            <div className={styles.sectionTop}>
              <p className={styles.eyebrow}>THE CALL IS ALREADY WARM</p>
              <span className={styles.smallDetail}>
                DIRECTIONAL BENCHMARKS · NOT PROMISES
              </span>
            </div>
            <div className={styles.proofHeading}>
              <h2 id="proof-heading">
                Answering is the first
                <br />
                <span>conversion.</span>
              </h2>
              <p>
                Independent call research points to the same opportunity across
                local businesses: the customer has already raised their hand. The
                front desk has to make the next step easy.
              </p>
            </div>
          </Reveal>
          <div className={styles.proofGrid}>
            <article className={styles.proofCard}>
              <strong>Up to 85%</strong>
              <p>of callers who reach voicemail may not call back.</p>
              <span className={styles.smallDetail}>
                CALLRAIL · 1.1M SMB CONVERSATIONS
              </span>
            </article>
            <article className={styles.proofCard}>
              <strong>42%</strong>
              <p>of phone leads convert on the call.</p>
              <span className={styles.smallDetail}>INVOCA · 70M+ CALLS</span>
            </article>
            <article className={styles.proofCard}>
              <strong>56%</strong>
              <p>of business callers speak with a person.</p>
              <span className={styles.smallDetail}>INVOCA · 70M+ CALLS</span>
            </article>
          </div>
          <p className={styles.proofNote}>
            Benchmarks are directional and do not predict your results.{" "}
            <a
              href="https://www.callrail.com/blog/callrail-releases-benchmark-report"
              target="_blank"
              rel="noreferrer"
            >
              CallRail SMB benchmark <ArrowUpRight size={12} aria-hidden="true" />
            </a>{" "}
            ·{" "}
            <a
              href="https://www.invoca.com/reports/the-invoca-lead-conversion-benchmarks-report-2026"
              target="_blank"
              rel="noreferrer"
            >
              Invoca 2026 benchmark <ArrowUpRight size={12} aria-hidden="true" />
            </a>
          </p>
          </div>
        </section>

        {/* ── Demos ────────────────────────────────────────── */}
        <section
          id="demos"
          className={styles.demos}
          aria-labelledby="demo-heading"
        >
          <Reveal>
            <div className={styles.sectionTop}>
              <p className={styles.eyebrow}>LESS IMAGINING. MORE EXPERIENCING.</p>
              <span className={styles.smallDetail}>
                REAL AI ASSISTANTS. TRY A CONVERSATION.
              </span>
            </div>
            <div className={styles.sectionHeading}>
              <h2 id="demo-heading">
                Don’t take our word.
                <br />
                <span>Have a word.</span>
              </h2>
              <p>
                Talk with an AI assistant in a live demo. Book a visit, request
                a repair, or place an order. Hear how it handles an after-hours
                call.
              </p>
            </div>
          </Reveal>
          <div className={styles.demoGrid}>
            <Reveal delay={0}>
              <Link
                href="/demo/pleasant-pediatric-appointments"
                className={styles.demoCard}
                aria-label="Talk to Alex: try the appointment demo"
              >
                <div className={`${styles.demoArt} ${styles.artA}`} aria-hidden="true">
                  <span className={styles.demoGlyph}>
                    <CalendarCheck size={30} />
                  </span>
                  <span className={styles.demoWave}>
                    <i /><i /><i /><i /><i /><i /><i />
                  </span>
                  <span className={styles.demoArtLabel}>Appointment bookings</span>
                  <span className={styles.demoArtSub}>Real availability · confirmed</span>
                  <ArrowUpRight />
                </div>
                <div className={styles.demoBody}>
                  <p className={styles.eyebrow}>THE NEXT APPOINTMENT</p>
                  <h3>
                    A missed call.
                    <br />
                    Becomes a booked chair.
                  </h3>
                  <p>
                    Try booking a dental visit in the live demo. Real availability,
                    confirmation, and a calendar event your front desk didn&apos;t
                    have to touch.
                  </p>
                  <span className={styles.demoLink}>
                    <span className={styles.playCircle}>
                      <Play size={11} fill="currentColor" />
                    </span>{" "}
                    Try the appointment demo <ArrowUpRight size={16} />
                  </span>
                </div>
              </Link>
            </Reveal>
            <Reveal delay={120}>
              <Link
                href="/demo/copper-ridge-service-request"
                className={styles.demoCard}
                aria-label="Talk to Jordan: try the service demo"
              >
                <div className={`${styles.demoArt} ${styles.artB}`} aria-hidden="true">
                  <span className={styles.demoGlyph}>
                    <Wrench size={30} />
                  </span>
                  <span className={styles.demoWave}>
                    <i /><i /><i /><i /><i /><i /><i />
                  </span>
                  <span className={styles.demoArtLabel}>Service requests</span>
                  <span className={styles.demoArtSub}>Symptoms · address · window</span>
                  <ArrowUpRight />
                </div>
                <div className={styles.demoBody}>
                  <p className={styles.eyebrow}>THE NEXT JOB</p>
                  <h3>
                    Out on a job.
                    <br />
                    Still winning the next.
                  </h3>
                  <p>
                    Ask for HVAC service in the live demo. Symptoms, address, and time
                    window captured into a clean request. Emergencies flagged,
                    routine booked.
                  </p>
                  <span className={styles.demoLink}>
                    <span className={styles.playCircle}>
                      <Play size={11} fill="currentColor" />
                    </span>{" "}
                    Try the service demo <ArrowUpRight size={16} />
                  </span>
                </div>
              </Link>
            </Reveal>
            <Reveal delay={200}>
              <Link
                href="/demo/verdi-table-restaurant"
                className={styles.demoCard}
                aria-label="Talk to Sofia: try the restaurant demo"
              >
                <div className={`${styles.demoArt} ${styles.artC}`} aria-hidden="true">
                  <span className={styles.demoGlyph}>
                    <UtensilsCrossed size={30} />
                  </span>
                  <span className={styles.demoWave}>
                    <i /><i /><i /><i /><i /><i /><i />
                  </span>
                  <span className={styles.demoArtLabel}>Restaurant orders</span>
                  <span className={styles.demoArtSub}>Items · quantities · contact</span>
                  <ArrowUpRight />
                </div>
                <div className={styles.demoBody}>
                  <p className={styles.eyebrow}>THE NEXT ORDER</p>
                  <h3>
                    In the weeds.
                    <br />
                    Still serving the next table.
                  </h3>
                  <p>
                    Ask about the menu or place a pickup order in the live demo. Items,
                    quantities, and contact details captured while your team
                    keeps the room moving.
                  </p>
                  <span className={styles.demoLink}>
                    <span className={styles.playCircle}>
                      <Play size={11} fill="currentColor" />
                    </span>{" "}
                    Try the restaurant demo <ArrowUpRight size={16} />
                  </span>
                </div>
              </Link>
            </Reveal>
          </div>
          <p className={styles.demoNote}>
            Interactive demos use example businesses. Your AI assistant is set
            up with your services and instructions.
          </p>
        </section>

        {/* ── Guided tour ──────────────────────────────────── */}
        <section
          id="tour"
          className={styles.tourBand}
          aria-labelledby="tour-heading"
        >
          <Reveal>
            <div className={styles.tourInner}>
              <div>
                <p className={styles.eyebrow}>HOW IT WORKS · FIVE-MINUTE TOUR</p>
                <h2 id="tour-heading">
                  See your AI front desk
                  <br />
                  <span>at work.</span>
                </h2>
                <p className={styles.tourCopy}>
                  See how your AI assistant answers your business number and
                  website, connects to your tools, follows your instructions,
                  and keeps every call easy to review.
                </p>
                <div className={styles.ctaRow}>
                  <Link className={styles.primary} href="/how-it-works">
                    Take the guided tour <ArrowUpRight size={18} />
                  </Link>
                </div>
              </div>
              <ol className={styles.tourChapters}>
                {[
                  ["01", "Create", "Describe it in plain words", "tour-create"],
                  [
                    "02",
                    "Answer everywhere",
                    "Number + website, one assistant",
                    "tour-answer-everywhere",
                  ],
                  ["03", "Connect tools", "Bookings land themselves", "tour-connect-tools"],
                  ["04", "Set instructions", "Rules, not code", "tour-teach-skills"],
                  ["05", "Review calls", "Every call, on record", "tour-review-calls"],
                ].map(([number, name, detail, anchor]) => (
                  <li key={number}>
                    <Link href={`/how-it-works#${anchor}`}>
                      <span className={styles.smallDetail}>{number}</span>
                      <span>
                        <strong>{name}</strong>
                        <small>{detail}</small>
                      </span>
                      <ArrowUpRight size={17} />
                    </Link>
                  </li>
                ))}
              </ol>
            </div>
          </Reveal>
        </section>

        {/* ── Industries ───────────────────────────────────── */}
        <section
          id="industries"
          className={styles.industries}
          aria-labelledby="industries-heading"
        >
          <Reveal>
            <p className={styles.eyebrow}>
              SMALL TEAMS. BIG AMBITIONS. EVERY BUSINESS IN BETWEEN.
            </p>
            <h2 id="industries-heading">
              You do what you do best.
              <br />
              <span>We’ll take the call.</span>
            </h2>
          </Reveal>
          <div className={styles.industryList}>
            {industries.map((industry) => (
              <Link key={industry.number} href={industry.href}>
                <span className={styles.smallDetail}>{industry.number}</span>
                <h3>{industry.name}</h3>
                <p>{industry.detail}</p>
                <ArrowUpRight size={22} />
              </Link>
            ))}
          </div>
          <p className={styles.demoNote}>
            Dedicated guides for dental, home services, and restaurants are live
            today. Every other trade gets a concierge setup built around how you
            work.
          </p>
        </section>

        {/* ── Integrations ─────────────────────────────────── */}
        <section
          id="integrations"
          className={styles.integrations}
          aria-labelledby="integrations-heading"
        >
          <div className={styles.contain}>
          <Reveal>
            <p className={styles.eyebrow}>WORKS WITH YOUR SYSTEMS.</p>
            <h2 id="integrations-heading">
              Plugs into the tools
              <br />
              <span>you already run.</span>
            </h2>
            <p className={styles.sectionSub}>
              Calendar, inbox, records, and your business number, connected during
              setup, so bookings and leads land where your team already works. We
              can adapt the connection to the tools your business already uses.
            </p>
          </Reveal>
          <div className={styles.integrationGrid}>
            {[
              {
                icon: CalendarDays,
                title: "Business calendar",
                body: "Bookings, reschedules, and reminders land in the calendar or scheduling system you choose. Examples include Google Calendar, Microsoft Outlook, Cal.com, and more.",
              },
              {
                icon: Mail,
                title: "Email",
                body: "Confirmations and follow-ups sent to you and your customers automatically.",
              },
              {
                icon: Database,
                title: "Records & CRM",
                body: "Every call is logged with name, number, and outcome. We can send that context to a spreadsheet, CRM, dispatch system, or another workflow, such as Google Sheets or HubSpot.",
              },
              {
                icon: Phone,
                title: "Your business number",
                body: "We answer on the number your customers already call. No new line to advertise.",
              },
              {
                icon: Globe,
                title: "Your website",
                body: "An embeddable voice button lets visitors talk to your front desk without leaving your site.",
              },
              {
                icon: Plug,
                title: "Custom business tools",
                body: "If your team runs on a tool we have not listed, we can scope a custom integration around it during setup.",
              },
            ].map((item, index) => (
              <Reveal key={item.title} delay={(index % 3) * 90}>
                <div className={styles.integrationCard}>
                  <span className={styles.integrationIcon}>
                    <item.icon size={21} />
                  </span>
                  <h3>{item.title}</h3>
                  <p>{item.body}</p>
                </div>
              </Reveal>
            ))}
          </div>
          <Link className={styles.secondaryBtn} href="/request-demo">
            Tell us what you run. We&apos;ll connect it <ArrowUpRight size={16} />
          </Link>
          </div>
        </section>

        {/* ── Setup ────────────────────────────────────────── */}
        <section
          id="how-it-works"
          className={styles.setup}
          aria-labelledby="setup-heading"
        >
          <Reveal>
            <div>
              <p className={styles.eyebrow}>YOUR BUSINESS. YOUR VOICE.</p>
              <h2 id="setup-heading">
                Feels like your team.
                <br />
                <span>Because you shape it.</span>
              </h2>
              <p>
                We build your front desk with you. You approve the experience
                before it answers your customers.
              </p>
              <Link className={styles.primary} href="/request-demo">
                Request a demo <ArrowUpRight size={16} />
              </Link>
            </div>
          </Reveal>
          <ol>
            {[
              {
                n: "01",
                title: "Tell us how you work.",
                body: "Your services, prices, hours, and the calls you want handled. Start with a 30-second brief.",
              },
              {
                n: "02",
                title: "We build it with you.",
                body: "Your number, calendar or scheduling system, and records destination connected. Test calls until it sounds like your front desk.",
              },
              {
                n: "03",
                title: "Approve it. Go live in 48 hours.",
                body: "You test it and approve. Then every call gets answered at night, on weekends, and during busy hours.",
              },
            ].map((step, index) => (
              <Reveal key={step.n} delay={index * 100}>
                <li>
                  <span>{step.n}</span>
                  <div>
                    <h3>{step.title}</h3>
                    <p>{step.body}</p>
                  </div>
                </li>
              </Reveal>
            ))}
          </ol>
        </section>

        {/* ── Closing ──────────────────────────────────────── */}
        <section
          id="pricing"
          className={styles.closing}
          aria-labelledby="closing-heading"
        >
          <Reveal>
            <p className={styles.eyebrow}>
              <span className={styles.statusDot} /> YOUR NEXT CHAPTER STARTS WITH
              HELLO.
            </p>
            <h2 id="closing-heading">
              Good evening.
              <br />
              Good morning.
              <br />
              <span>Good for business.</span>
            </h2>
            <p>
              Start with a concierge pilot, built around you.
              <br />
              Monthly plans from $49/month, including up to 250 call minutes.
            </p>
            <div className={styles.ctaRow}>
              <Link className={styles.primary} href="/request-demo">
                Request a demo <ArrowUpRight size={18} />
              </Link>
              <a className={styles.textLink} href={`mailto:${SITE_SALES_EMAIL}`}>
                Talk to sales <ArrowUpRight size={16} />
              </a>
            </div>
          </Reveal>
          <div className={styles.closingOrbit} aria-hidden="true" />
        </section>

        <section
          className={styles.beyondVoice}
          aria-labelledby="beyond-voice-heading"
        >
          <div className={styles.beyondVoiceInner}>
            <div>
              <p className={styles.eyebrow}>BEYOND VOICE AI</p>
              <h2 id="beyond-voice-heading">
                Need more than a front desk?
                <br />
                <span>We can build the workflow too.</span>
              </h2>
            </div>
            <div>
              <p className={styles.beyondVoiceCopy}>
                We also build custom AI solutions to automate the daily work
                around your business. Explore the broader practice when your
                needs go beyond phone calls.
              </p>
              <a
                className={styles.textLink}
                href={SITE_AI_SERVICES_URL}
                target="_blank"
                rel="noreferrer"
              >
                Explore custom AI solutions <ArrowUpRight size={16} />
              </a>
            </div>
          </div>
        </section>
      </main>

      <footer className={styles.footer}>
        <div className={styles.footerTop}>
          <Link className={styles.brand} href="/">
            {SITE_NAME}
            <span className={styles.statusDot} />
          </Link>
          <p>Always there for your business.</p>
          <a href={`mailto:${SITE_SALES_EMAIL}`}>
            Say hello <MoveUpRight size={15} />
          </a>
        </div>
        <div className={styles.footerBottom}>
          <span>
            © {new Date().getFullYear()} {SITE_NAME}
          </span>
          <span className={styles.footerAttribution}>
            Built by an AI solutions company:{" "}
            <a
              href={SITE_AI_SERVICES_URL}
              target="_blank"
              rel="noreferrer"
              aria-label="Visit Cognitive Entities LLC"
            >
              Cognitive Entities LLC <ArrowUpRight size={12} aria-hidden="true" />
            </a>
          </span>
          <div>
            <a href="#demos">Live demos</a>
            <a href="#pricing">Pricing</a>
            <Link href="/auth/signin">Sign in</Link>
            <button onClick={toggleTheme}>
              {theme === "night" ? <Sun size={13} /> : <Moon size={13} />}{" "}
              {theme === "night" ? "Try the day shift" : "Try the night shift"}
            </button>
          </div>
          <span>ALWAYS ON. ALWAYS YOURS.</span>
        </div>
      </footer>
    </div>
  );
}
