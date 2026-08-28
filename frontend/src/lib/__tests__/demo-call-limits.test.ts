import { describe, expect, it } from "vitest";

import {
  formatDemoCallsRemaining,
  formatDemoDuration,
  isDemoCallLimitReached,
} from "@/lib/demo-call-limits";

describe("demo call limit helpers", () => {
  it("recognizes only zero as exhausted", () => {
    expect(isDemoCallLimitReached(0)).toBe(true);
    expect(isDemoCallLimitReached(-1)).toBe(false);
    expect(isDemoCallLimitReached(undefined)).toBe(false);
  });

  it("formats unlimited and finite call budgets", () => {
    expect(formatDemoCallsRemaining(-1)).toBe("Unlimited trial calls");
    expect(formatDemoCallsRemaining(0)).toBe("No trial calls remaining");
    expect(formatDemoCallsRemaining(1)).toBe("1 trial call remaining");
    expect(formatDemoCallsRemaining(3)).toBe("3 trial calls remaining");
    expect(formatDemoCallsRemaining(null)).toBeNull();
  });

  it("formats unlimited, minute, mixed, and invalid durations", () => {
    expect(formatDemoDuration(-1)).toBe("No maximum call duration");
    expect(formatDemoDuration(600)).toBe("Maximum 10 minutes per call");
    expect(formatDemoDuration(90)).toBe("Maximum 1m 30s per call");
    expect(formatDemoDuration(30)).toBe("Maximum 30 seconds per call");
    expect(formatDemoDuration(0)).toBeNull();
    expect(formatDemoDuration(undefined)).toBeNull();
  });
});
