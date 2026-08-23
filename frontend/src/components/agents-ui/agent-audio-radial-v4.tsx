'use client';

/**
 * High-energy radial voice visualizer for the public demo page.
 *
 * This is the finalized radial treatment for the public demo. It keeps the
 * polished orb treatment while giving each spoke its own pulse rate, sharper
 * crest, and transient flare so agent and user speech feel equally alive.
 */

import { useEffect, useRef } from 'react';

import { cn } from '@/lib/utils';

import {
  clampMotionLevel,
  createRadialV4BarTargets,
  smoothMotionValues,
} from './audio-visualizer-motion';

/** Props accepted by the high-energy radial visualizer. */
export interface AgentAudioRadialV4Props {
  /** Optional local MediaStreamTrack to analyse. */
  track?: MediaStreamTrack | null;
  /** Diameter of the square canvas in CSS pixels. */
  size?: number;
  /** Number of radial spokes. */
  barCount?: number;
  /** Accent color used by the core and glow. */
  color?: string;
  /** Optional scalar level for playback sources without a MediaStreamTrack. */
  getAudioLevel?: () => number | null;
  /** Keeps the spoke field energetic while the corresponding speaker is active. */
  active?: boolean;
  /** Additional class names applied to the canvas. */
  className?: string;
}

/**
 * Renders a more reactive radial orb with independent spoke pulses and a
 * speaking energy floor that remains visibly varied when analyser data is
 * sparse or arrives as one scalar level.
 *
 * @param props - Canvas sizing, color, audio source, and active state.
 * @returns A transparent canvas containing the animated radial visualizer.
 */
