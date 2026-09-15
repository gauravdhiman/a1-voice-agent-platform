"use client";

import { useEffect, useRef } from "react";

interface ParticleFieldProps {
  theme: "day" | "night";
  paused: boolean;
}

/** Scroll-hold map: each formation holds still for ~62% of its chapter, then
 * morphs during the remaining ~38%. Without plateaus the dots never settle
 * long enough to read, so visitors see a blur instead of a bell, wave,
 * calendar, or captured lead. */
export function shapeProgress(progress: number): number {
  if (progress <= 0) return 0;
  if (progress >= 3) return 3;
  const HOLD = 0.62;
  const MORPH = 0.38;
  const segment = Math.floor(progress);
  const local = progress - segment;
  if (local <= HOLD) return segment;
  const t = (local - HOLD) / MORPH;
  return segment + t * t * (3 - 2 * t);
}

/** Decorative, bounded canvas field. Scroll morphs a ringing service bell
 * into a voice wave, booking calendar, and captured-lead check. Each
 * formation holds still mid-chapter (see shapeProgress) so it can actually
 * be read. Stops offscreen, in hidden tabs, and for reduced motion. */
export function ParticleField({ theme, paused }: ParticleFieldProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");
    const journey = canvas?.closest<HTMLElement>("[data-journey]");
    if (!canvas || !context || !journey) return;

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
    let width = 0;
    let height = 0;
    let frame = 0;
    let time = 0;
    let lastTime = 0;
    let visible = true;
    let progress = 0;
    const pointer = { x: 0, y: 0 };
    // Deterministic sampling avoids random hydration or resize differences.
    const points = Array.from({ length: 2400 }, (_, i) => {
      const u = (i % 120) / 120;
      const v = Math.floor(i / 120) / 20;
      const seed = (salt: number) => {
        const value = Math.sin((i + salt) * 12.9898) * 43758.5453;
        return value - Math.floor(value);
      };
      const bellPoint = () => {
        const xNoise = seed(7);
        const yNoise = seed(19);
        // A counter service bell: dome, base bar, and top button, with ring
        // arcs on both shoulders. Deliberately simple and symmetric — a bell
        // reads at any dot density and tilt, and "ring for service" is the
        // whole front-desk story in one symbol.
        const baseY = 0.38;
        if (i < 450) {
          // Base bar the bell sits on.
          return {
            point: [
              -0.5 + xNoise * 1.0,
              baseY + (yNoise - 0.5) * 0.12,
              (xNoise - 0.5) * 0.06,
            ],
            role: "receiver" as const,
          };
        }
        if (i < 1400) {
          // Dome: a thick half-ring so it stays solid, never a hairline.
          const angle = Math.PI + xNoise * Math.PI;
          const radius = 0.36 + (yNoise - 0.5) * 0.13;
          return {
            point: [
              Math.cos(angle) * radius,
              baseY + Math.sin(angle) * radius,
              (xNoise - 0.5) * 0.06,
            ],
            role: "receiver" as const,
          };
        }
        if (i < 1550) {
          // Top button: small filled disc.
          const angle = xNoise * Math.PI * 2;
          const radius = Math.sqrt(yNoise) * 0.07;
          return {
            point: [
              Math.cos(angle) * radius,
              -0.06 + Math.sin(angle) * radius,
              (xNoise - 0.5) * 0.05,
            ],
            role: "receiver" as const,
          };
        }
        if (i < 2200) {
          // Ring arcs on both shoulders of the dome.
          const side = i < 1875 ? -1 : 1;
          const arc = Math.floor((i < 1875 ? i - 1550 : i - 1875) / 163);
          const angle =
            side < 0
              ? Math.PI * (1.06 + yNoise * 0.38) + xNoise * 0.02
              : Math.PI * (1.56 + yNoise * 0.38) + xNoise * 0.02;
          const radius = 0.52 + arc * 0.15;
          const centerX = side * 0.1;
          const centerY = 0.12;
          return {
            point: [
              centerX + Math.cos(angle) * radius,
              centerY + Math.sin(angle) * radius,
              (xNoise - 0.5) * 0.05,
            ],
            role: "signal" as const,
          };
        }
        // Bright core on the button: the bell ringing right now.
        const pulseAngle = xNoise * Math.PI * 2;
        const pulseRadius = Math.sqrt(yNoise) * 0.05;
        return {
          point: [
            Math.cos(pulseAngle) * pulseRadius,
            -0.06 + Math.sin(pulseAngle) * pulseRadius,
            0.12,
          ],
          role: "active" as const,
        };
      };
      const bell = bellPoint();
      const wave = [
        (u - 0.5) * 1.9,
        Math.sin(u * Math.PI * 7) * (0.17 + Math.sin(u * Math.PI) * 0.3) +
          (v - 0.5) * 0.25,
        (v - 0.5) * 0.65,
      ];
      const col = i % 48;
      const row = Math.floor(i / 48);
      // A grid becomes a calendar with four highlighted appointment cells.
      const calendar = [
        (col / 47 - 0.5) * 1.45,
        (row / 49 - 0.5) * 1.45,
        Math.sin(col * 0.4) * 0.025,
      ];
      const targetRole = i < 1600 ? "ring" : "check";
      const targetIndex = i < 1600 ? i : i - 1600;
      // Three bold rings read instantly as "captured / done". Five thin rings
      // looked busy at dot density and drowned out the check mark.
      const targetRing = [0.24, 0.46, 0.68][i % 3];
      // Each ring gets the same angular sampling instead of forming a spiral
      // as particles morph into place.
      const targetAngle =
        i < 1600
          ? (Math.floor(i / 3) / 534) * Math.PI * 2
          : targetIndex * 0.031;
      const targetPoint =
        i < 1600
          ? [
              Math.cos(targetAngle) * (targetRing + (seed(31) - 0.5) * 0.03),
              Math.sin(targetAngle) * (targetRing + (seed(31) - 0.5) * 0.03),
              Math.sin(targetAngle * 0.7) * 0.08,
            ]
          : (() => {
              const progress = targetIndex / 800;
              const firstHalf = progress < 0.42;
              const local = firstHalf
                ? progress / 0.42
                : (progress - 0.42) / 0.58;
              const start = firstHalf ? [-0.3, 0.02] : [-0.05, 0.26];
              const end = firstHalf ? [-0.05, 0.26] : [0.38, -0.24];
              // Wider jitter makes a thick, confident check instead of a hairline.
              return [
                start[0] +
                  (end[0] - start[0]) * local +
                  (seed(41) - 0.5) * 0.055,
                start[1] +
                  (end[1] - start[1]) * local +
                  (seed(53) - 0.5) * 0.055,
                0.12,
              ];
            })();
      return {
        shapes: [bell.point, wave, calendar, targetPoint],
        bellRole: bell.role,
        targetRole,
        u,
        v,
        col,
        row,
      };
    });

    const measure = () => {
      width = canvas.clientWidth;
      height = canvas.clientHeight;
      const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      context.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    const readScroll = () => {
      const rect = journey.getBoundingClientRect();
      progress = Math.max(
        0,
        Math.min(3, -rect.top / (window.innerHeight * 0.94)),
      );
    };
    const draw = () => {
      context.clearRect(0, 0, width, height);
      const mobile = width < 760;
      const scale = Math.min(width * (mobile ? 0.47 : 0.29), height * 0.43);
      const cx = width * (mobile ? 0.58 : 0.735);
      const cy = height * (mobile ? 0.68 : 0.51);
      // Holds make each chapter readable: sProgress rests on integers while
      // the visitor reads, then eases through the morph window.
      const sProgress = shapeProgress(progress);
      const stage = Math.min(2, Math.floor(sProgress));
      const mix = sProgress - stage;
      const moving = !paused && !reduced.matches;
      const rotation = moving ? Math.sin(time * 0.00015) * 0.17 : 0.08;
      // A nearly flat bell reads far better than a tilted one; keep a hint
      // of depth at rest without distorting the silhouette.
      const tilt = 0.32 * (1 - Math.min(sProgress, 1));
      const color = theme === "night" ? "143,205,255" : "11,67,163";
      const day = theme === "day";
      // Wide screens spread the same dots over more pixels: grow them so the
      // formations stay solid past 1600px. Day mode gets extra size + alpha
      // because cobalt on paper blue needs more weight than ice-blue on ink.
      const wideBoost = Math.min(1.45, Math.max(1, width / 1440));
      const dotSize = (day ? 1.32 : 1) * wideBoost;
      const guideAlpha = day ? 1.6 : 1;

      for (let i = 0; i < points.length; i += mobile ? 2 : 1) {
        const point = points[i];
        const a = point.shapes[stage];
        const b = point.shapes[stage + 1];
        let x = a[0] + (b[0] - a[0]) * mix;
        let y = a[1] + (b[1] - a[1]) * mix;
        let z = a[2] + (b[2] - a[2]) * mix;
        const rotatedY = y * Math.cos(tilt) - z * Math.sin(tilt);
        z = y * Math.sin(tilt) + z * Math.cos(tilt);
        y = rotatedY;
        const rotatedX = x * Math.cos(rotation) - z * Math.sin(rotation);
        z = x * Math.sin(rotation) + z * Math.cos(rotation);
        x = rotatedX;
        const drift = moving
          ? Math.sin(time * 0.0007 + point.u * 12 + point.v * 6) * 0.017
          : 0;
        const perspective = 2.5 / (2.5 - z);
        const px = cx + (x + drift) * scale * perspective + pointer.x * 8;
        const py = cy + (y + drift) * scale * perspective + pointer.y * 8;
        const isBooking = sProgress > 1.55 && sProgress < 2.45;
        const booked =
          (point.col > 9 &&
            point.col < 18 &&
            point.row > 16 &&
            point.row < 24) ||
          (point.col > 28 &&
            point.col < 37 &&
            point.row > 30 &&
            point.row < 38);
        const grid =
          point.col % 10 === 0 || point.row % 10 === 0 || point.row < 8;
        const isBell = sProgress < 0.55;
        const isTarget = sProgress > 2.55;
        const role = isBell
          ? point.bellRole
          : isTarget
            ? point.targetRole
            : "default";
        const alpha = isBell
          ? role === "signal"
            ? 0.7
            : role === "active"
              ? 0.98
              : 0.9
          : isTarget
            ? role === "check"
              ? 0.95
              : 0.18 + ((z + 1) / 2) * 0.55
            : isBooking
              ? booked
                ? 0.95
                : grid
                  ? 0.62
                  : 0.16
              : 0.25 + ((z + 1) / 2) * 0.65;
        const visibleAlpha = day ? Math.min(1, alpha * 1.35 + 0.1) : alpha;
        context.fillStyle = `rgba(${color},${visibleAlpha})`;
        context.beginPath();
        context.arc(
          px,
          py,
          (i % 19 === 0 ? 1.9 : 1.0) * perspective * dotSize,
          0,
          Math.PI * 2,
        );
        context.fill();
      }
      // Quiet vector guides make each dot formation unmistakable while leaving
      // particles as the hero. Guides fade out during morph windows.
      if (sProgress < 0.62) {
        const fade = 1 - sProgress / 0.62;
        context.strokeStyle = `rgba(${color},${Math.min(0.42, 0.24 * fade * guideAlpha)})`;
        context.lineCap = "round";
        // Base bar the bell sits on.
        context.lineWidth = Math.max(2, scale * 0.09);
        context.beginPath();
        context.moveTo(cx - scale * 0.5, cy + scale * 0.38);
        context.lineTo(cx + scale * 0.5, cy + scale * 0.38);
        context.stroke();
        // Dome: one confident arc, drawn wide so it backs the dots instead
        // of competing with them.
        context.lineWidth = Math.max(2, scale * 0.08);
        context.beginPath();
        context.arc(cx, cy + scale * 0.38, scale * 0.36, Math.PI, 2 * Math.PI);
        context.stroke();
        context.lineWidth = 1;
        // Top button.
        context.beginPath();
        context.arc(cx, cy - scale * 0.06, scale * 0.07, 0, Math.PI * 2);
        context.stroke();
        // Ring arcs on both shoulders.
        for (const side of [-1, 1]) {
          for (const radius of [0.52, 0.67]) {
            context.beginPath();
            context.arc(
              cx + side * scale * 0.1,
              cy + scale * 0.12,
              scale * radius,
              side < 0 ? Math.PI * 1.06 : Math.PI * 1.56,
              side < 0 ? Math.PI * 1.44 : Math.PI * 1.94,
            );
            context.stroke();
          }
        }
      }
      if (sProgress > 1.55 && sProgress < 2.5) {
        // A calendar frame + header bar makes the booking grid read as a
        // calendar even when individual dots are faint on paper blue.
        const edge = Math.min(
          1,
          (sProgress - 1.55) / 0.15,
          (2.5 - sProgress) / 0.15,
        );
        context.strokeStyle = `rgba(${color},${Math.min(0.4, 0.26 * edge * guideAlpha)})`;
        context.lineWidth = 1;
        context.strokeRect(
          cx - scale * 0.725,
          cy - scale * 0.725,
          scale * 1.45,
          scale * 1.45,
        );
        context.beginPath();
        context.moveTo(cx - scale * 0.725, cy - scale * 0.44);
        context.lineTo(cx + scale * 0.725, cy - scale * 0.44);
        context.stroke();
        for (const bx of [-0.36, 0.36]) {
          context.beginPath();
          context.arc(
            cx + scale * bx,
            cy - scale * 0.725,
            scale * 0.045,
            0,
            Math.PI * 2,
          );
          context.stroke();
        }
      }
      if (sProgress > 2.55) {
        // Rings + check reinforce the "captured outcome" story in the final
        // chapter, even when the visitor pauses the ambient motion.
        const grow = Math.min(1, (sProgress - 2.55) / 0.3);
        context.strokeStyle = `rgba(${color},${Math.min(0.42, (0.2 + grow * 0.14) * guideAlpha)})`;
        context.lineWidth = 1;
        context.beginPath();
        for (const ring of [0.24, 0.46, 0.68]) {
          context.moveTo(cx + scale * ring, cy);
          context.arc(cx, cy, scale * ring, 0, Math.PI * 2);
        }
        context.stroke();
        context.lineWidth = 1.6;
        context.beginPath();
        context.moveTo(cx - scale * 0.3, cy + scale * 0.02);
        context.lineTo(cx - scale * 0.05, cy + scale * 0.26);
        context.lineTo(cx + scale * 0.38, cy - scale * 0.24);
        context.stroke();
      }
    };
    const tick = (timestamp: number) => {
      frame = 0;
      if (!visible || document.hidden) return;
      if (timestamp - lastTime >= 32) {
        time += Math.min(timestamp - lastTime, 50);
        lastTime = timestamp;
        draw();
      }
      if (!paused && !reduced.matches) frame = requestAnimationFrame(tick);
      else draw();
    };
    const schedule = () => {
      if (!frame && visible && !document.hidden)
        frame = requestAnimationFrame(tick);
    };
    const onScroll = () => {
      readScroll();
      schedule();
    };
    const onResize = () => {
      measure();
      readScroll();
      schedule();
    };
    const onPointer = (event: PointerEvent) => {
      if (paused || reduced.matches || event.pointerType !== "mouse") return;
      pointer.x = event.clientX / window.innerWidth - 0.5;
      pointer.y = event.clientY / window.innerHeight - 0.5;
    };
    const onMotion = () => {
      cancelAnimationFrame(frame);
      frame = 0;
      schedule();
    };
    const observer = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting;
      if (!visible) {
        cancelAnimationFrame(frame);
        frame = 0;
      } else schedule();
    });
    observer.observe(journey);
    const resize = new ResizeObserver(onResize);
    resize.observe(canvas);
    measure();
    readScroll();
    schedule();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("pointermove", onPointer, { passive: true });
    document.addEventListener("visibilitychange", onMotion);
    reduced.addEventListener("change", onMotion);
    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
      resize.disconnect();
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("pointermove", onPointer);
      document.removeEventListener("visibilitychange", onMotion);
      reduced.removeEventListener("change", onMotion);
    };
  }, [theme, paused]);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      style={{ width: "100%", height: "100%", display: "block" }}
    />
  );
}
