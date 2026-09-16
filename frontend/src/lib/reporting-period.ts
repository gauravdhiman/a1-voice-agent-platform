export type ReportingPeriod =
  | "today"
  | "yesterday"
  | "last_7_days"
  | "last_15_days"
  | "last_30_days";

export interface ReportingPeriodOption {
  value: ReportingPeriod;
  label: string;
}

export interface ReportingDateWindow {
  from: string;
  toExclusive: string;
}

export const REPORTING_PERIOD_OPTIONS: ReportingPeriodOption[] = [
  { value: "today", label: "Today" },
  { value: "yesterday", label: "Yesterday" },
  { value: "last_7_days", label: "Last 7 days" },
  { value: "last_15_days", label: "Last 15 days" },
  { value: "last_30_days", label: "Last 30 days" },
];

const ROLLING_PERIOD_DAYS: Partial<Record<ReportingPeriod, number>> = {
  last_7_days: 7,
  last_15_days: 15,
  last_30_days: 30,
};

const MILLISECONDS_PER_DAY = 24 * 60 * 60 * 1000;

/** Return the human-readable label used by dashboard period captions. */
export function getReportingPeriodLabel(period: ReportingPeriod): string {
  return (
    REPORTING_PERIOD_OPTIONS.find((option) => option.value === period)?.label ??
    "Last 30 days"
  );
}

/** Format an ISO date-only analytics key without shifting it to local time. */
export function formatReportingDateLabel(value: string): string {
  const date = new Date(value + "T12:00:00Z");
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeZone: "UTC",
  }).format(date);
}

/** Return the rolling day count, or null for a calendar-day period. */
export function getRollingPeriodDays(period: ReportingPeriod): number | null {
  return ROLLING_PERIOD_DAYS[period] ?? null;
}

/**
 * Build the UTC query window shared by the workspace call list and analytics.
 * Calendar-day boundaries follow the organization's IANA timezone, including
 * daylight-saving changes; rolling ranges retain their exact 24-hour windows.
 */
export function getReportingDateWindow(
  period: ReportingPeriod,
  timeZone: string,
  now: Date = new Date(),
): ReportingDateWindow {
  const to = now.toISOString();

  if (period === "today" || period === "yesterday") {
    const todayKey = localDateKey(now, timeZone);
    const todayStart = startOfLocalDate(todayKey, timeZone, now);
    const from =
      period === "today"
        ? todayStart
        : startOfLocalDate(shiftDateKey(todayKey, -1), timeZone, todayStart);
    return {
      from: from.toISOString(),
      toExclusive: period === "today" ? to : todayStart.toISOString(),
    };
  }

  const days = ROLLING_PERIOD_DAYS[period] ?? 30;
  return {
    from: new Date(now.getTime() - days * MILLISECONDS_PER_DAY).toISOString(),
    toExclusive: to,
  };
}

function localDateKey(date: Date, timeZone: string): string {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(date);
  const values = new Map(parts.map((part) => [part.type, part.value]));
  return `${values.get("year")}-${values.get("month")}-${values.get("day")}`;
}

function shiftDateKey(dateKey: string, offsetDays: number): string {
  const [year, month, day] = dateKey.split("-").map(Number);
  const shifted = new Date(Date.UTC(year, month - 1, day + offsetDays));
  return [
    String(shifted.getUTCFullYear()).padStart(4, "0"),
    String(shifted.getUTCMonth() + 1).padStart(2, "0"),
    String(shifted.getUTCDate()).padStart(2, "0"),
  ].join("-");
}

function startOfLocalDate(dateKey: string, timeZone: string, before: Date): Date {
  const maximumSearchDays = 370;
  let low = before.getTime() - 4 * MILLISECONDS_PER_DAY;
  let high = before.getTime();

  while (localDateKey(new Date(low), timeZone) >= dateKey) {
    low -= 4 * MILLISECONDS_PER_DAY;
    if (before.getTime() - low > maximumSearchDays * MILLISECONDS_PER_DAY) {
      throw new RangeError(`Unable to find the start of ${dateKey} in ${timeZone}`);
    }
  }

  while (localDateKey(new Date(high), timeZone) < dateKey) {
    high += 4 * MILLISECONDS_PER_DAY;
    if (high - before.getTime() > maximumSearchDays * MILLISECONDS_PER_DAY) {
      throw new RangeError(`Unable to find the start of ${dateKey} in ${timeZone}`);
    }
  }

  while (high - low > 1) {
    const midpoint = Math.floor((low + high) / 2);
    if (localDateKey(new Date(midpoint), timeZone) < dateKey) {
      low = midpoint;
    } else {
      high = midpoint;
    }
  }

  return new Date(high);
}
