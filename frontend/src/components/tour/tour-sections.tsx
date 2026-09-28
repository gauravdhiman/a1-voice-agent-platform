"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { Pause, Play, RotateCcw } from "lucide-react";
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

export interface TourStep {
  title: string;
  body: string;
}

export interface TourChapter {
  id: string;
  tab: string;
  number: string;
  title: string;
  lede: string;
  steps: TourStep[];
  /** Dwell per step (ms): each scene's animation timeline plus a beat of
   * hold, so a transition never cuts a scene off mid-story. */
  durations: [number, number, number];
  view: (step: number) => ReactNode;
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
    lede: "No setup wizards, no code. Tell the agent your hours, services, and prices the way you'd tell a new hire — then hear it back on a test call.",
    steps: [
      {
        title: "Write it like you'd say it",
        body: "Business name, hours, services, prices. Plain sentences are the whole configuration.",
      },
      {
        title: "Hear it back on a test call",
        body: "Place a test call, adjust the wording until it sounds like your front desk.",
      },
      {
        title: "Approve it — live in about 48 hours",
        body: "You test and approve before it answers a single real customer.",
      },
    ],
    durations: [5200, 6800, 5400],
    view: (step) =>
      [<CreateWriteScene key={0} />, <CreateTestScene key={1} />, <CreateApproveScene key={2} />][step],
  },
  {
    id: "answer-everywhere",
    tab: "Answer everywhere",
    number: "02",
    title: "One agent, every place customers call.",
    lede: "Put the same front desk on the phone number customers already dial and on your website as a voice button. Both lines ring the same agent.",
    steps: [
      {
        title: "Keep your business number",
        body: "We answer on the number your customers already call. Nothing new to advertise.",
      },
      {
        title: "Add the website voice button",
        body: "Visitors talk to your front desk without leaving your site.",
      },
      {
        title: "Every line, same agent",
        body: "Website and phone calls land with the same instructions, at the same time.",
      },
    ],
    durations: [6200, 7600, 6200],
    view: (step) =>
      [<NumberScene key={0} />, <EmbedScene key={1} />, <BothScene key={2} />][step],
  },
  {
    id: "connect-tools",
    tab: "Connect tools",
    number: "03",
    title: "Works with the tools you already use.",
    lede: "Bookings land in your calendar, confirmations go out by email, and every outcome is logged where your team already works.",
    steps: [
      {
        title: "Pick your tools during setup",
        body: "Calendar, inbox, records or CRM — for example Google Calendar, Outlook, Sheets, or HubSpot.",
      },
      {
        title: "Watch a booking land",
        body: "The agent checks real availability and writes the appointment in — no double-booking.",
      },
      {
        title: "Confirmations handle the rest",
        body: "Automatic confirmations and reminders cut no-shows without lifting a finger.",
      },
    ],
    durations: [5400, 6000, 6000],
    view: (step) =>
      [<ToolsPickScene key={0} />, <BookingFlowScene key={1} />, <ConfirmScene key={2} />][step],
  },
  {
    id: "teach-skills",
    tab: "Teach skills",
    number: "04",
    title: "Teach it your way of working.",
    lede: "Skills are plain-language rules — how to handle after-hours calls, what to quote, when to flag urgent. Attach them to any agent in one click.",
    steps: [
      {
        title: "Write rules, not code",
        body: "“After 6 PM, capture name, number, reason.” If you can say it, the agent can follow it.",
      },
      {
        title: "Attach skills to agents",
        body: "One click assigns a skill. Update the wording once, every attached agent follows.",
      },
      {
        title: "Followed on every call",
        body: "The agent applies its skills consistently — nights, weekends, mid-rush.",
      },
    ],
    durations: [5400, 5400, 6000],
    view: (step) =>
      [<SkillWriteScene key={0} />, <SkillAttachScene key={1} />, <SkillFollowedScene key={2} />][step],
  },
  {
    id: "review-calls",
    tab: "Review calls",
    number: "05",
    title: "Hear every call — without hearing all of them.",
    lede: "Every call lands in one log with its source, outcome, and recording. Filter, spot-check, and stay in control.",
    steps: [
      {
        title: "One log for every call",
        body: "When it came in, through what source, how long it ran, what happened.",
      },
      {
        title: "Play the moments that matter",
        body: "Recordings with instant playback for the calls you want to verify.",
      },
      {
        title: "Kept for 30 days",
        body: "Recordings and full call details stay available for a month.",
      },
    ],
    durations: [5400, 7200, 5600],
    view: (step) =>
      [<LogScene key={0} />, <PlaybackScene key={1} />, <KeepScene key={2} />][step],
  },
];

