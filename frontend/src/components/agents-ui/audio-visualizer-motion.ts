/**
 * Shared deterministic motion models for the two finalized public voice
 * visualizers: radial and lk-bars.
 *
 * The models deliberately do not depend on Web Audio, requestAnimationFrame,
 * or random numbers. This keeps their most important motion guarantees
 * straightforward to test without a microphone or a live call.
 */

export type LiveKitMotionState =
  | "connecting"
  | "initializing"
  | "listening"
  | "thinking"
  | "speaking"
  | "idle"
  | "disconnected";

export interface RadialV4BarTargetOptions {
  /** Number of bars to generate. Values below one return an empty array. */
  barCount: number;
  /** Continuous animation phase in radians. */
  phase: number;
  /** Optional audio/RMS level, clamped to the inclusive 0..1 range. */
  level: number | null | undefined;
  /** Whether the source is actively speaking and should receive dynamic pulses. */
  active: boolean;
}

export interface LiveKitV4BarTargetOptions {
  /** Number of bars to generate. Values below one return an empty array. */
  barCount: number;
  /** Continuous animation phase in radians. */
  phase: number;
  /** Voice UI state used to choose the visual energy profile. */
  state: LiveKitMotionState;
  /** Optional per-bar volume input from a transport or analyser. */
  volumeBands: number[] | null | undefined;
}

/**
 * Clamps a possibly missing level to a safe visual intensity.
 *
 * @param value - Raw level to normalize.
 * @returns A finite number between zero and one.
 */
export function clampMotionLevel(value: number | null | undefined): number {
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(1, value as number));
}

/**
 * Generates the high-contrast radial silhouette for an active speaker.
 *
 * Independent per-spoke pulse rates, sharper crests, and transient flares
 * keep the field moving while a speaker talks instead of settling into one
 * shared level. The phase and audio level remain deterministic for testing.
 *
 * @param options - Bar count, phase, level, and speaking state.
 * @returns One normalized target height for each radial bar.
 */
export function createRadialV4BarTargets({
  barCount,
  phase,
  level,
  active,
}: RadialV4BarTargetOptions): number[] {
  const count = Math.max(0, Math.floor(barCount));
  if (count === 0) return [];

  const audioLevel = clampMotionLevel(level);
  const voiceEnergy = active ? Math.max(audioLevel, 0.32) : audioLevel * 0.34;
  const idleBreath = active ? 0.028 : 0.018;

  return Array.from({ length: count }, (_, index) => {
    const position = index / count;
    const seed = 0.5 + 0.5 * Math.sin(index * 9.37 + 2.1);
    const pulseSpeed = 1.45 + (index % 9) * 0.11;
    const pulse = 0.5 + 0.5 * Math.sin(phase * pulseSpeed + position * 16.4 + seed * 2.7);
    const crest = Math.pow(pulse, 1.55);
    const counterPulse = 0.5 + 0.5 * Math.sin(phase * 0.83 - position * 29.6 + seed * 4.1);
    const detailPulse = 0.5 + 0.5 * Math.sin(phase * 3.2 + position * 47.8 + 1.3);
    const transient = 0.5 + 0.5 * Math.sin(phase * 4.4 + position * 10.7 + seed * 5.8);
    const contour = 0.12 + crest * 0.63 + counterPulse * 0.2 + detailPulse * 0.13;
    const breath = idleBreath * (0.4 + 0.6 * counterPulse);
    const flare = active ? Math.pow(transient, 2.1) * 0.14 : 0;

    return clampMotionLevel(0.022 + breath + voiceEnergy * (0.18 + contour) + flare);
  });
}

/**
 * Generates the shared speaking envelope for the finalized LiveKit-v4 bars.
 *
 * The measured band level nudges the shared envelope, so a quiet bot analyser
 * cannot make the agent look less alive than the local microphone. Both sides
 * therefore receive the same pulse amplitude, timing, and crest; only their
 * color and small per-band input differences remain distinct.
 *
 * @param options - Bar count, phase, state, and optional volume bands.
 * @returns One normalized target height for each visual bar.
 */
export function createLiveKitV4BarTargets({
  barCount,
  phase,
  state,
  volumeBands,
}: LiveKitV4BarTargetOptions): number[] {
  const count = Math.max(0, Math.floor(barCount));
  if (count === 0) return [];

  const input = Array.from({ length: count }, (_, index) => clampMotionLevel(volumeBands?.[index]));
  const hasLocalSignal = state === "listening" && input.some((value) => value > 0.14);
  const isSpeaking = state === "speaking" || hasLocalSignal;
  const averageInput = input.reduce((sum, value) => sum + value, 0) / count;
  const audioLift = isSpeaking ? Math.min(0.16, averageInput * 0.2) : 0;
  const sharedEnergy = isSpeaking ? 0.5 + audioLift : 0;

  return input.map((value, index) => {
    const position = count === 1 ? 0.5 : index / (count - 1);
    const pulse = 0.5 + 0.5 * Math.sin(phase * (2.8 + (index % 3) * 0.28) + index * 1.41);
    const counterPulse = 0.5 + 0.5 * Math.sin(phase * 1.15 - position * Math.PI * 2.4 + 0.8);
    const crest = Math.pow(pulse, 1.28);

    if (isSpeaking) {
      const contour = 0.64 + pulse * 0.42 + counterPulse * 0.08;
      const localVariation = Math.max(0, value - averageInput) * 0.14;
      return clampMotionLevel(0.025 + sharedEnergy * contour + crest * 0.14 + localVariation);
    }

    const base = state === "listening" ? 0.045 : state === "thinking" ? 0.055 : 0.025;
    const motion = state === "listening" ? 0.085 : state === "thinking" ? 0.12 : 0.065;
    return clampMotionLevel(base + pulse * motion + counterPulse * 0.025);
  });
}

/**
 * Moves values toward their targets using a time-based linear response.
 *
 * @param previous - Values rendered on the previous frame.
 * @param target - Desired values for the current frame.
 * @param deltaMs - Milliseconds elapsed since the previous frame.
 * @param responseMs - Optional response window in milliseconds.
 * @returns Smoothed values with the target array's length.
 */
export function smoothMotionValues(previous: number[], target: number[], deltaMs: number, responseMs = 100): number[] {
  const alpha = Math.max(0, Math.min(1, deltaMs / Math.max(1, responseMs)));
  return target.map((value, index) => {
    const current = Number.isFinite(previous[index]) ? previous[index] : 0;
    return current + (value - current) * alpha;
  });
}
