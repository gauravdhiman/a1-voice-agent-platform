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
 * but fully declarative geometry with a tiny rAF driver: two beads ride a
 * fixed-viewBox SVG path back and forth together (there and back again),
 * one trailing the other, so no layout measuring is needed and it survives
 * every form factor. Parks statically for reduced motion and idles
 * offscreen.
 */
export function Beam({ id, label, reverse }: { id: string; label?: string; reverse?: boolean }) {
  const svgRef = useRef<SVGSVGElement>(null);
  const pathRef = useRef<SVGPathElement>(null);
  const dotsRef = useRef<Array<SVGCircleElement | null>>([]);

  useEffect(() => {
    const svg = svgRef.current;
    const path = pathRef.current;
    const dots = dotsRef.current;
    if (!svg || !path || dots.some((dot) => !dot)) return;
    let length = 0;
    try {
      length = path.getTotalLength();
    } catch {
      return;
    }
    if (length <= 0) return;

    const place = (fraction: number, index: number) => {
      const point = path.getPointAtLength(length * fraction);
      dots[index]?.setAttribute("cx", String(point.x));
      dots[index]?.setAttribute("cy", String(point.y));
    };

    if (
      typeof window.matchMedia === "function" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    ) {
      place(0.42, 0);
      place(0.58, 1);
      return;
    }

    let frame = 0;
    let visible = true;
    const TRAVERSE_MS = 1900;
    // Small phase trail so the second bead follows the first; both always
    // travel the same direction and never cross.
    const TRAIL = 0.16;
    const tick = (now: number) => {
      frame = 0;
      if (!visible || document.hidden) return;
      for (let i = 0; i < dots.length; i += 1) {
        const phase = ((((now - i * TRAIL * TRAVERSE_MS) / TRAVERSE_MS) % 2) + 2) % 2;
        place(1 - Math.abs(1 - phase), i);
      }
      frame = requestAnimationFrame(tick);
    };
    const schedule = () => {
      if (!frame && visible && !document.hidden)
        frame = requestAnimationFrame(tick);
    };

    let observer: IntersectionObserver | null = null;
    if (typeof IntersectionObserver !== "undefined") {
      observer = new IntersectionObserver(([entry]) => {
        visible = entry.isIntersecting;
        if (!visible) {
          cancelAnimationFrame(frame);
          frame = 0;
        } else schedule();
      });
      observer.observe(svg);
    }
    schedule();
    return () => {
      cancelAnimationFrame(frame);
      observer?.disconnect();
    };
  }, [id]);

  return (
    <span className={styles.beamWrap}>
      <svg
        ref={svgRef}
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
          ref={pathRef}
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
            ref={(node) => {
              dotsRef.current[n] = node;
            }}
          />
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
          <PhoneCall size={15} strokeWidth={1.75} style={{ transform: "scale(0.85)" }} />
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
