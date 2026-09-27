"use client";

import { useEffect, useState } from "react";
import {
  AudioLines,
  CalendarCheck,
  ClipboardCheck,
  MessageCircleQuestion,
  Pause,
  PhoneCall,
  PhoneIncoming,
  Play,
} from "lucide-react";
import styles from "./concurrency-diagram.module.css";

interface ConcurrencyDiagramProps {
  paused: boolean;
}

const lanes = [
  {
    initials: "MG",
    name: "Maria G.",
    intent: "“Deep cleaning price?”",
    icon: MessageCircleQuestion,
    outcome: "Answered in 4s",
    tone: "tone-a" as const,
  },
  {
    initials: "SR",
    name: "Sam R.",
    intent: "“AC out tonight?”",
    icon: ClipboardCheck,
    outcome: "Urgent job captured",
    tone: "tone-b" as const,
  },
  {
    initials: "PK",
    name: "Priya K.",
    intent: "“Table for 4?”",
    icon: CalendarCheck,
    outcome: "Thu 7 PM · booked",
    tone: "tone-c" as const,
  },
];

const transcripts = [
  {
    caller: "Maria: “What are your prices for a deep cleaning?”",
    agent: "24x7 AI: “Deep cleanings start at $149. Want me to hold a slot for you?”",
  },
  {
    caller: "Sam: “Our AC stopped. Can someone come tonight?”",
    agent: "24x7 AI: “I’ve flagged this as urgent and captured your address and window.”",
  },
  {
    caller: "Priya: “Table for four tomorrow at 7?”",
    agent: "24x7 AI: “You’re booked for 7. Confirmation and reminder are set.”",
  },
];

/**
 * Calm concurrency story: three callers, each lane flowing into its outcome
 * through one shared 24x7 AI front desk. Each lane is self-contained so it
 * reads the same way stacked on mobile as it does side-by-side on desktop.
 * Beams are pure CSS (no layout measuring), transform-only. The transcript
 * ticker pauses on hover/focus, via its own button, the page pause control,
 * or reduced motion.
 */
export function ConcurrencyDiagram({ paused }: ConcurrencyDiagramProps) {
  const [active, setActive] = useState(0);
  const [manualHold, setManualHold] = useState(false);
  const [hoverHold, setHoverHold] = useState(false);

  // Rotation hold (button + hover/focus + global pause) freezes only the
  // transcript carousel. Beam/wave motion follows the global pause alone, so
  // reading a message never stops the diagram itself.
  const held = paused || manualHold || hoverHold;
  useEffect(() => {
    if (held) return;
    if (typeof window.matchMedia !== "function") return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const timer = window.setInterval(
      () => setActive((index) => (index + 1) % transcripts.length),
      4500,
    );
    return () => window.clearInterval(timer);
  }, [held]);

  const transcript = transcripts[active];

  return (
    <div
      className={styles.diagram}
      data-paused={paused}
      role="img"
      aria-label="Illustrative live simulation: three customers call at once and the 24x7 AI front desk answers every line — Maria's question answered, Sam's urgent job captured, Priya's table booked."
    >
      <div className={styles.status}>
        <span className={styles.liveDot} aria-hidden="true" />
        <span className={styles.liveText}>3 calls live · answered at once</span>
        <span className={styles.illustrative}>Illustrative</span>
      </div>

      <div className={styles.core}>
        <span className={styles.coreIcon} aria-hidden="true">
          <PhoneCall size={18} />
        </span>
        <span className={styles.coreText}>
          <strong>24x7 AI front desk</strong>
          <small>answering every line</small>
        </span>
        <span className={styles.wave} aria-hidden="true">
          <i />
          <i />
          <i />
          <i />
        </span>
      </div>

      <div className={styles.lanes}>
        {lanes.map((lane, index) => (
          <div key={lane.name} className={styles.lane}>
            <div className={`${styles.caller} ${styles[lane.tone]}`}>
              <span className={styles.avatar} aria-hidden="true">
                {lane.initials}
              </span>
              <span className={styles.callerText}>
                <strong>{lane.name}</strong>
                <em>{lane.intent}</em>
              </span>
            </div>
            <span
              className={styles.beam}
              aria-hidden="true"
              style={{ animationDelay: `${index * 0.5}s` }}
            >
              <span
                className={styles.pulse}
                style={{ animationDelay: `${index * 0.5}s` }}
              />
            </span>
            <div className={styles.outcome}>
              <span className={styles.outcomeIcon} aria-hidden="true">
                <lane.icon size={16} />
              </span>
              <span>{lane.outcome}</span>
            </div>
          </div>
        ))}
      </div>

      <div
        className={styles.ticker}
        aria-live="polite"
        onMouseEnter={() => !manualHold && setHoverHold(true)}
        onMouseLeave={() => setHoverHold(false)}
        onFocus={() => !manualHold && setHoverHold(true)}
        onBlur={() => setHoverHold(false)}
      >
        <button
          type="button"
          className={styles.tickerToggle}
          onClick={() => setManualHold((hold) => !hold)}
          aria-label={held ? "Play message rotation" : "Pause message rotation"}
          aria-pressed={held}
        >
          {held ? (
            <Play size={12} fill="currentColor" aria-hidden="true" />
          ) : (
            <Pause size={12} aria-hidden="true" />
          )}
        </button>
        <span className={styles.tickerIcon} aria-hidden="true">
          {active === 0 ? <AudioLines size={14} /> : <PhoneIncoming size={14} />}
        </span>
        <div key={active} className={styles.tickerText}>
          <p>{transcript.caller}</p>
          <p className={styles.agentLine}>{transcript.agent}</p>
        </div>
        <div className={styles.tickerDots} aria-hidden="true">
          {transcripts.map((_, index) => (
            <i key={index} data-active={index === active} />
          ))}
        </div>
      </div>
    </div>
  );
}
