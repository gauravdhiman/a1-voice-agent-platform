import { useEffect, useRef, useState, type ReactNode } from "react";
import styles from "./platform-tour.module.css";
import {
  BookingFlowScene,
  ConfirmScene,
  ToolsPickScene,
} from "./scenes-connect";
import {
  CreateApproveScene,
  CreateTestScene,
  CreateWriteScene,
} from "./scenes-create";
import { BothScene, EmbedScene, NumberScene } from "./scenes-publish";
import {
  KeepScene,
  LogScene,
  PlaybackScene,
} from "./scenes-review";
import {
  SkillAttachScene,
  SkillFollowedScene,
  SkillWriteScene,
} from "./scenes-skills";

export interface TourHighlight {
  title: string;
  body: string;
  animationDurationMs: number;
  view: ReactNode;
}

export interface TourChapter {
  id: string;
  tab: string;
  number: string;
  title: string;
  lede: string;
  highlights: TourHighlight[];
}

/**
 * The five platform chapters in owner-first language. Demos use one
 * fictional business ("Maple Street Dental", 555-numbers) so nothing reads
 * as a real customer story; every app view is tagged as an illustration.
 */
export const chapters: TourChapter[] = [
  {
    id: "create",
    tab: "Create",
    number: "01",
    title: "Describe your business in plain words.",
    lede: "Give your AI phone assistant your hours, services, prices and call-handling rules in plain words. Test how it answers before it goes live.",
    highlights: [
      {
        title: "Write it like you'd say it",
        body: "Start with the details customers ask about most: your hours, services, prices, and what to do after hours. Write a short note in your own words; there are no menus to configure or scripts to learn.",
        animationDurationMs: 5200,
        view: <CreateWriteScene />,
      },
      {
        title: "Hear it back on a test call",
        body: "Call a private test line and hear your AI assistant answer using your business details. Adjust its wording and try common questions until you are comfortable with the conversation.",
        animationDurationMs: 6800,
        view: <CreateTestScene />,
      },
      {
        title: "Approve it, then go live in about 48 hours",
        body: "Review the setup, then approve it when you are ready. It stays off customer calls until you approve, and we help get it live in about 48 hours.",
        animationDurationMs: 5400,
        view: <CreateApproveScene />,
      },
    ],
  },
  {
    id: "answer-everywhere",
    tab: "Answer everywhere",
    number: "02",
    title: "One AI assistant, your number and website.",
    lede: "It answers your business number and lets website visitors talk through a voice button. No press-1 menus or waiting on hold. The same assistant handles both.",
    highlights: [
      {
        title: "Keep your business number",
        body: "Customers keep calling the number they already know. Your AI assistant answers directly, without press-1 menus or hold music, and follows the business details and instructions you set.",
        animationDurationMs: 6800,
        view: <NumberScene />,
      },
      {
        title: "Add the website voice button",
        body: "Visitors tap Talk to us and speak directly with the same AI assistant. It can answer a question or take an appointment request without making them search for your number or wait on hold.",
        animationDurationMs: 10500,
        view: <EmbedScene />,
      },
      {
        title: "Same AI assistant, every line",
        body: "Your business number and website use the same AI assistant, instructions and availability. It answers questions and books work consistently, then captures a callback request when a customer needs your team.",
        animationDurationMs: 6200,
        view: <BothScene />,
      },
    ],
  },
  {
    id: "connect-tools",
    tab: "Connect tools",
    number: "03",
    title: "Works with the tools you already use.",
    lede: "Bookings land in your calendar, confirmations go out by email, and every outcome is logged where your team already works.",
    highlights: [
      {
        title: "Pick your tools during setup",
        body: "Choose the calendar, inbox, or records tools your team already uses, such as Google Calendar, Outlook, Sheets, or HubSpot. We help connect the right accounts during setup.",
        animationDurationMs: 5400,
        view: <ToolsPickScene />,
      },
      {
        title: "Watch a booking land",
        body: "When a caller asks for an appointment, your AI assistant checks your calendar before offering a time. After the customer chooses, it adds the booking to your calendar to prevent overlaps.",
        animationDurationMs: 6000,
        view: <BookingFlowScene />,
      },
      {
        title: "Confirmations handle the rest",
        body: "After a booking, your AI assistant can send a confirmation and reminder through your connected tools. Customers get the details they need, and your team spends less time repeating them.",
        animationDurationMs: 6000,
        view: <ConfirmScene />,
      },
    ],
  },
  {
    id: "teach-skills",
    tab: "Set instructions",
    number: "04",
    title: "Teach it your way of working.",
    lede: "Set plain-language instructions for after-hours calls, prices, bookings and urgent requests. Your AI assistant follows the same guidance on every call.",
    highlights: [
      {
        title: "Write rules, not code",
        body: "Add a repeatable instruction in everyday language, such as what to collect after hours or when to flag an urgent request. No code or technical setup is needed.",
        animationDurationMs: 5400,
        view: <SkillWriteScene />,
      },
      {
        title: "Choose which assistant follows each rule",
        body: "Give the right AI assistant your call-handling instructions. When your process changes, update the rule once instead of repeating it for each assistant.",
        animationDurationMs: 5400,
        view: <SkillAttachScene />,
      },
      {
        title: "Followed on every call",
        body: "During each call, your AI assistant follows your instructions, asks the right questions, captures the details you need, and flags urgent work. Your process stays consistent on nights, weekends and busy days.",
        animationDurationMs: 6000,
        view: <SkillFollowedScene />,
      },
    ],
  },
  {
    id: "review-calls",
    tab: "Review calls",
    number: "05",
    title: "Review every call without listening to each one.",
    lede: "Calls and callback requests land in one log with their source and outcome. Review what your AI assistant handled, then spot-check recordings when needed.",
    highlights: [
      {
        title: "One log for every call",
        body: "Find calls and callback requests in one place with their time, source and outcome. Filter by phone or website and see what your AI assistant handled before your team follows up.",
        animationDurationMs: 5400,
        view: <LogScene />,
      },
      {
        title: "Play the moments that matter",
        body: "Open a call to play its recording and review the transcript. Spot-check a booking, answer, or callback request without listening through every call.",
        animationDurationMs: 7200,
        view: <PlaybackScene />,
      },
      {
        title: "Kept for 30 days",
        body: "Review calls and share a weekly summary with your team. Recordings and call details stay available for 30 days, so you can revisit a conversation while it is still fresh.",
        animationDurationMs: 5600,
        view: <KeepScene />,
      },
    ],
  },
];