/**
 * One chapter block: copy on one side, live app-view preview on the other.
 * Steps auto-advance only while the block is meaningfully on screen, and can
 * be replayed, paused, hover-held, or stepped manually. Reduced-motion
 * visitors get a static first step with clickable dots instead.
 */
function TourSection({
  chapter,
  flip,
  reduced,
}: {
  chapter: TourChapter;
  flip: boolean;
  reduced: boolean;
}) {
  const [step, setStep] = useState(0);
  const [manualHold, setManualHold] = useState(false);
  const [hoverHold, setHoverHold] = useState(false);
  const [inView, setInView] = useState(false);
  const ref = useRef<HTMLElement>(null);

  const held = manualHold || hoverHold || reduced;

  useEffect(() => {
    const node = ref.current;
    if (!node || typeof IntersectionObserver === "undefined") {
      setInView(true);
      return;
    }
    const observer = new IntersectionObserver(
      ([entry]) => setInView(entry.isIntersecting),
      { threshold: 0.25 },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (held || !inView) return;
    const timer = window.setTimeout(() => {
      setStep((current) => (current + 1) % chapter.steps.length);
    }, chapter.durations[step] ?? 4200);
    return () => window.clearTimeout(timer);
  }, [held, inView, chapter, step]);

  const replay = () => {
    setStep(0);
    setManualHold(false);
  };

  return (
    <section
      ref={ref}
      id={`tour-${chapter.id}`}
      aria-labelledby={`tour-${chapter.id}-heading`}
      className={styles.chapter}
      data-flip={flip}
    >
      <div
        className={styles.chapterCopy}
        onMouseEnter={() => !manualHold && setHoverHold(true)}
        onMouseLeave={() => setHoverHold(false)}
        onFocus={() => !manualHold && setHoverHold(true)}
        onBlur={() => setHoverHold(false)}
      >
        <p className={styles.stageKicker}>
          {chapter.number} / {chapter.tab.toUpperCase()}
        </p>
        <h3 id={`tour-${chapter.id}-heading`}>{chapter.title}</h3>
        <p className={styles.stageLede}>{chapter.lede}</p>
        <ol className={styles.stepList} aria-live="polite">
          {chapter.steps.map((entry, index) => (
            <li
              key={entry.title}
              data-active={index === step}
              data-done={index < step}
            >
              <button
                type="button"
                onClick={() => setStep(index)}
                aria-label={`Step ${index + 1}: ${entry.title}`}
                aria-current={index === step ? "step" : undefined}
              >
                <span className={styles.stepDot} aria-hidden="true" />
                <span>
                  <strong>{entry.title}</strong>
                  {index === step && <em>{entry.body}</em>}
                </span>
              </button>
            </li>
          ))}
        </ol>
        <div className={styles.stageControls}>
          <button
            type="button"
            className={styles.stageToggle}
            onClick={() => setManualHold((hold) => !hold)}
            aria-label={held && !reduced ? "Play the run-through" : "Pause the run-through"}
            aria-pressed={held}
          >
            {held && !reduced ? (
              <Play size={12} fill="currentColor" aria-hidden="true" />
            ) : (
              <Pause size={12} aria-hidden="true" />
            )}
            <span>{held && !reduced ? "Play" : "Pause"}</span>
          </button>
          <button
            type="button"
            className={styles.stageToggle}
            onClick={replay}
            aria-label={`Replay ${chapter.tab} from the start`}
          >
            <RotateCcw size={12} aria-hidden="true" />
            <span>Replay</span>
          </button>
        </div>
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
          <div key={step} className={styles.viewBody}>
            {chapter.view(step)}
          </div>
        </div>
      </div>
    </section>
  );
}

/**
 * All five chapters as alternating full-width sections: copy left/view
 * right, then mirrored, so every feature is visible on scroll with no
 * tab interaction required.
 */
export function TourSections() {
  const [reduced, setReduced] = useState(false);

  useEffect(() => {
    if (typeof window.matchMedia !== "function") return;
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(query.matches);
    const onChange = (event: MediaQueryListEvent) => setReduced(event.matches);
    query.addEventListener("change", onChange);
    return () => query.removeEventListener("change", onChange);
  }, []);

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
      {chapters.map((entry, index) => (
        <TourSection
          key={entry.id}
          chapter={entry}
          flip={index % 2 === 1}
          reduced={reduced}
        />
      ))}
    </div>
  );
}
