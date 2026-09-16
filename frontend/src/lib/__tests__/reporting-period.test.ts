import { describe, expect, it } from "vitest";
import {
  getReportingDateWindow,
  getReportingPeriodLabel,
  getRollingPeriodDays,
  REPORTING_PERIOD_OPTIONS,
} from "@/lib/reporting-period";

describe("reporting periods", () => {
  it("offers the dashboard periods in the requested order", () => {
    expect(REPORTING_PERIOD_OPTIONS.map(({ label }) => label)).toEqual([
      "Today",
      "Yesterday",
      "Last 7 days",
      "Last 15 days",
      "Last 30 days",
    ]);
    expect(getReportingPeriodLabel("yesterday")).toBe("Yesterday");
    expect(getRollingPeriodDays("last_15_days")).toBe(15);
    expect(getRollingPeriodDays("today")).toBeNull();
  });

  it("uses the selected workspace timezone for today's boundary", () => {
    const now = new Date("2025-03-09T12:30:00.000Z");

    expect(getReportingDateWindow("today", "America/Phoenix", now)).toEqual({
      from: "2025-03-09T07:00:00.000Z",
      toExclusive: "2025-03-09T12:30:00.000Z",
    });
  });

  it("uses the actual 23-hour local day across a daylight-saving change", () => {
    const now = new Date("2025-03-10T12:00:00.000Z");

    expect(getReportingDateWindow("yesterday", "America/New_York", now)).toEqual(
      {
        from: "2025-03-09T05:00:00.000Z",
        toExclusive: "2025-03-10T04:00:00.000Z",
      },
    );
  });

  it("keeps the existing rolling windows exact for 7, 15, and 30 days", () => {
    const now = new Date("2026-09-16T12:00:00.000Z");

    expect(getReportingDateWindow("last_7_days", "UTC", now)).toEqual({
      from: "2026-09-09T12:00:00.000Z",
      toExclusive: "2026-09-16T12:00:00.000Z",
    });
    expect(getReportingDateWindow("last_15_days", "UTC", now).from).toBe(
      "2026-09-01T12:00:00.000Z",
    );
    expect(getReportingDateWindow("last_30_days", "UTC", now).from).toBe(
      "2026-08-17T12:00:00.000Z",
    );
  });
});
