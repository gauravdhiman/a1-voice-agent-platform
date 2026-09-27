"use client";

import { useEffect, useRef } from "react";

interface AuroraFieldProps {
  theme: "day" | "night";
  paused: boolean;
}

interface Orb {
  x: number;
  y: number;
  radius: number;
  dx: number;
  dy: number;
  alpha: number;
  hue: number;
}

interface Speck {
  x: number;
  y: number;
  radius: number;
  phase: number;
  speed: number;
  depth: number;
}

/**
 * Lightweight ambient canvas for the homepage hero.
 *
 * Inspired by ball-pit style fields (e.g. ReactBits Ballpit) but deliberately
 * cheap: a handful of large low-alpha drifting orbs plus a sparse speck layer
 * on a single 2D canvas. No physics engine, no WebGL, no per-frame React
 * state. Rendering is capped at ~30fps with a 1.5 DPR ceiling, pauses
 * offscreen / in hidden tabs / when `paused`, and renders one static frame
 * for reduced-motion visitors.
 */
export function AuroraField({ theme, paused }: AuroraFieldProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");
    const host = canvas?.closest<HTMLElement>("[data-aurora]");
    if (!canvas || !context || !host) return;
    if (
      typeof IntersectionObserver === "undefined" ||
      typeof ResizeObserver === "undefined" ||
      typeof window.matchMedia !== "function"
    ) {
      return;
    }

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
    let width = 0;
    let height = 0;
    let frame = 0;
    let last = 0;
    let time = 0;
    let visible = true;
    const pointer = { x: 0, y: 0, tx: 0, ty: 0 };

    // Deterministic pseudo-random so server/client and resizes agree.
    const rand = (seed: number) => {
      const value = Math.sin(seed * 12.9898) * 43758.5453;
      return value - Math.floor(value);
    };

    const orbs: Orb[] = Array.from({ length: 14 }, (_, i) => ({
      x: rand(i + 1),
      y: rand(i + 101),
      radius: 0.1 + rand(i + 201) * 0.16,
      dx: (rand(i + 301) - 0.5) * 0.00012,
      dy: (rand(i + 401) - 0.5) * 0.0001,
      alpha: 0.1 + rand(i + 501) * 0.12,
      hue: rand(i + 601),
    }));

    const specks: Speck[] = Array.from({ length: 90 }, (_, i) => ({
      x: rand(i + 701),
      y: rand(i + 801),
      radius: 0.6 + rand(i + 901) * 1.1,
      phase: rand(i + 1001) * Math.PI * 2,
      speed: 0.0004 + rand(i + 1101) * 0.0008,
      depth: 0.25 + rand(i + 1201) * 0.75,
    }));

    const measure = () => {
      width = host.clientWidth;
      height = host.clientHeight;
      const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
      canvas.width = Math.max(1, Math.floor(width * dpr));
      canvas.height = Math.max(1, Math.floor(height * dpr));
      context.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    const palette = () =>
      theme === "night"
        ? { orb: "120,170,255", speck: "150,195,255", glow: "80,130,255" }
        : { orb: "40,90,220", speck: "20,70,180", glow: "60,110,230" };

    const draw = () => {
      const colors = palette();
      context.clearRect(0, 0, width, height);
      const minDim = Math.min(width, height) || 1;

      // Soft orbs: large low-alpha circles. No shadowBlur (expensive);
      // softness comes from size + low alpha over the page gradient.
      for (const orb of orbs) {
        const px =
          (orb.x + pointer.x * 0.03 * orb.alpha * 10) * width;
        const py =
          (orb.y + pointer.y * 0.03 * orb.alpha * 10) * height;
        const radius = orb.radius * minDim;
        const gradient = context.createRadialGradient(px, py, 0, px, py, radius);
        gradient.addColorStop(0, `rgba(${colors.orb},${orb.alpha})`);
        gradient.addColorStop(1, `rgba(${colors.orb},0)`);
        context.fillStyle = gradient;
        context.beginPath();
        context.arc(px, py, radius, 0, Math.PI * 2);
        context.fill();
      }

      // Sparse specks drift gently; parallax by depth.
      for (const speck of specks) {
        const drift = Math.sin(time * speck.speed + speck.phase) * 6;
        const px =
          speck.x * width + pointer.x * 14 * speck.depth + drift * speck.depth;
        const py =
          speck.y * height + pointer.y * 14 * speck.depth + drift * 0.6;
        const twinkle =
          0.16 + 0.22 * (0.5 + 0.5 * Math.sin(time * 0.001 + speck.phase * 2));
        context.fillStyle = `rgba(${colors.speck},${(twinkle * speck.depth).toFixed(3)})`;
        context.beginPath();
        context.arc(px, py, speck.radius, 0, Math.PI * 2);
        context.fill();
      }

      // One quiet horizon glow line near the bottom of the hero.
      const glowY = height * 0.88;
      const glow = context.createLinearGradient(0, glowY - 60, 0, glowY + 40);
      glow.addColorStop(0, `rgba(${colors.glow},0)`);
      glow.addColorStop(0.5, `rgba(${colors.glow},0.12)`);
      glow.addColorStop(1, `rgba(${colors.glow},0)`);
      context.fillStyle = glow;
      context.fillRect(0, glowY - 60, width, 100);
    };

    const step = () => {
      for (const orb of orbs) {
        orb.x += orb.dx;
        orb.y += orb.dy;
        if (orb.x < -0.2) orb.x = 1.2;
        if (orb.x > 1.2) orb.x = -0.2;
        if (orb.y < -0.2) orb.y = 1.2;
        if (orb.y > 1.2) orb.y = -0.2;
      }
      pointer.x += (pointer.tx - pointer.x) * 0.04;
      pointer.y += (pointer.ty - pointer.y) * 0.04;
    };

    const tick = (timestamp: number) => {
      frame = 0;
      if (!visible || document.hidden) return;
      if (timestamp - last >= 33) {
        time += Math.min(timestamp - last, 60);
        last = timestamp;
        step();
        draw();
      }
      if (!paused && !reduced.matches) frame = requestAnimationFrame(tick);
      else draw();
    };

    const schedule = () => {
      if (!frame && visible && !document.hidden)
        frame = requestAnimationFrame(tick);
    };

    const onResize = () => {
      measure();
      schedule();
    };

    const onPointer = (event: PointerEvent) => {
      if (paused || reduced.matches || event.pointerType !== "mouse") return;
      pointer.tx = event.clientX / window.innerWidth - 0.5;
      pointer.ty = event.clientY / window.innerHeight - 0.5;
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
    observer.observe(host);

    const resize = new ResizeObserver(onResize);
    resize.observe(host);

    measure();
    schedule();
    window.addEventListener("pointermove", onPointer, { passive: true });
    document.addEventListener("visibilitychange", onMotion);
    reduced.addEventListener("change", onMotion);
    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
      resize.disconnect();
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
