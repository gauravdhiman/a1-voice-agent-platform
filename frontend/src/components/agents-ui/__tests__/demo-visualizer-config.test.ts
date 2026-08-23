import { describe, expect, it } from "vitest";

import { resolveDemoVisualizer } from "../demo-visualizer-config";

describe("resolveDemoVisualizer", () => {
  it("defaults the public demo to radial", () => {
    expect(resolveDemoVisualizer(null)).toBe("radial");
    expect(resolveDemoVisualizer(undefined)).toBe("radial");
    expect(resolveDemoVisualizer("")).toBe("radial");
  });

  it("keeps only the two finalized visualizer choices", () => {
    expect(resolveDemoVisualizer("radial")).toBe("radial");
    expect(resolveDemoVisualizer("lk-bars")).toBe("lk-bars");
    expect(resolveDemoVisualizer("radial-v4")).toBe("radial");
    expect(resolveDemoVisualizer("livekit-v4")).toBe("radial");
    expect(resolveDemoVisualizer("livekit-v5")).toBe("radial");
    expect(resolveDemoVisualizer("audiomotion")).toBe("radial");
  });
});