const LOOP_PAUSE_MS = 3000;

interface LoopingPreviewProps {
  animationDurationMs: number;
  children: ReactNode;
}

/** Replays a preview while it is visible, with a short pause between runs. */
function LoopingPreview({ animationDurationMs, children }: LoopingPreviewProps) {
  const previewRef = useRef<HTMLDivElement | null>(null);
  const hasBeenVisibleRef = useRef(false);
  const [isInView, setIsInView] = useState(false);
  const [isGap, setIsGap] = useState(false);
  const [cycle, setCycle] = useState(0);
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    const updatePreference = () => setReducedMotion(mediaQuery.matches);
    updatePreference();
    mediaQuery.addEventListener("change", updatePreference);
    return () => mediaQuery.removeEventListener("change", updatePreference);
  }, []);

  useEffect(() => {
    const preview = previewRef.current;
    if (!preview) return;

    if (!("IntersectionObserver" in window)) {
      hasBeenVisibleRef.current = true;
      setIsInView(true);
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          hasBeenVisibleRef.current = true;
          setIsInView(true);
          return;
        }

        if (hasBeenVisibleRef.current) {
          hasBeenVisibleRef.current = false;
          setCycle((current) => current + 1);
          setIsGap(false);
        }
        setIsInView(false);
      },
      { threshold: 0.1 },
    );

    observer.observe(preview);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!isInView || reducedMotion) return;

    const finishAnimation = window.setTimeout(
      () => setIsGap(true),
      animationDurationMs,
    );
    return () => window.clearTimeout(finishAnimation);
  }, [animationDurationMs, cycle, isInView, reducedMotion]);

  useEffect(() => {
    if (!isInView || reducedMotion || !isGap) return;

    const restartAnimation = window.setTimeout(() => {
      setCycle((current) => current + 1);
      setIsGap(false);
    }, LOOP_PAUSE_MS);
    return () => window.clearTimeout(restartAnimation);
  }, [isGap, isInView, reducedMotion]);

  const isPlaying = isInView && !reducedMotion && !isGap;

  return (
    <div
      ref={previewRef}
      className={styles.viewBody}
      data-looping-preview="true"
      data-loop-cycle={cycle}
      data-playing={isPlaying}
      data-animation-duration-ms={animationDurationMs}
    >
      <div key={cycle}>{children}</div>
    </div>
  );
}

/** A chapter with all of its highlights and illustrative previews in view. */
function TourSection({ chapter }: { chapter: TourChapter }) {
  return (
    <section
      id={`tour-${chapter.id}`}
      aria-labelledby={`tour-${chapter.id}-heading`}
      className={styles.chapter}
    >
      <header className={styles.chapterHeader}>
        <div className={styles.chapterHeading}>
          <p className={styles.stageKicker}>
            {chapter.number} / {chapter.tab.toUpperCase()}
          </p>
          <h3 id={`tour-${chapter.id}-heading`}>{chapter.title}</h3>
        </div>
        <p className={styles.chapterLede}>{chapter.lede}</p>
      </header>

      <ol className={styles.highlightList} aria-label={`${chapter.tab} highlights`}>
        {chapter.highlights.map((highlight, index) => (
          <li
            key={highlight.title}
            className={styles.highlightItem}
            data-reverse={index % 2 === 1}
          >
            <div className={styles.highlightCopy}>
              <p className={styles.highlightNumber}>
                {String(index + 1).padStart(2, "0")}
              </p>
              <h4>{highlight.title}</h4>
              <p>{highlight.body}</p>
            </div>

            <div className={styles.stageView}>
              <div className={styles.viewFrame}>
                <div className={styles.viewChrome} aria-hidden="true">
                  <span>
                    <i />
                    <i />
                    <i />
                  </span>
                  <em>Illustrative preview</em>
                </div>
                <LoopingPreview
                  animationDurationMs={highlight.animationDurationMs}
                >
                  {highlight.view}
                </LoopingPreview>
              </div>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}

/** All chapters as sections with static highlight descriptions and previews. */
export function TourSections() {
  return (
    <div className={styles.tour}>
      <nav aria-label="Platform chapters" className={styles.chapterNav}>
        {chapters.map((entry) => (
          <a key={entry.id} href={`#tour-${entry.id}`}>
            <span className={styles.tabNumber}>{entry.number}</span>
            {entry.tab}
          </a>
        ))}
      </nav>
      {chapters.map((entry) => (
        <TourSection key={entry.id} chapter={entry} />
      ))}
    </div>
  );
}
