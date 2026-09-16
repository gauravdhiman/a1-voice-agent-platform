"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Activity, ArrowUpRight, CheckCircle2, Clock3, Phone, RefreshCw, Users } from "lucide-react";
import { useAuth } from "@/contexts/auth-context";
import { callLogService, type CallAnalytics } from "@/services/call-log-service";
import {
  formatReportingDateLabel,
  getReportingPeriodLabel,
  REPORTING_PERIOD_OPTIONS,
} from "@/lib/reporting-period";
import type { ReportingPeriod } from "@/lib/reporting-period";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  InteractiveChart,
  uniformBandIndexAtProgress,
  uniformBandPositionForIndex,
  weightedIndexAtProgress,
  weightedPositionForIndex,
} from "@/components/charts/interactive-chart";

const number = new Intl.NumberFormat();
const UNSUCCESSFUL_STATUSES = new Set([
  "failed", "busy", "missed", "no-answer", "no_answer", "canceled", "cancelled",
]);
const STATUS_COLORS: Record<string, string> = {
  completed: "bg-emerald-500",
  failed: "bg-rose-500",
  canceled: "bg-rose-500",
  cancelled: "bg-rose-500",
  busy: "bg-amber-500",
  missed: "bg-amber-500",
  "no-answer": "bg-amber-500",
  no_answer: "bg-amber-500",
};

