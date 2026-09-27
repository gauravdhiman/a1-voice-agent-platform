"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  ArrowDown,
  ArrowUpRight,
  ArrowRight,
  Sun,
  Moon,
  Pause,
  Play,
  Phone,
  CalendarCheck,
  CalendarDays,
  Check,
  AudioLines,
  Database,
  Globe,
  Mail,
  MoveUpRight,
  Plug,
} from "lucide-react";
import {
  SITE_AI_SERVICES_URL,
  SITE_NAME,
  SITE_SALES_EMAIL,
} from "@/lib/site-config";
import { usePublicTheme } from "@/components/public-theme/public-theme-context";
import { PublicHeader } from "@/components/public-theme/public-header";
import { ParticleField } from "./particle-field";
import styles from "./home-page-legacy.module.css";

const chapters = [
  "Every call answered",
  "Questions resolved",
  "Calendar filled",
  "Leads captured",
];
/** What the dot field is forming right now. Naming each formation out loud
 * keeps the animation legible: visitors read the caption, then see it. */
const formations = [
  "Ringing service bell · every call answered",
  "Live conversation · questions resolved on the call",
  "Booking calendar · synced to your business calendar",
  "Captured lead · your team gets the full context",
];
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

/** Homepage visual concept (legacy fallback, preserved at /home-classic). Uses the single site-wide theme (shared with
 * the dashboard), so one toggle is honored everywhere. Dashboard styling
 * is unaffected. */
