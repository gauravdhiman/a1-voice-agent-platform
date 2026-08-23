'use client';

/**
 * Matched-energy LiveKit-style bar visualizer for public voice demos.
 *
 * This finalized bar visualizer keeps the baseline geometry but feeds agent and
 * user bars through the same speaking envelope. It prevents a quiet bot
 * analyser from making the agent look less reactive than the local speaker.
 */

import React, { useEffect, useMemo, useRef, useState } from 'react';

import { createLiveKitV4BarTargets, smoothMotionValues } from './audio-visualizer-motion';
import { cn } from '@/lib/utils';

/** Voice session state used by the public LiveKit-style visualizer. */
export type AgentState =
  | 'connecting'
  | 'initializing'
  | 'listening'
  | 'thinking'
  | 'speaking'
  | 'idle'
  | 'disconnected';

const BAR_SIZE_CLASSES: Record<NonNullable<AgentAudioVisualizerBarV4Props['size']>, string> = {
  icon: 'h-[24px] gap-[2px]',
  sm: 'h-[56px] gap-[4px]',
  md: 'h-[112px] gap-[8px]',
  lg: 'h-[224px] gap-[16px]',
  xl: 'h-[448px] gap-[32px]',
};

const BAR_WIDTH_CLASSES: Record<NonNullable<AgentAudioVisualizerBarV4Props['size']>, string> = {
  icon: 'w-[4px] min-h-[4px]',
  sm: 'w-[8px] min-h-[8px]',
  md: 'w-[16px] min-h-[16px]',
  lg: 'w-[32px] min-h-[32px]',
  xl: 'w-[64px] min-h-[64px]',
};

/** Props accepted by the matched-energy LiveKit bars visualizer. */
export interface AgentAudioVisualizerBarV4Props extends React.ComponentProps<'div'> {
  /** Visualizer size preset shared by the agent and user instances. */
  size?: 'icon' | 'sm' | 'md' | 'lg' | 'xl';
  /** Current voice session state. */
  state?: AgentState;
  /** CSS accent color used by the bars. */
  color?: string;
  /** Number of bars to render. */
  barCount?: number;
  /** Optional transport-provided normalized volume bands. */
  volumeBands?: number[];
  /** Optional custom bar content retained for API parity with the baseline. */
  children?: React.ReactNode;
}

/**
 * Renders matched-size, matched-energy bars for both sides of a voice call.
 * Speaking pulses are fluid and deterministic even when the two input
 * analysers report different absolute levels.
 *
 * @param props - Size, state, color, band input, and HTML div props.
 * @returns A baseline-proportioned LiveKit-style bar visualizer.
 */
export function AgentAudioVisualizerBarV4({
  size = 'md',
  state = 'connecting',
  color = '#22d3ee',
  barCount,
  volumeBands,
  className,
  children,
  style,
  ...props
}: AgentAudioVisualizerBarV4Props) {
  const count = useMemo(() => {
    if (barCount && barCount > 0) return Math.floor(barCount);
    return size === 'icon' || size === 'sm' ? 3 : 5;
  }, [barCount, size]);
  const [bars, setBars] = useState<number[]>(() => Array.from({ length: count }, () => 0));
  const stateRef = useRef<AgentState | undefined>(state);
  const bandsRef = useRef<number[] | undefined>(volumeBands);
  stateRef.current = state;
  bandsRef.current = volumeBands;

  useEffect(() => {
    let animationFrame = 0;
    let previousTime = performance.now();
    let phase = 0;
    let current = Array.from({ length: count }, () => 0);
    let reducedMotion = false;

    try {
      reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    } catch {
      // matchMedia is not available in some embedded webviews.
    }

    const draw = (time: DOMHighResTimeStamp) => {
      const deltaMs = Math.min(48, Math.max(1, time - previousTime));
      previousTime = time;
      // Keep the fallback pulse quick enough to bridge analyser update gaps;
      // live bands still provide the primary amplitude changes.
      phase += deltaMs * 0.0028;
      const targets = createLiveKitV4BarTargets({
        barCount: count,
        phase: reducedMotion ? 0 : phase,
        state: stateRef.current ?? 'idle',
        volumeBands: bandsRef.current,
      });
      current = smoothMotionValues(current, targets, reducedMotion ? 1000 : deltaMs, 36);
      setBars(current);
      animationFrame = requestAnimationFrame(draw);
    };

    animationFrame = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(animationFrame);
  }, [count]);

  return (
    <div
      data-lk-state={state}
      data-visualizer="lk-bars"
      style={{ ...style, color } as React.CSSProperties}
      className={cn('relative flex items-center justify-center', BAR_SIZE_CLASSES[size], className)}
      {...props}
    >
      {bars.map((value, index) => {
        const normalizedValue = Math.max(0, Math.min(1, value));
        const height = `${Math.max(8, normalizedValue * 100)}%`;
        return children ? (
          <React.Fragment key={index}>{children}</React.Fragment>
        ) : (
          <div
            key={index}
            data-lk-index={index}
            data-lk-highlighted={normalizedValue > 0.34}
            className={cn(
              'relative block origin-center rounded-full transition-colors duration-250 ease-linear',
              BAR_WIDTH_CLASSES[size],
            )}
            style={{
              height,
              opacity: 0.7 + normalizedValue * 0.3,
              backgroundColor: color,
              boxShadow: `0 0 ${Math.round(4 + normalizedValue * 10)}px ${colorToRgba(color, 0.2 + normalizedValue * 0.22)}`,
              willChange: 'height, opacity, box-shadow',
            }}
          />
        );
      })}
    </div>
  );
}

/**
 * Adds alpha to hex colors for a restrained bar glow.
 *
 * @param color - Hex color supplied by the caller.
 * @param alpha - Desired opacity.
 * @returns An rgba color for hex input, or the original value as a fallback.
 */
function colorToRgba(color: string, alpha: number): string {
  const match = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(color.trim());
  if (!match) return color;

  let hex = match[1];
  if (hex.length === 3) hex = hex.split('').map((character) => `${character}${character}`).join('');
  const value = Number.parseInt(hex, 16);
  return `rgba(${(value >> 16) & 255}, ${(value >> 8) & 255}, ${value & 255}, ${alpha})`;
}
