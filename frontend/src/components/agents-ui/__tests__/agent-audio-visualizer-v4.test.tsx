import { act, render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AgentAudioVisualizerBarV4 } from "../agent-audio-visualizer-livekit-bar-v4";

describe("AgentAudioVisualizerBarV4", () => {
  let frames: FrameRequestCallback[];

  beforeEach(() => {
    frames = [];
    vi.stubGlobal("requestAnimationFrame", (callback: FrameRequestCallback) => {
      frames.push(callback);
      return frames.length;
    });
    vi.stubGlobal("cancelAnimationFrame", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders matched baseline-sized speaking bars with fluid motion", () => {
    const { container } = render(
      <AgentAudioVisualizerBarV4
        size="lg"
        state="speaking"
        barCount={5}
        volumeBands={[0.08, 0.08, 0.08, 0.08, 0.08]}
        color="#22d3ee"
      />,
    );

    expect(container.querySelector('[data-visualizer="lk-bars"]')).not.toBeNull();
    expect(container.querySelectorAll("[data-lk-index]")).toHaveLength(5);
    const firstBar = container.querySelector<HTMLElement>('[data-lk-index="0"]');
    expect(firstBar?.className).toContain("w-[32px]");
    expect(firstBar?.className).not.toContain("transition-[height");

    act(() => {
      for (let frame = 1; frame <= 12; frame += 1) {
        frames.shift()?.(frame * 16);
      }
    });

    const heights = Array.from(container.querySelectorAll<HTMLElement>("[data-lk-index]"), (bar) =>
      Number.parseFloat(bar.style.height),
    );
    expect(Math.max(...heights)).toBeGreaterThan(35);
    expect(new Set(heights).size).toBeGreaterThan(1);
  });
});