export function HomePageLegacy() {
  const { theme, toggleTheme } = usePublicTheme();
  const [paused, setPaused] = useState(false);
  const [chapter, setChapter] = useState(0);
  const root = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const sections =
      root.current?.querySelectorAll<HTMLElement>("[data-chapter]");
    if (!sections || typeof IntersectionObserver === "undefined") return;
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting)
            setChapter(Number((entry.target as HTMLElement).dataset.chapter));
        }
      },
      { rootMargin: "-35% 0px -35% 0px", threshold: 0 },
    );
    sections.forEach((section) => observer.observe(section));
    return () => observer.disconnect();
  }, []);

  return (
    <div
      ref={root}
      className={styles.home}
      data-theme={theme}
      data-paused={paused}
    >
      <a className={styles.skip} href="#main-content">
        Skip to content
      </a>
      <PublicHeader />

      <main id="main-content">
        <div className={styles.journey} data-journey>
          <div className={styles.field}>
            <div className={styles.fieldGlow} />
            <ParticleField theme={theme} paused={paused} />
            <div className={styles.fieldCoordinates} aria-hidden="true">
              <span>24 / 7</span>
              <span>EVERY CONVERSATION COUNTS</span>
            </div>
          </div>
          <section
            className={`${styles.scene} ${styles.hero}`}
            data-chapter="0"
            aria-labelledby="hero-heading"
          >
            <div className={styles.heroContent}>
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
                A call is a customer asking for a next step. Your 24x7 AI front
                desk answers in seconds, handles routine questions, books the
                work, and captures the rest, even nights, weekends, and
                mid-rush.
              </p>
              <div className={styles.ctaRow}>
                <Link className={styles.primary} href="/request-demo">
                  Meet your AI front desk <ArrowUpRight size={18} />
                </Link>
                <a className={styles.textLink} href="#demos">
                  <span className={styles.playCircle}>
                    <Play size={11} fill="currentColor" />
                  </span>{" "}
                  Hear it handle a real call
                </a>
              </div>
              <p className={styles.heroNote}>
                Concierge setup with you · You approve every word · No coding
                required, plans from $79/mo.
              </p>
            </div>
            <div className={styles.fieldLabel} aria-hidden="true">
              <span className={styles.statusDot} /> {formations[chapter]}
            </div>
            <div className={styles.heroBottom}>
              <a href="#features">
                <ArrowDown size={15} /> SCROLL TO SEE WHAT’S POSSIBLE
              </a>
              <span>HUMAN CONNECTION. MEET ALWAYS ON.</span>
            </div>
          </section>

          <section
            id="features"
            className={styles.scene}
            data-chapter="1"
            aria-labelledby="answer-heading"
          >
            <div className={styles.sceneContent}>
              <p className={styles.eyebrow}>01 / ANSWERS ON THE SPOT</p>
              <h2 id="answer-heading">
                Routine questions?
                <br />
                <span>Resolved on the call.</span>
              </h2>
              <p>
                Hours, prices, services, order updates, directions, answered
                instantly from your business info. Routine callers get what they
                need without pulling you or your staff off the job.
              </p>
              <div className={styles.example}>
                <div className={styles.exampleHeading}>
                  <Phone size={15} /> AN EVERYDAY MOMENT{" "}
                  <span>ILLUSTRATIVE CONVERSATION</span>
                </div>
                <p>&ldquo;What are your prices for a deep cleaning?&rdquo;</p>
                <p className={styles.agentReply}>
                  &ldquo;Deep cleanings start at $149. Want me to hold a slot
                  for you?&rdquo;
                </p>
                <div className={styles.exampleFoot}>
                  <AudioLines size={17} />
                  <span>Zero interruptions to your day.</span>
                </div>
              </div>
              <span className={styles.smallDetail}>
                HOURS · PRICES · SERVICES · ORDER UPDATES, TRAINED IN.
              </span>
            </div>
          </section>
          <section
            id="bookings"
            className={styles.scene}
            data-chapter="2"
            aria-labelledby="booking-heading"
          >
            <div className={styles.sceneContent}>
              <p className={styles.eyebrow}>02 / BOOKINGS THAT GROW REVENUE</p>
              <h2 id="booking-heading">
                &ldquo;Can I book?&rdquo;
                <br />
                <span>Becomes &ldquo;You&apos;re booked.&rdquo;</span>
              </h2>
              <p>
                Checks your real availability, books and reschedules
                appointments, and writes everything to your business calendar,
                with confirmations that cut no-shows. Every open slot turns into
                paying work.
              </p>
              <div className={styles.bookingCard}>
                <span className={styles.bookingIcon}>
                  <CalendarCheck size={23} />
                </span>
                <div>
                  <span className={styles.smallDetail}>EXAMPLE OUTCOME</span>
                  <h3>Thu 2:00 PM · Maria G., booked</h3>
                  <p>Time confirmed · On your calendar · Reminder set</p>
                </div>
                <Check size={18} />
              </div>
              <span className={styles.smallDetail}>
                YOUR BUSINESS CALENDAR · NO DOUBLE-BOOKING · FEWER NO-SHOWS
              </span>
            </div>
          </section>
          <section
            id="connections"
            className={styles.scene}
            data-chapter="3"
            aria-labelledby="connection-heading"
          >
            <div className={styles.sceneContent}>
              <p className={styles.eyebrow}>03 / LEADS CAPTURED AFTER HOURS</p>
              <h2 id="connection-heading">
                Close up shop.
                <br />
                <span>Keep winning work.</span>
              </h2>
              <p>
                Nights, weekends, holidays. Every caller is captured with name,
                number, and reason, and you&apos;re notified in seconds. Urgent
                calls get flagged; routine ones wait neatly for the morning with
                full context.
              </p>
              <ul className={styles.outcomeList}>
                <li>
                  <Check size={16} /> Name, number &amp; reason captured on
                  every call
                </li>
                <li>
                  <Check size={16} /> Instant notification, straight to you in
                  seconds
                </li>
                <li>
                  <Check size={16} /> Urgent flagged, routine ready for the
                  morning. Nothing lost to voicemail
                </li>
              </ul>
              <a className={styles.textLink} href="#how-it-works">
                See the 48-hour setup <ArrowRight size={17} />
              </a>
            </div>
          </section>
          <div className={styles.journeyControls}>
            <span>
              <b>0{chapter + 1}</b> / 04 <i /> {chapters[chapter]}
            </span>
            <button
              onClick={() => setPaused(!paused)}
              aria-label={
                paused ? "Resume ambient animation" : "Pause ambient animation"
              }
              aria-pressed={paused}
            >
              {paused ? <Play size={12} /> : <Pause size={12} />}
              <span>{paused ? "Resume motion" : "Pause motion"}</span>
            </button>
          </div>
        </div>

        <section
          id="proof"
          className={styles.proof}
          aria-labelledby="proof-heading"
        >
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
              CallRail SMB benchmark{" "}
              <ArrowUpRight size={12} aria-hidden="true" />
            </a>{" "}
            ·{" "}
            <a
              href="https://www.invoca.com/reports/the-invoca-lead-conversion-benchmarks-report-2026"
              target="_blank"
              rel="noreferrer"
            >
              Invoca 2026 benchmark{" "}
              <ArrowUpRight size={12} aria-hidden="true" />
            </a>
          </p>
        </section>

        <section
          id="demos"
          className={styles.demos}
          aria-labelledby="demo-heading"
        >
          <div className={styles.sectionTop}>
            <p className={styles.eyebrow}>LESS IMAGINING. MORE EXPERIENCING.</p>
            <span className={styles.smallDetail}>
              REAL AGENTS. TRY A CONVERSATION.
            </span>
          </div>
          <div className={styles.sectionHeading}>
            <h2 id="demo-heading">
              Don’t take our word.
              <br />
              <span>Have a word.</span>
            </h2>
            <p>
              Talk to a demo agent right now. Book a visit. Request a repair.
              Place an order. Hear exactly how your after-hours caller would be
              treated.
            </p>
          </div>
          <div className={styles.demoGrid}>
            <Link
              href="/demo/pleasant-pediatric-appointments"
              className={styles.demoCard}
            >
              <div className={styles.demoArt} aria-hidden="true">
                <div className={styles.dotReceiver} />
                <span>APPOINTMENT BOOKINGS</span>
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
                  Try the appointment demo <ArrowUpRight size={17} />
                </span>
              </div>
            </Link>
            <Link
              href="/demo/copper-ridge-service-request"
              className={`${styles.demoCard} ${styles.secondDemo}`}
            >
              <div className={styles.demoArt} aria-hidden="true">
                <div className={styles.dotWave} />
                <span>SERVICE REQUESTS</span>
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
                  Try the service demo <ArrowUpRight size={17} />
                </span>
              </div>
            </Link>
            <Link
              href="/demo/verdi-table-restaurant"
              className={styles.demoCard}
            >
              <div className={styles.demoArt} aria-hidden="true">
                <div className={styles.dotReceiver} />
                <span>RESTAURANT ORDERS</span>
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
                  Try the restaurant demo <ArrowUpRight size={17} />
                </span>
              </div>
            </Link>
          </div>
          <p className={styles.demoNote}>
            Interactive demos use example businesses. Your agent is configured
            with your own services and instructions.
          </p>
        </section>

        <section
          id="industries"
          className={styles.industries}
          aria-labelledby="industries-heading"
        >
          <p className={styles.eyebrow}>
            SMALL TEAMS. BIG AMBITIONS. EVERY BUSINESS IN BETWEEN.
          </p>
          <h2 id="industries-heading">
            You do what you do best.
            <br />
            <span>We’ll take the call.</span>
          </h2>
          <div className={styles.industryList}>
            {industries.map((industry) => (
              <Link key={industry.number} href={industry.href}>
                <span className={styles.smallDetail}>{industry.number}</span>
                <h3>{industry.name}</h3>
                <p>{industry.detail}</p>
                <ArrowUpRight size={23} />
              </Link>
            ))}
          </div>
          <p className={styles.demoNote}>
            Dedicated guides for dental, home services, and restaurants are live
            today. Every other trade gets a concierge setup built around how you
            work.
          </p>
        </section>

        <section
          id="integrations"
          className={styles.integrations}
          aria-labelledby="integrations-heading"
        >
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
          <div className={styles.integrationGrid}>
            <div className={styles.integrationCard}>
              <span className={styles.integrationIcon}>
                <CalendarDays size={22} />
              </span>
              <h3>Business calendar</h3>
              <p>
                Bookings, reschedules, and reminders land in the calendar or
                scheduling system you choose. Examples include Google Calendar,
                Microsoft Outlook, Cal.com, and more.
              </p>
            </div>
            <div className={styles.integrationCard}>
              <span className={styles.integrationIcon}>
                <Mail size={22} />
              </span>
              <h3>Email</h3>
              <p>
                Confirmations and follow-ups sent to you and your customers
                automatically.
              </p>
            </div>
            <div className={styles.integrationCard}>
              <span className={styles.integrationIcon}>
                <Database size={22} />
              </span>
              <h3>Records &amp; CRM</h3>
              <p>
                Every call is logged with name, number, and outcome. We can send
                that context to a spreadsheet, CRM, dispatch system, or another
                workflow, such as Google Sheets or HubSpot.
              </p>
            </div>
            <div className={styles.integrationCard}>
              <span className={styles.integrationIcon}>
                <Phone size={22} />
              </span>
              <h3>Your business number</h3>
              <p>
                We answer on the number your customers already call. No new line
                to advertise.
              </p>
            </div>
            <div className={styles.integrationCard}>
              <span className={styles.integrationIcon}>
                <Globe size={22} />
              </span>
              <h3>Your website</h3>
              <p>
                An embeddable voice button lets visitors talk to your front desk
                without leaving your site.
              </p>
            </div>
            <div className={styles.integrationCard}>
              <span className={styles.integrationIcon}>
                <Plug size={22} />
              </span>
              <h3>Custom business tools</h3>
              <p>
                If your team runs on a tool we have not listed, we can scope a
                custom integration around it during setup.
              </p>
            </div>
          </div>
          <Link className={styles.textLink} href="/request-demo">
            Tell us what you run. We&apos;ll connect it{" "}
            <ArrowUpRight size={17} />
          </Link>
        </section>

        <section
          id="how-it-works"
          className={styles.setup}
          aria-labelledby="setup-heading"
        >
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
            <Link className={styles.textLink} href="/request-demo">
              Request a demo <ArrowUpRight size={17} />
            </Link>
          </div>
          <ol>
            <li>
              <span>01</span>
              <div>
                <h3>Tell us how you work.</h3>
                <p>
                  Your services, prices, hours, and the calls you want handled.
                  Start with a 30-second brief.
                </p>
              </div>
            </li>
            <li>
              <span>02</span>
              <div>
                <h3>We build it with you.</h3>
                <p>
                  Your number, calendar or scheduling system, and records
                  destination connected. Test calls until it sounds like your
                  front desk.
                </p>
              </div>
            </li>
            <li>
              <span>03</span>
              <div>
                <h3>Approve it. Go live in 48 hours.</h3>
                <p>
                  You sign off every word. Then every call gets answered at
                  night, on weekends, and during busy hours.
                </p>
              </div>
            </li>
          </ol>
        </section>

        <section
          id="pricing"
          className={styles.closing}
          aria-labelledby="closing-heading"
        >
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
            Monthly plans from $79 as you grow.
          </p>
          <div className={styles.ctaRow}>
            <Link className={styles.primary} href="/request-demo">
              Request a demo <ArrowUpRight size={18} />
            </Link>
            <a className={styles.textLink} href={`mailto:${SITE_SALES_EMAIL}`}>
              Talk to sales <ArrowUpRight size={17} />
            </a>
          </div>
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
                Explore custom AI solutions <ArrowUpRight size={17} />
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
            Say hello <MoveUpRight size={16} />
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
              Cognitive Entities LLC{" "}
              <ArrowUpRight size={12} aria-hidden="true" />
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
