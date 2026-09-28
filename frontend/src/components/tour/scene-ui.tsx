"use client";

import { useEffect, useRef } from "react";
import { AudioLines, Check, PhoneCall } from "lucide-react";
import styles from "./platform-tour.module.css";

/**
 * Shared primitives for the per-step tour scenes. Everything is CSS/SMIL —
 * no libraries, no per-frame JS. Each scene remounts on step change
 * (keyed by step), so entrance animations replay deterministically.
 */

/** Animated pointer that travels to a target and clicks. The scene supplies
 * the motion class (each scene knows where its own button lives). Hidden
 * for reduced motion. */
export function Cursor({ motionClass }: { motionClass: string }) {
  return (
    <span className={`${styles.cursor} ${motionClass}`} aria-hidden="true">
      <i />
    </span>
  );
}

/** Live-voice waveform bars. */
export function Waveform({ bars = 7 }: { bars?: number }) {
  return (
    <span className={styles.wavebars} aria-hidden="true">
      {Array.from({ length: bars }, (_, i) => (
        <i key={i} style={{ animationDelay: `${i * 0.12}s` }} />
      ))}
    </span>
  );
}

/**
 * Traveling-pulse flow connector in the spirit of MagicUI's Animated Beam,
 * but fully declarative: a fixed-viewBox SVG path with SMIL pulses, so no
 * layout measuring is needed and it survives every form factor. Pauses
 * itself for reduced motion. Pass `reverse` when the flow runs right to
 * left (every flow here is inbound: callers ring the agent).
 */
export function Beam({ id, label, reverse }: { id: string; label?: string; reverse?: boolean }) {
  const ref = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (
      typeof window.matchMedia === "function" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    ) {
      ref.current?.pauseAnimations();
    }
  }, []);

  return (
    <span className={styles.beamWrap}>
      <svg
        ref={ref}
        viewBox="0 0 300 72"
        preserveAspectRatio="none"
        className={styles.beamSvg}
        aria-hidden="true"
      >
        <defs>
          <linearGradient id={`${id}-beam`} x1="0" y1="0" x2="1" y2="0">
            <stop offset="0" style={{ stopColor: "var(--public-accent)", stopOpacity: 0.15 }} />
            <stop offset="0.5" style={{ stopColor: "var(--public-accent)", stopOpacity: 0.9 }} />
            <stop offset="1" style={{ stopColor: "var(--public-accent)", stopOpacity: 0.15 }} />
          </linearGradient>
        </defs>
        <path
          id={`${id}-beam-path`}
          d={
            reverse
              ? "M294 56 C 220 56, 210 16, 150 16 S 80 56, 6 56"
              : "M6 56 C 80 56, 90 16, 150 16 S 220 56, 294 56"
          }
          fill="none"
          stroke={`url(#${id}-beam)`}
          strokeWidth="2"
        />
        {[0, 1].map((n) => (
          <circle
            key={n}
            r="4.5"
            style={{ fill: "var(--public-accent)" }}
          >
            <animateMotion dur="2s" begin={`${n * -1}s`} repeatCount="indefinite">
              <mpath href={`#${id}-beam-path`} />
            </animateMotion>
          </circle>
        ))}
      </svg>
      {label && <small className={styles.beamLabel}>{label}</small>}
    </span>
  );
}

/** Call status card: rings, then connects with a live waveform. */
export function CallCard({
  caller,
  detail,
  state,
}: {
  caller: string;
  detail: string;
  state: "ringing" | "live";
}) {
  return (
    <div className={styles.callCard} data-state={state}>
      <span className={styles.callAvatar} aria-hidden="true">
        {state === "live" ? (
          <AudioLines size={17} />
        ) : (
          <PhoneCall size={17} />
        )}
      </span>
      <span className={styles.callText}>
        <strong>{caller}</strong>
        <small>{detail}</small>
      </span>
      {state === "ringing" ? (
        <span className={styles.ringBadge}>Ringing…</span>
      ) : (
        <Waveform bars={5} />
      )}
    </div>
  );
}

/** Green approval check with a draw-on animation. */
export function CheckBadge({ label }: { label: string }) {
  return (
    <span className={styles.checkBadge}>
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <circle cx="12" cy="12" r="10" />
        <path d="M8 12.5 L 11 15.5 L 16.5 9.5" />
      </svg>
      {label}
    </span>
  );
}

/** Small caption line under a scene. */
export function SceneNote({ children }: { children: React.ReactNode }) {
  return (
    <p className={styles.mockCaption}>
      <Check size={12} aria-hidden="true" /> {children}
    </p>
  );
}
