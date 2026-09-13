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
  Menu,
  X,
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
import { SITE_NAME, SITE_SALES_EMAIL } from "@/lib/site-config";
import { ParticleField } from "./particle-field";
import styles from "./home-page.module.css";

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
    href: "/dental",
    number: "01",
  },
  {
    name: "HVAC, plumbing & roofing",
    detail: "Every service call captured while your crew is out on site.",
    href: "/hvac",
    number: "02",
  },
  {
    name: "Restaurants & cafés",
    detail:
      "Reservations, party bookings and order questions, handled mid-rush.",
    href: "/request-demo",
    number: "03",
  },
  {
    name: "Salons, spas & clinics",
    detail: "Chairs filled with bookings and reminders that cut no-shows.",
    href: "/request-demo",
    number: "04",
  },
  {
    name: "Real estate & local services",
    detail: "Every enquiry answered, viewings and quotes booked on the spot.",
    href: "/request-demo",
    number: "05",
  },
  {
    name: "Your kind of business",
    detail: "Tell us how you work. We build the front desk around it.",
    href: "/request-demo",
    number: "06",
  },
];

/** Homepage-only visual concept. Keeps the public demo and concierge funnel intact;
 * theme preference is scoped to this page so other platform surfaces are unaffected. */
export function HomePage() {
  const [theme, setTheme] = useState<"day" | "night">("night");
  const [paused, setPaused] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [chapter, setChapter] = useState(0);
  const root = useRef<HTMLDivElement>(null);

  useEffect(() => {
    try {
      const saved = localStorage.getItem("247ai-home-theme");
      if (saved === "day" || saved === "night") setTheme(saved);
    } catch {
      /* Storage may be unavailable; the switch still works in memory. */
    }
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

  const toggleTheme = () => {
    const next = theme === "night" ? "day" : "night";
    setTheme(next);
    try {
      localStorage.setItem("247ai-home-theme", next);
    } catch {
      /* Optional persistence. */
    }
  };
  const closeMenu = () => setMenuOpen(false);

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
      <header className={styles.header}>
        <Link
          href="/"
          className={styles.brand}
          aria-label={`${SITE_NAME} home`}
        >
          <span className={styles.brandMark} aria-hidden="true">
            <i />
            <i />
            <i />
            <i />
            <i />
            <i />
            <i />
            <i />
            <i />
          </span>
          <span>{SITE_NAME}</span>
        </Link>
        <nav className={styles.desktopNav} aria-label="Main navigation">
          <a href="#features">Use cases</a>
          <a href="#demos">Live demos</a>
          <a href="#industries">For your business</a>
          <a href="#integrations">Integrations</a>
          <a href="#pricing">Pricing</a>
        </nav>
        <div className={styles.headerActions}>
          <button
            className={styles.themeSwitch}
            onClick={toggleTheme}
            aria-label={`Switch to ${theme === "night" ? "day" : "night"} mode`}
          >
            <Sun size={14} />
            <span className={styles.switchTrack}>
              <span />
            </span>
            <Moon size={13} />
          </button>
          <Link className={styles.signIn} href="/auth/signin">
            Sign in <ArrowUpRight size={13} />
          </Link>
          <Link className={styles.headerCta} href="/request-demo">
            Let’s talk <ArrowUpRight size={14} />
          </Link>
          <button
            className={styles.menuToggle}
            aria-label={menuOpen ? "Close navigation" : "Open navigation"}
            aria-expanded={menuOpen}
            aria-controls="home-mobile-nav"
            onClick={() => setMenuOpen(!menuOpen)}
          >
            {menuOpen ? <X /> : <Menu />}
          </button>
        </div>
        {menuOpen && (
          <nav
            id="home-mobile-nav"
            className={styles.mobileNav}
            aria-label="Mobile navigation"
            onKeyDown={(event) => {
              if (event.key === "Escape") {
                closeMenu();
                root.current
                  ?.querySelector<HTMLButtonElement>(
                    `[aria-controls="home-mobile-nav"]`,
                  )
                  ?.focus();
              }
            }}
          >
            <a href="#features" onClick={closeMenu}>
              Use cases
            </a>
            <a href="#industries" onClick={closeMenu}>
              For your business
            </a>
            <a href="#integrations" onClick={closeMenu}>
              Integrations
            </a>
            <a href="#demos" onClick={closeMenu}>
              Live demos
            </a>
            <a href="#pricing" onClick={closeMenu}>
              Pricing
            </a>
            <Link href="/auth/signin" onClick={closeMenu}>
              Sign in
            </Link>
          </nav>
        )}
      </header>

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
                Your 24x7 AI front desk for local businesses. Every call
                answered in seconds, even nights, weekends, and mid-rush.
                <br className={styles.desktopBreak} /> You stay on the job; it
                handles the phones.
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
              Hear exactly how your after-hours caller would be treated.
            </p>
          </div>
          <div className={styles.demoGrid}>
            <Link
              href="/demo/pleasant-pediatric-appointments"
              className={styles.demoCard}
            >
              <div className={styles.demoArt} aria-hidden="true">
                <div className={styles.dotReceiver} />
                <span>ALEX / APPOINTMENTS</span>
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
                  Try booking a dental visit with Alex. Real availability,
                  confirmation, and a calendar event your front desk didn&apos;t
                  have to touch.
                </p>
                <span className={styles.demoLink}>
                  <span className={styles.playCircle}>
                    <Play size={11} fill="currentColor" />
                  </span>{" "}
                  Talk to Alex <ArrowUpRight size={17} />
                </span>
              </div>
            </Link>
            <Link
              href="/demo/copper-ridge-service-request"
              className={`${styles.demoCard} ${styles.secondDemo}`}
            >
              <div className={styles.demoArt} aria-hidden="true">
                <div className={styles.dotWave} />
                <span>JORDAN / SERVICE REQUESTS</span>
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
                  Ask Jordan for HVAC service. Symptoms, address, and time
                  window captured into a clean request. Emergencies flagged,
                  routine booked.
                </p>
                <span className={styles.demoLink}>
                  <span className={styles.playCircle}>
                    <Play size={11} fill="currentColor" />
                  </span>{" "}
                  Talk to Jordan <ArrowUpRight size={17} />
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
            Dedicated guides for dental and home services are live today. Every
            other trade gets a concierge setup built around how you work.
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
            setup, so bookings and leads land where your team already works. Run
            something else? We connect that too.
          </p>
          <div className={styles.integrationGrid}>
            <div className={styles.integrationCard}>
              <span className={styles.integrationIcon}>
                <CalendarDays size={22} />
              </span>
              <h3>Business calendar</h3>
              <p>
                Bookings, reschedules, and reminders land on your calendar.
                Works with Google Calendar, Cal.com, and more.
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
                Every call logged with name, number, and outcome. Sheets works
                out of the box, and we connect your CRM on setup.
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
              <h3>The rest of your stack</h3>
              <p>
                Booking software, trade tools, or something custom. Tell us what
                you run and we connect it during setup.
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
                  a 30-second brief.
                </p>
              </div>
            </li>
            <li>
              <span>02</span>
              <div>
                <h3>We build it with you.</h3>
                <p>
                  Number, calendar, and records connected. Test calls until it
                  sounds like your front desk.
                </p>
              </div>
            </li>
            <li>
              <span>03</span>
              <div>
                <h3>Approve it. Go live in 48 hours.</h3>
                <p>
                  You sign off every word. Then every call gets answered.
                  nights, weekends, and busy hours.
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