export function AgentAudioRadialV4({
  track = null,
  size = 260,
  barCount = 72,
  color = '#22d3ee',
  getAudioLevel,
  active = false,
  className,
}: AgentAudioRadialV4Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const smoothRef = useRef<Float32Array>(new Float32Array(barCount));
  const trackRef = useRef<MediaStreamTrack | null | undefined>(track);
  const levelRef = useRef(getAudioLevel);
  const activeRef = useRef(active);

  trackRef.current = track;
  levelRef.current = getAudioLevel;
  activeRef.current = active;

  useEffect(() => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext('2d');
    if (!canvas || !context) return;

    smoothRef.current = new Float32Array(barCount);

    let audioContext: AudioContext | null = null;
    let analyser: AnalyserNode | null = null;
    let source: MediaStreamAudioSourceNode | null = null;
    let frequencyData: Uint8Array<ArrayBuffer> | null = null;
    let attachedTrack: MediaStreamTrack | null = null;
    let animationFrame = 0;
    let previousTime = performance.now();
    let phase = 0;

    const attachTrack = (nextTrack: MediaStreamTrack | null | undefined) => {
      if (nextTrack === attachedTrack) return;

      try {
        source?.disconnect();
      } catch {
        // Audio nodes may already be disconnected by the browser.
      }
      source = null;
      analyser = null;
      frequencyData = null;
      attachedTrack = nextTrack ?? null;

      if (!nextTrack) return;

      try {
        const AudioContextConstructor =
          window.AudioContext ??
          (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
        if (!AudioContextConstructor) return;

        audioContext ??= new AudioContextConstructor();
        if (audioContext.state === 'suspended') void audioContext.resume();
        source = audioContext.createMediaStreamSource(new MediaStream([nextTrack]));
        analyser = audioContext.createAnalyser();
        analyser.fftSize = 1024;
        analyser.smoothingTimeConstant = 0.58;
        source.connect(analyser);
        frequencyData = new Uint8Array(new ArrayBuffer(analyser.frequencyBinCount));
      } catch {
        // Rendering continues with the deterministic scalar/idle motion path.
      }
    };

    const readAudioLevel = (): number => {
      if (analyser && frequencyData) {
        analyser.getByteFrequencyData(frequencyData);
        const binHz = (audioContext?.sampleRate ?? 48_000) / analyser.fftSize;
        const lowBin = Math.max(1, Math.floor(80 / binHz));
        const highBin = Math.min(frequencyData.length - 1, Math.floor(6_000 / binHz));
        let total = 0;
        let weight = 0;

        for (let index = lowBin; index <= highBin; index += 1) {
          const normalized = (index - lowBin) / Math.max(1, highBin - lowBin);
          const emphasis = 1.25 - normalized * 0.42;
          total += (frequencyData[index] / 255) * emphasis;
          weight += emphasis;
        }

        return clampMotionLevel(weight ? total / weight : 0);
      }

      return clampMotionLevel(levelRef.current?.() ?? 0);
    };

    const draw = (time: DOMHighResTimeStamp) => {
      const deltaMs = Math.min(48, Math.max(1, time - previousTime));
      previousTime = time;
      phase += deltaMs * 0.001;
      attachTrack(trackRef.current);

      const devicePixelRatio = globalThis.devicePixelRatio || 1;
      const width = Math.max(1, Math.floor(size * devicePixelRatio));
      if (canvas.width !== width || canvas.height !== width) {
        canvas.width = width;
        canvas.height = width;
      }

      const center = width / 2;
      const baseRadius = width * 0.245;
      const maximumSpokeLength = width * 0.29;
      const level = readAudioLevel();
      const speaking = activeRef.current || level > 0.045;
      const targets = createRadialV4BarTargets({
        barCount,
        phase,
        level,
        active: speaking,
      });
      const smoothed = smoothMotionValues(Array.from(smoothRef.current), targets, deltaMs, 58);
      smoothRef.current.set(smoothed);

      context.clearRect(0, 0, width, width);
      context.save();
      context.translate(center, center);
      context.globalCompositeOperation = 'lighter';

      const pulse = speaking
        ? 1 + level * 0.16 + Math.sin(phase * 3.1) * 0.028
        : 1 + Math.sin(phase * 0.9) * 0.012;
      const auraRadius = (baseRadius + maximumSpokeLength * 0.72) * pulse;
      const aura = context.createRadialGradient(0, 0, baseRadius * 0.35, 0, 0, auraRadius);
      aura.addColorStop(0, colorToRgba(color, speaking ? 0.28 : 0.13));
      aura.addColorStop(0.55, colorToRgba(color, speaking ? 0.13 : 0.06));
      aura.addColorStop(1, colorToRgba(color, 0));
      context.fillStyle = aura;
      context.beginPath();
      context.arc(0, 0, auraRadius, 0, Math.PI * 2);
      context.fill();

      context.globalCompositeOperation = 'source-over';
      context.strokeStyle = colorToRgba(color, speaking ? 0.24 : 0.12);
      context.lineWidth = Math.max(1, width * 0.003);
      context.setLineDash([width * 0.018, width * 0.036]);
      context.lineDashOffset = -phase * width * 0.08;
      context.beginPath();
      context.arc(0, 0, baseRadius + maximumSpokeLength * 0.78, phase * 0.22, Math.PI * 1.66 + phase * 0.22);
      context.stroke();
      context.setLineDash([]);

      const coreRadius = baseRadius * (0.93 + level * 0.14);
      const coreGlow = context.createRadialGradient(0, 0, coreRadius * 0.12, 0, 0, coreRadius * 1.18);
      coreGlow.addColorStop(0, colorToRgba(color, speaking ? 0.94 : 0.62));
      coreGlow.addColorStop(0.42, colorToRgba(color, speaking ? 0.46 : 0.26));
      coreGlow.addColorStop(1, colorToRgba(color, 0));
      context.globalCompositeOperation = 'lighter';
      context.fillStyle = coreGlow;
      context.beginPath();
      context.arc(0, 0, coreRadius * 1.18, 0, Math.PI * 2);
      context.fill();

      context.globalCompositeOperation = 'source-over';
      context.strokeStyle = colorToRgba(color, speaking ? 0.94 : 0.62);
      context.lineWidth = Math.max(2, width * 0.005);
      context.shadowBlur = speaking ? width * 0.03 : width * 0.014;
      context.shadowColor = color;
      context.beginPath();
      context.arc(0, 0, baseRadius, 0, Math.PI * 2);
      context.stroke();
      context.shadowBlur = 0;

      const slotAngle = (Math.PI * 2) / barCount;
      const spokeWidth = Math.max(2, (width / barCount) * 0.5);
      for (let index = 0; index < barCount; index += 1) {
        const value = smoothed[index] ?? 0;
        const angle = index * slotAngle + phase * 0.18;
        const startRadius = baseRadius + width * 0.014;
        const spokeLength = width * 0.009 + value * maximumSpokeLength;
        const endRadius = startRadius + spokeLength;
        const startX = Math.cos(angle) * startRadius;
        const startY = Math.sin(angle) * startRadius;
        const endX = Math.cos(angle) * endRadius;
        const endY = Math.sin(angle) * endRadius;
        const hue = 184 + ((index / barCount) * 142 + phase * 18) % 142;

        context.strokeStyle = `hsla(${hue}, 94%, ${58 + value * 25}%, ${0.28 + value * 0.72})`;
        context.lineWidth = spokeWidth * (0.72 + value * 0.48);
        context.lineCap = 'round';
        context.beginPath();
        context.moveTo(startX, startY);
        context.lineTo(endX, endY);
        context.stroke();

        if (value > 0.42) {
          context.fillStyle = `hsla(${hue}, 100%, 84%, ${0.5 + value * 0.5})`;
          context.beginPath();
          context.arc(endX, endY, spokeWidth * (0.3 + value * 0.14), 0, Math.PI * 2);
          context.fill();
        }
      }

      context.globalCompositeOperation = 'lighter';
      context.fillStyle = colorToRgba(color, speaking ? 0.88 : 0.44);
      for (let orbit = 0; orbit < 3; orbit += 1) {
        const orbitAngle = phase * (0.5 + orbit * 0.14) + orbit * 2.1;
        const orbitRadius = baseRadius + maximumSpokeLength * (0.56 + orbit * 0.12);
        context.beginPath();
        context.arc(
          Math.cos(orbitAngle) * orbitRadius,
          Math.sin(orbitAngle) * orbitRadius,
          Math.max(1.5, width * 0.006),
          0,
          Math.PI * 2,
        );
        context.fill();
      }

      context.restore();
      animationFrame = requestAnimationFrame(draw);
    };

    animationFrame = requestAnimationFrame(draw);
    return () => {
      cancelAnimationFrame(animationFrame);
      try {
        source?.disconnect();
        void audioContext?.close();
      } catch {
        // The browser may close the context during page teardown.
      }
    };
  }, [barCount, color, size]);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      className={cn('block', className)}
      width={size}
      height={size}
      style={{ width: size, height: size }}
    />
  );
}

/**
 * Converts a hex accent color to an alpha-aware canvas color.
 *
 * @param color - Hex color supplied by the visualizer caller.
 * @param alpha - Desired opacity.
 * @returns An rgba string for hex colors, or the original color as a fallback.
 */
function colorToRgba(color: string, alpha: number): string {
  const match = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(color.trim());
  if (!match) return color;

  let hex = match[1];
  if (hex.length === 3) hex = hex.split('').map((character) => `${character}${character}`).join('');
  const value = Number.parseInt(hex, 16);
  return `rgba(${(value >> 16) & 255}, ${(value >> 8) & 255}, ${value & 255}, ${alpha})`;
}