function formatStatus(status: string): string {
  return status.replaceAll("_", " ").replaceAll("-", " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

function Unavailable({ retry }: { retry: () => void }) {
  return (
    <div role="alert" className="flex flex-wrap items-center gap-3 py-4 text-sm text-muted-foreground">
      <span>Platform analytics could not be loaded.</span>
      <Button variant="outline" size="sm" onClick={retry}>Try again</Button>
    </div>
  );
}

function Metric({ label, value, detail, icon: Icon }: {
  label: string;
  value: string;
  detail: string;
  icon: typeof Phone;
}) {
  return (
    <div className="min-w-0 rounded-lg bg-muted/35 p-4">
      <dt className="flex items-center gap-2 text-sm text-muted-foreground">
        <Icon aria-hidden="true" className="h-4 w-4 text-primary" />{label}
      </dt>
      <dd className="mt-3 text-2xl font-semibold tabular-nums tracking-tight">{value}</dd>
      <p className="mt-1 text-xs text-muted-foreground">{detail}</p>
    </div>
  );
}

function VolumeChart({
  data,
  period,
}: {
  data: CallAnalytics;
  period: ReportingPeriod;
}) {
  const points = data.calls_by_day;
  const maximum = Math.max(...points.map((point) => point.calls), 1);
  const total = points.reduce((sum, point) => sum + point.calls, 0);
  const polyline = points
    .map((point, index) => {
      const x = points.length < 2 ? 50 : (index / (points.length - 1)) * 100;
      return String(x) + "," + String(88 - (point.calls / maximum) * 68);
    })
    .join(" ");

  return (
    <section className="rounded-xl border bg-card p-5 sm:p-6">
      <div>
        <h2 className="font-semibold">Platform call volume</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          {getReportingPeriodLabel(period)} · {number.format(total)} calls · UTC
        </p>
      </div>
      {total === 0 ? (
        <p className="mt-6 flex h-28 items-center justify-center rounded-lg border border-dashed text-sm text-muted-foreground">
          No calls match these filters.
        </p>
      ) : (
        <>
          <InteractiveChart
            data={points}
            chartLabel="Platform daily call volume. Move the pointer or use the arrow keys to inspect each UTC date."
            label={(point) => formatReportingDateLabel(point.date)}
            value={(point) =>
              number.format(point.calls) +
              " " +
              (point.calls === 1 ? "call" : "calls")
            }
            className="mt-5 h-32"
          >
            {() => (
              <>
                <svg
                  role="img"
                  aria-label={
                    "Platform daily call volume, " +
                    number.format(total) +
                    " " +
                    (total === 1 ? "call" : "calls") +
                    " across " +
                    points.length +
                    " UTC calendar dates"
                  }
                  viewBox="0 0 100 100"
                  preserveAspectRatio="none"
                  className="block h-32 w-full overflow-visible"
                >
                  <line
                    x1="0"
                    y1="88"
                    x2="100"
                    y2="88"
                    stroke="currentColor"
                    className="text-border"
                    strokeDasharray="2 3"
                  />
                  <polyline
                    points={polyline}
                    fill="none"
                    stroke="currentColor"
                    className="text-primary"
                    strokeWidth="2"
                    vectorEffect="non-scaling-stroke"
                  />
                </svg>
                {points.map((point, index) => {
                  const x =
                    points.length < 2 ? 50 : (index / (points.length - 1)) * 100;
                  const y = 88 - (point.calls / maximum) * 68;
                  return (
                    <span
                      key={point.date}
                      aria-hidden="true"
                      data-chart-marker
                      className="pointer-events-none absolute z-[11] h-1.5 w-1.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-primary"
                      style={{ left: `${x}%`, top: `${y}%` }}
                    />
                  );
                })}
              </>
            )}
          </InteractiveChart>
          <div className="mt-2 flex justify-between text-xs text-muted-foreground">
            <span>{points[0]?.date}</span>
            <span>{number.format(maximum)} max/day</span>
            <span>{points.at(-1)?.date}</span>
          </div>
        </>
      )}
    </section>
  );
}

function formatHourRange(hour: number): string {
  const start = String(hour).padStart(2, "0");
  const end = String((hour + 1) % 24).padStart(2, "0");
  return start + ":00–" + end + ":00";
}

function PeakHours({ data }: { data: CallAnalytics }) {
  const peak = data.calls_by_hour.reduce(
    (best, hour) => hour.calls > best.calls ? hour : best,
    { hour: 0, calls: 0 },
  );
  const maximum = Math.max(...data.calls_by_hour.map((hour) => hour.calls), 1);
  const peakLabel = formatHourRange(peak.hour);

  return (
    <section className="rounded-xl border bg-card p-5 sm:p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="font-semibold">Peak call hours</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {peak.calls ? "Busiest: " + peakLabel : "No calls in this period"}
          </p>
        </div>
        <Clock3 aria-hidden="true" className="h-5 w-5 text-primary" />
      </div>
      <InteractiveChart
        data={data.calls_by_hour}
        chartLabel="Calls by hour in UTC. Move the pointer or use the arrow keys to inspect each hour."
        label={(hour) => formatHourRange(hour.hour)}
        value={(hour) =>
          number.format(hour.calls) + " " + (hour.calls === 1 ? "call" : "calls")
        }
        getIndexForProgress={(progress, hours) =>
          uniformBandIndexAtProgress(progress, hours.length)
        }
        getPositionForIndex={(index, hours) =>
          uniformBandPositionForIndex(index, hours.length)
        }
        className="mt-6 h-24"
      >
        {({ activeIndex }) => (
          <div className="flex h-full items-end gap-[3px]">
            {data.calls_by_hour.map((hour, index) => (
              <div
                key={hour.hour}
                aria-hidden="true"
                className={cn("flex-1 rounded-t-sm",
                  activeIndex === index ||
                  (activeIndex === null && hour.hour === peak.hour && peak.calls)
                    ? "bg-primary"
                    : "bg-primary/25",
                )}
                style={{
                  height: `${Math.max(hour.calls ? 10 : 3, (hour.calls / maximum) * 88)}%`,
                }}
              />
            ))}
          </div>
        )}
      </InteractiveChart>
      <div className="mt-2 flex justify-between text-xs text-muted-foreground">
        <span>12 am</span><span>6 am</span><span>12 pm</span><span>6 pm</span><span>12 am</span>
      </div>
      <p className="mt-3 text-xs text-muted-foreground">UTC · all organizations</p>
    </section>
  );
}

/** Shows cross-organization call aggregates to platform administrators. */
export default function PlatformDashboardPage() {
  const { user } = useAuth();
  const platformAdmin = Boolean(user?.hasRole("platform_admin"));
  const [period, setPeriod] = useState<ReportingPeriod>("last_30_days");
  const [status, setStatus] = useState("");
  const query = useQuery({
    queryKey: ["platform-call-analytics", user?.id, period, status],
    queryFn: () => callLogService.getPlatformAnalytics(period, status || undefined),
    enabled: Boolean(user && platformAdmin),
    staleTime: 60_000,
  });
  const data = query.data;
  const statusCounts = data?.calls_by_status ?? [];
  const statusWeights = statusCounts.map((item) => item.count);
  const completed = statusCounts.find((item) => item.status === "completed")?.count ?? 0;
  const unsuccessful = statusCounts.filter((item) => UNSUCCESSFUL_STATUSES.has(item.status)).reduce((sum, item) => sum + item.count, 0);
  const completionRate = data?.selected_total_calls ? Math.round((completed / data.selected_total_calls) * 100) : null;

  if (!platformAdmin) {
    return (
      <main className="mx-auto max-w-4xl rounded-xl border bg-card p-8">
        <h1 className="text-2xl font-semibold">Platform overview</h1>
        <p role="alert" className="mt-2 text-sm text-muted-foreground">Only platform administrators can view cross-organization analytics.</p>
      </main>
    );
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 pb-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary">Platform administration</p>
          <h1 className="mt-1 text-3xl font-semibold tracking-tight">Platform overview</h1>
          <p className="mt-1 text-sm text-muted-foreground">Cross-organization voice activity. Workspace dashboards remain scoped to the selected organization.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Link className="text-sm underline" href="/dashboard">Selected workspace</Link>
          <Button variant="outline" size="sm" onClick={() => void query.refetch()} disabled={query.isFetching}>
            <RefreshCw className={cn("mr-2 h-4 w-4", query.isFetching && "animate-spin")} />Refresh
          </Button>
        </div>
      </header>

      <section aria-label="Platform call performance" className="rounded-xl border bg-card p-5 sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-5">
          <div><p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">All organizations</p><p className="mt-1 text-sm text-muted-foreground">Platform totals and demand patterns, in UTC</p></div>
          <div className="flex flex-wrap gap-2">
            <label className="sr-only" htmlFor="platform-period">Platform reporting period</label>
            <select id="platform-period" aria-label="Platform reporting period" value={period} onChange={(event) => setPeriod(event.target.value as ReportingPeriod)} className="h-9 rounded-md border border-input bg-background px-3 text-sm">{REPORTING_PERIOD_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select>
            <label className="sr-only" htmlFor="platform-status">Platform call status filter</label>
            <select id="platform-status" aria-label="Platform call status filter" value={status} onChange={(event) => setStatus(event.target.value)} className="h-9 min-w-40 rounded-md border border-input bg-background px-3 text-sm"><option value="">All call statuses</option>{(data?.available_statuses ?? []).map((item) => <option key={item} value={item}>{formatStatus(item)}</option>)}</select>
          </div>
        </div>
        {query.isError ? <Unavailable retry={() => void query.refetch()} /> : !data ? <p role="status" className="py-10 text-center text-sm text-muted-foreground">Loading platform call metrics…</p> : (
          <>
            <dl className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <Metric label="Calls" value={number.format(data.selected_total_calls)} detail={getReportingPeriodLabel(period) + (status ? " · " + formatStatus(status) : " · all statuses")} icon={Phone} />
              <Metric label="Completed" value={number.format(completed)} detail={status ? "Within selected status" : completionRate == null ? "No calls match these filters" : String(completionRate) + "% of matching calls"} icon={CheckCircle2} />
              <Metric label="Unsuccessful" value={number.format(unsuccessful)} detail="Failed, unanswered, busy or canceled outcomes" icon={Activity} />
              <Metric label="Organizations with calls" value={number.format(data.selected_active_organizations)} detail={getReportingPeriodLabel(period) + (status ? " · " + formatStatus(status) : " · all statuses") + " · not a paying-customer count"} icon={Users} />
            </dl>
            <p className="mt-4 text-right text-xs text-muted-foreground">Platform aggregates · UTC · Updated {new Date(query.dataUpdatedAt).toLocaleTimeString()}</p>
          </>
        )}
      </section>

      {data && !query.isError && (
        <div className="grid items-start gap-4 xl:grid-cols-12">
          <div className="xl:col-span-8"><VolumeChart data={data} period={period} /></div>
          <div className="xl:col-span-4"><PeakHours data={data} /></div>
          <section className="rounded-xl border bg-card p-5 sm:p-6 xl:col-span-5">
            <div className="flex items-start justify-between gap-4"><div><h2 className="font-semibold">Call outcomes</h2><p className="mt-1 text-sm text-muted-foreground">Filtered status mix across the platform</p></div><CheckCircle2 aria-hidden="true" className="h-5 w-5 text-primary" /></div>
            {data.selected_total_calls === 0 ? <p className="mt-5 rounded-lg border border-dashed p-4 text-sm text-muted-foreground">No calls match these filters.</p> : (
              <>
                <InteractiveChart
                  data={statusCounts}
                  chartLabel="Platform call outcomes by status. Move the pointer or use the arrow keys to inspect each status."
                  label={(item) => formatStatus(item.status)}
                  value={(item) =>
                    number.format(item.count) +
                    " " +
                    (item.count === 1 ? "call" : "calls")
                  }
                  getIndexForProgress={(progress) =>
                    weightedIndexAtProgress(progress, statusWeights)
                  }
                  getPositionForIndex={(index) =>
                    weightedPositionForIndex(index, statusWeights)
                  }
                  className="mt-5 h-14"
                >
                  {() => (
                    <div
                      aria-hidden="true"
                      className="absolute inset-x-0 bottom-0 flex h-3 overflow-hidden rounded-full bg-muted"
                    >
                      {statusCounts.map((item) => (
                        <span
                          key={item.status}
                          className={STATUS_COLORS[item.status] ?? "bg-sky-500"}
                          style={{
                            width: String(
                              (item.count / data.selected_total_calls) * 100,
                            ) + "%",
                          }}
                        />
                      ))}
                    </div>
                  )}
                </InteractiveChart>
                <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-3">{statusCounts.map((item) => <div key={item.status} className="flex items-center gap-2 text-sm"><span aria-hidden="true" className={cn("h-2.5 w-2.5 shrink-0 rounded-full", STATUS_COLORS[item.status] ?? "bg-sky-500")} /><dt className="min-w-0 truncate text-muted-foreground">{formatStatus(item.status)}</dt><dd className="ml-auto tabular-nums">{number.format(item.count)}</dd></div>)}</dl>
              </>
            )}
          </section>
          <section className="rounded-xl border bg-card p-5 sm:p-6 xl:col-span-7">
            <h2 className="font-semibold">Platform operations</h2><p className="mt-1 text-sm text-muted-foreground">Move from aggregate activity to organization-level administration.</p>
            <div className="mt-4 flex flex-wrap gap-4 text-sm"><Link className="inline-flex items-center gap-1 underline" href="/organizations">Organizations <ArrowUpRight className="h-4 w-4" /></Link><Link className="inline-flex items-center gap-1 underline" href="/organizations/credits">Credit management <ArrowUpRight className="h-4 w-4" /></Link><Link className="inline-flex items-center gap-1 underline" href="/platform/phone-numbers">Phone number settings <ArrowUpRight className="h-4 w-4" /></Link></div>
          </section>
        </div>
      )}
    </div>
  );
}
