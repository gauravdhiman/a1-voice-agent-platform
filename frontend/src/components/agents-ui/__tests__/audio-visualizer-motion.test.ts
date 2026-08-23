import { describe, expect, it } from "vitest";

import {
  createLiveKitV4BarTargets,
  createRadialV4BarTargets,
  smoothMotionValues,
} from "../audio-visualizer-motion";

describe("final audio visualizer motion models", () => {
  it("creates a high-contrast temporal radial-v4 pulse field", () => {
    const first = createRadialV4BarTargets({
      barCount: 72,
      phase: 0.4,
      level: 0.72,
      active: true,
    });
    const later = createRadialV4BarTargets({
      barCount: 72,
      phase: 1.7,
      level: 0.72,
      active: true,
    });

    expect(new Set(first).size).toBeGreaterThan(30);
    expect(Math.max(...first) - Math.min(...first)).toBeGreaterThan(0.3);
    expect(first.some((value) => value > 0.7)).toBe(true);
    expect(first.some((value) => value < 0.35)).toBe(true);
    expect(first.reduce((sum, value, index) => sum + Math.abs(value - (later[index] ?? 0)), 0)).toBeGreaterThan(2);
  });

  it("keeps livekit-v4 agent and user speaking envelopes aligned", () => {
    const agent = createLiveKitV4BarTargets({
      barCount: 5,
      phase: 0.8,
      state: "speaking",
      volumeBands: [0.08, 0.08, 0.08, 0.08, 0.08],
    });
    const user = createLiveKitV4BarTargets({
      barCount: 5,
      phase: 0.8,
      state: "speaking",
      volumeBands: [0.62, 0.62, 0.62, 0.62, 0.62],
    });
    const later = createLiveKitV4BarTargets({
      barCount: 5,
      phase: 2.1,
      state: "speaking",
      volumeBands: [0.08, 0.08, 0.08, 0.08, 0.08],
    });
    const average = (values: number[]) => values.reduce((sum, value) => sum + value, 0) / values.length;

    expect(Math.max(...agent) - Math.min(...agent)).toBeGreaterThan(0.18);
    expect(Math.max(...user) - Math.min(...user)).toBeGreaterThan(0.18);
    expect(Math.abs(average(agent) - average(user))).toBeLessThan(0.12);
    expect(agent.reduce((sum, value, index) => sum + Math.abs(value - (later[index] ?? 0)), 0)).toBeGreaterThan(0.35);
  });

  it("keeps livekit-v4 bars responsive to a real change in audio energy", () => {
    const quiet = createLiveKitV4BarTargets({
      barCount: 5,
      phase: 1.1,
      state: "speaking",
      volumeBands: [0.08, 0.08, 0.08, 0.08, 0.08],
    });
    const loud = createLiveKitV4BarTargets({
      barCount: 5,
      phase: 1.1,
      state: "speaking",
      volumeBands: [0.9, 0.9, 0.9, 0.9, 0.9],
    });
    const average = (values: number[]) => values.reduce((sum, value) => sum + value, 0) / values.length;

    expect(average(loud) - average(quiet)).toBeGreaterThan(0.08);
  });

  it("smooths toward a target with a capped, frame-rate-independent step", () => {
    expect(smoothMotionValues([0, 0], [1, 0.5], 16)).toEqual([0.16, 0.08]);
    expect(smoothMotionValues([0, 0], [1, 0.5], 1000)).toEqual([1, 0.5]);
    expect(smoothMotionValues([1, 0.5], [0, 0], 16)).toEqual([0.84, 0.42]);
  });
});
