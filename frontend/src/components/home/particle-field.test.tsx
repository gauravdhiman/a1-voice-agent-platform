/** The decorative animation must stop scheduling when unmounted, paused,
 * or when the visitor requests reduced motion. */
import React from "react";
import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ParticleField, shapeProgress } from "./particle-field";

function setup(reduced = false) {
  const frames: FrameRequestCallback[] = [];
  const cancel = vi.fn();
  const disconnect = vi.fn();
  vi.stubGlobal(
    "requestAnimationFrame",
    vi.fn((callback: FrameRequestCallback) => {
      frames.push(callback);
      return frames.length;
    }),
  );
  vi.stubGlobal("cancelAnimationFrame", cancel);
  vi.stubGlobal(
    "IntersectionObserver",
    class {
      observe() {}
      disconnect = disconnect;
    },
  );
  vi.spyOn(window, "matchMedia").mockReturnValue({
    matches: reduced,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  } as unknown as MediaQueryList);
  const draw = vi.fn();
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({
    setTransform: vi.fn(),
    clearRect: draw,
    beginPath: vi.fn(),
    closePath: vi.fn(),
    moveTo: vi.fn(),
    lineTo: vi.fn(),
    quadraticCurveTo: vi.fn(),
    arc: vi.fn(),
    fill: vi.fn(),
    ellipse: vi.fn(),
    stroke: vi.fn(),
    strokeRect: vi.fn(),
  } as unknown as CanvasRenderingContext2D);
  return { frames, cancel, disconnect, draw };
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("Particle field lifecycle", () => {
  it.each([
    { paused: true, reduced: false },
    { paused: false, reduced: true },
  ])("draws once without an ambient loop for %j", ({ paused, reduced }) => {
    const { frames, draw } = setup(reduced);
    render(
      <div data-journey>
        <ParticleField theme="night" paused={paused} />
      </div>,
    );
    frames[0](16);
    expect(draw).toHaveBeenCalled();
    expect(frames).toHaveLength(1);
  });

  it("cancels the animation and disconnects observation on unmount", () => {
    const { frames, cancel, disconnect } = setup();
    const { unmount } = render(
      <div data-journey>
        <ParticleField theme="day" paused={false} />
      </div>,
    );
    frames[0](40);
    expect(frames).toHaveLength(2);
    unmount();
    expect(cancel).toHaveBeenCalledWith(2);
    expect(disconnect).toHaveBeenCalled();
  });
});

describe("Scroll holds", () => {
  it("holds each formation still before morphing to the next", () => {
    expect(shapeProgress(0)).toBe(0);
    expect(shapeProgress(0.3)).toBe(0);
    expect(shapeProgress(1.2)).toBe(1);
    expect(shapeProgress(2.3)).toBe(2);
    expect(shapeProgress(3)).toBe(3);
  });

  it("eases through morph windows between holds", () => {
    const midPhoneWave = shapeProgress(0.81);
    expect(midPhoneWave).toBeGreaterThan(0);
    expect(midPhoneWave).toBeLessThan(1);
    const midCalendarTarget = shapeProgress(2.81);
    expect(midCalendarTarget).toBeGreaterThan(2);
    expect(midCalendarTarget).toBeLessThan(3);
  });
});
