"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  ArrowUpRight,
  Bot,
  CheckCircle2,
  Clock3,
  Phone,
  RefreshCw,
  Users,
} from "lucide-react";
import { useAuth } from "@/contexts/auth-context";
import { useOrganization } from "@/contexts/organization-context";
import { useUserPermissions } from "@/hooks/use-user-permissions";
import { useEscalations } from "@/hooks/use-escalations";
import { useCallLogs } from "@/hooks/use-call-logs";
import {
  callLogService,
  type CallAnalytics,
  type CallLog,
} from "@/services/call-log-service";
import {
  formatReportingDateLabel,
  getReportingDateWindow,
  getReportingPeriodLabel,
  REPORTING_PERIOD_OPTIONS,
} from "@/lib/reporting-period";
import type { ReportingPeriod } from "@/lib/reporting-period";
import { agentService } from "@/services/agent-service";
import { billingService } from "@/services/billing-service";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  InteractiveChart,
  uniformBandIndexAtProgress,
  uniformBandPositionForIndex,
  weightedIndexAtProgress,
  weightedPositionForIndex,
} from "@/components/charts/interactive-chart";
import type { OrganizationAgentSummary } from "@/types/agent";

const number = new Intl.NumberFormat();
const UNSUCCESSFUL_STATUSES = new Set([
  "failed",
  "busy",
  "missed",
  "no-answer",
  "no_answer",
  "canceled",
  "cancelled",
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

interface MetricProps {
  label: string;
  value: string;
  detail: string;
  icon: typeof Phone;
}

interface RecentCallsProps {
  orgId: string;
  period: ReportingPeriod;
  status?: string;
  dateFrom: string;
  dateToExclusive: string;
  timezone: string;
  analytics?: CallAnalytics;
}

interface AgentSnapshotProps {
  orgId: string;
  period: ReportingPeriod;
  status?: string;
  canManage: boolean;
  timezone: string;
  data?: CallAnalytics;
}

interface DashboardFiltersProps {
  period: ReportingPeriod;
  status: string;
  statusOptions: string[];
  onPeriodChange: (period: ReportingPeriod) => void;
  onStatusChange: (status: string) => void;
}

function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null) return "—";
  const minutes = Math.floor(seconds / 60);
  const remainder = Math.round(seconds % 60);
  return minutes ? `${minutes}m ${remainder}s` : `${remainder}s`;
}

function formatStatus(status: string): string {
  return status
    .replaceAll("_", " ")
    .replaceAll("-", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function formatTimestamp(value: string, timezone: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Unknown time";
  try {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
      timeZone: timezone,
    }).format(date);
  } catch {
    return date.toLocaleString();
  }
}

/** A small, accessible metric row for the selected workspace. */
function Metric({ label, value, detail, icon: Icon }: MetricProps) {
  return (
    <div className="min-w-0 rounded-lg bg-muted/35 p-4">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Icon aria-hidden="true" className="h-4 w-4 text-primary" />
        <dt>{label}</dt>
      </div>
      <dd className="mt-3 text-2xl font-semibold tabular-nums tracking-tight">
        {value}
      </dd>
      <p className="mt-1 text-xs text-muted-foreground">{detail}</p>
    </div>
  );
}

function Unavailable({ retry }: { retry: () => void }) {
  return (
    <div
      role="alert"
      className="flex flex-wrap items-center gap-3 py-4 text-sm text-muted-foreground"
    >
      <span>This data could not be loaded.</span>
      <Button variant="outline" size="sm" onClick={retry}>
        Try again
      </Button>
    </div>
  );
}

/** Keep the shared call filters visible at the page level so their scope is clear. */
function DashboardFilters({
  period,
  status,
  statusOptions,
  onPeriodChange,
  onStatusChange,
}: DashboardFiltersProps) {
  return (
    <section
      aria-label="Dashboard filters"
      className="rounded-xl border bg-card px-4 py-3 sm:px-5"
    >
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-sm font-semibold">Dashboard filters</p>
          <p className="mt-1 text-xs text-muted-foreground">
            Filters this workspace’s call analytics. Platform pulse, follow-ups
            and credits keep their own scope.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <label className="sr-only" htmlFor="dashboard-period">
            Call reporting period
          </label>
          <select
            id="dashboard-period"
            aria-label="Call reporting period"
            value={period}
            onChange={(event) =>
              onPeriodChange(event.target.value as ReportingPeriod)
            }
            className="h-9 rounded-md border border-input bg-background px-3 text-sm"
          >
            {REPORTING_PERIOD_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <label className="sr-only" htmlFor="dashboard-status">
            Call status filter
          </label>
          <select
            id="dashboard-status"
            aria-label="Call status filter"
            value={status}
            onChange={(event) => onStatusChange(event.target.value)}
            className="h-9 min-w-40 rounded-md border border-input bg-background px-3 text-sm"
          >
            <option value="">All call statuses</option>
            {statusOptions.map((option) => (
              <option key={option} value={option}>
                {formatStatus(option)}
              </option>
            ))}
          </select>
        </div>
      </div>
    </section>
  );
}

/** Give admins a compact platform pulse while all workspace data stays scoped. */
function PlatformPulse({ userId }: { userId: string }) {
  const query = useQuery({
    queryKey: ["platform-call-analytics", userId, 30, ""],
    queryFn: () => callLogService.getPlatformAnalytics(),
    staleTime: 60_000,
  });

  return (
    <section className="min-w-0 rounded-xl border border-primary/20 bg-primary/[0.035] px-5 py-4">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-primary">
            Platform pulse
          </p>
          <p className="mt-1 text-sm text-muted-foreground">
            Aggregate activity across organizations · last 30 days
          </p>
        </div>
        {query.isError ? (
          <Unavailable retry={() => void query.refetch()} />
        ) : !query.data ? (
          <p role="status" className="text-sm text-muted-foreground">
            Loading platform pulse…
          </p>
        ) : (
          <dl className="flex flex-wrap gap-x-8 gap-y-3">
            <div>
              <dt className="text-xs text-muted-foreground">Calls</dt>
              <dd className="text-lg font-semibold tabular-nums">
                {number.format(query.data.total_calls_month)}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">
                Organizations with calls
              </dt>
              <dd className="text-lg font-semibold tabular-nums">
                {number.format(query.data.active_organizations)}
              </dd>
            </div>
          </dl>
        )}
        <Link
          className="inline-flex items-center gap-1 text-sm underline"
          href="/platform/dashboard"
        >
          View platform overview <ArrowUpRight className="h-4 w-4" />
        </Link>
      </div>
    </section>
  );
}

/** Render daily call volume with pointer and keyboard selection. */

function CallVolume({
  data,
  period,
}: {
  data: CallAnalytics;
  period: ReportingPeriod;
}) {
  const points = data.calls_by_day;
  const max = Math.max(...points.map((point) => point.calls), 1);
  const total = points.reduce((sum, point) => sum + point.calls, 0);
  const polyline = points
    .map((point, index) => {
      const x = points.length === 1 ? 50 : (index / (points.length - 1)) * 100;
      const y = 88 - (point.calls / max) * 68;
      return x + "," + y;
    })
    .join(" ");

  return (
    <section className="flex h-full min-w-0 flex-col rounded-xl border bg-card p-5 sm:p-6">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h2 className="font-semibold">Call volume</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {getReportingPeriodLabel(period)} · {number.format(total)}{" "}
            {total === 1 ? "call" : "calls"}
          </p>
        </div>
        <Activity aria-hidden="true" className="h-5 w-5 text-primary" />
      </div>
      {total === 0 ? (
        <p className="mt-7 flex h-28 items-center justify-center rounded-lg border border-dashed text-sm text-muted-foreground">
          No calls match these filters.
        </p>
      ) : (
        <>
          <InteractiveChart
            data={points}
            chartLabel="Daily call volume chart. Move the pointer or use the arrow keys to inspect each day."
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
                    "Daily call volume, " +
                    number.format(total) +
                    " " +
                    (total === 1 ? "call" : "calls") +
                    " across " +
                    points.length +
                    " local calendar days"
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
                    points.length === 1
                      ? 50
                      : (index / (points.length - 1)) * 100;
                  const y = 88 - (point.calls / max) * 68;
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
            <span>Local dates · {number.format(max)} max/day</span>
            <span>{points.at(-1)?.date}</span>
          </div>
        </>
      )}
    </section>
  );
}

/** Show when callers contact the selected workspace, in its business timezone. */
function formatHourRange(hour: number): string {
  const start = String(hour).padStart(2, "0");
  const end = String((hour + 1) % 24).padStart(2, "0");
  return start + ":00–" + end + ":00";
}

function PeakHours({
  data,
  timezone,
}: {
  data: CallAnalytics;
  timezone: string;
}) {
  const peak = data.calls_by_hour.reduce(
    (best, hour) => (hour.calls > best.calls ? hour : best),
    { hour: 0, calls: 0 },
  );
  const max = Math.max(...data.calls_by_hour.map((hour) => hour.calls), 1);
  const label = formatHourRange(peak.hour);

  return (
    <section className="flex h-full flex-col rounded-xl border bg-card p-5 sm:p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="font-semibold">Peak call hours</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {peak.calls ? "Busiest: " + label : "No calls in this period"}
          </p>
        </div>
        <Clock3 aria-hidden="true" className="h-5 w-5 text-primary" />
      </div>
      <InteractiveChart
        data={data.calls_by_hour}
        chartLabel={`Calls by hour in ${timezone}. Move the pointer or use the arrow keys to inspect each hour.`}
        label={(hour) => formatHourRange(hour.hour)}
        value={(hour) =>
          number.format(hour.calls) +
          " " +
          (hour.calls === 1 ? "call" : "calls")
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
                className={cn(
                  "flex-1 rounded-t-sm",
                  activeIndex === index ||
                    (activeIndex === null &&
                      hour.hour === peak.hour &&
                      peak.calls)
                    ? "bg-primary"
                    : "bg-primary/25",
                )}
                style={{
                  height: `${Math.max(hour.calls ? 10 : 3, (hour.calls / max) * 88)}%`,
                }}
              />
            ))}
          </div>
        )}
      </InteractiveChart>
      <div className="mt-2 flex justify-between text-xs text-muted-foreground">
        <span>12 am</span>
        <span>6 am</span>
        <span>12 pm</span>
        <span>6 pm</span>
        <span>12 am</span>
      </div>
      <p className="mt-3 text-xs text-muted-foreground">
        Local time · {timezone}
      </p>
    </section>
  );
}

/** Report the selected organization's agent capacity and recent performance. */
function AgentSnapshot({
  orgId,
  period,
  status,
  canManage,
  timezone,
  data,
}: AgentSnapshotProps) {
  const summary = useQuery({
    queryKey: ["organization-agent-summary", orgId],
    queryFn: () => agentService.getOrganizationAgentSummary(orgId),
    staleTime: 60_000,
  });
  const stats = data?.calls_by_agent ?? [];
  const agentsSummary: OrganizationAgentSummary | undefined = summary.data;

  return (
    <section className="flex h-full flex-col rounded-xl border bg-card p-5 sm:p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="font-semibold">Agent activity</h2>
          {summary.isError ? (
            <p className="mt-1 text-sm text-muted-foreground">
              Agent capacity unavailable
            </p>
          ) : !agentsSummary ? (
            <p role="status" className="mt-1 text-sm text-muted-foreground">
              Loading agent capacity…
            </p>
          ) : (
            <p className="mt-1 text-sm text-muted-foreground">
              {agentsSummary.active_agents} active of{" "}
              {agentsSummary.total_agents} configured ·{" "}
              {getReportingPeriodLabel(period)}
              {status ? ` · ${formatStatus(status)}` : ""}
            </p>
          )}
        </div>
        <Bot aria-hidden="true" className="h-5 w-5 shrink-0 text-primary" />
      </div>
      {summary.isError && (
        <div className="mt-4">
          <Unavailable retry={() => void summary.refetch()} />
        </div>
      )}
      {data && stats.length === 0 ? (
        <div className="mt-5 rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
          {agentsSummary?.total_agents === 0
            ? "No agents are configured for this workspace."
            : "No agent calls match these filters. Active agents are ready for new calls."}
        </div>
      ) : (
        data && (
          <ol className="mt-4 divide-y">
            {stats.slice(0, 5).map((agent) => (
              <li key={agent.agent_id} className="py-3 first:pt-0 last:pb-0">
                <div className="flex items-center justify-between gap-3">
                  <span className="min-w-0 truncate text-sm font-medium">
                    {agent.agent_id ? agent.agent_name : "Unassigned calls"}
                  </span>
                  <span className="shrink-0 text-sm tabular-nums">
                    {number.format(agent.count)} calls
                  </span>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  {(!status || status === "completed") &&
                    `Avg. completed call ${formatDuration(agent.avg_duration_seconds)}`}
                  {agent.last_call_at
                    ? `${!status || status === "completed" ? " · " : ""}Last ${formatStatus(agent.last_call_status ?? "unknown")} ${formatTimestamp(agent.last_call_at, timezone)}`
                    : ""}
                </p>
              </li>
            ))}
          </ol>
        )
      )}
      <div className="mt-auto flex flex-wrap gap-x-4 gap-y-2 border-t pt-4 text-sm">
        <Link
          className="inline-flex items-center gap-1 underline"
          href="/agents"
        >
          View agents <ArrowUpRight className="h-4 w-4" />
        </Link>
        {canManage && (
          <Link
            className="inline-flex items-center gap-1 underline"
            href="/agents/create"
          >
            Create agent <ArrowUpRight className="h-4 w-4" />
          </Link>
        )}
      </div>
    </section>
  );
}

/** Show real credit headroom to users allowed to manage workspace billing. */
function AccountCapacity({ orgId }: { orgId: string }) {
  const query = useQuery({
    queryKey: ["billing-summary", orgId],
    queryFn: () => billingService.getBillingSummary(orgId),
    staleTime: 60_000,
  });
  return (
    <section className="flex h-full min-w-0 flex-col rounded-xl border bg-card p-5 sm:p-6">
      <div className="flex min-w-0 items-start justify-between gap-4">
        <div className="min-w-0">
          <h2 className="font-semibold">Account capacity</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Voice credit availability
          </p>
        </div>
        <Users aria-hidden="true" className="h-5 w-5 shrink-0 text-primary" />
      </div>
      {query.isError ? (
        <Unavailable retry={() => void query.refetch()} />
      ) : !query.data ? (
        <p role="status" className="mt-4 text-sm text-muted-foreground">
          Loading account capacity…
        </p>
      ) : (
        <>
          <div className="mt-5 flex min-w-0 flex-wrap items-end justify-between gap-4">
            <div className="min-w-0">
              <p className="text-xs text-muted-foreground">Available credits</p>
              <p className="mt-1 break-words text-3xl font-semibold tabular-nums">
                {number.format(query.data.credit_balance)}
              </p>
            </div>
            <span className="max-w-full shrink-0 break-words rounded-full bg-muted px-3 py-1 text-xs capitalize">
              {query.data.subscription?.status.replaceAll("_", " ") ??
                "No subscription"}
            </span>
          </div>
          {query.data.credit_balance <= 0 && (
            <p className="mt-4 text-sm text-destructive">
              No credits remain. Review billing to keep calls available.
            </p>
          )}
          <Link
            className="mt-auto inline-flex items-center gap-1 pt-4 text-sm underline"
            href="/organization/billing"
          >
            Manage billing <ArrowUpRight className="h-4 w-4" />
          </Link>
        </>
      )}
    </section>
  );
}

/** Surface recent unanswered callback requests with a clear next step. */
function FollowUp({
  orgId,
  canManage,
  timezone,
}: {
  orgId: string;
  canManage: boolean;
  timezone: string;
}) {
  const query = useEscalations(orgId, "new");
  const requests = [...(query.data ?? [])].sort(
    (a, b) =>
      Number(b.urgency === "urgent") - Number(a.urgency === "urgent") ||
      b.created_at.localeCompare(a.created_at),
  );
  return (
    <section className="flex h-full min-w-0 flex-col rounded-xl border bg-card p-5 sm:p-6">
      <div className="flex min-w-0 items-start justify-between gap-4">
        <div className="min-w-0">
          <h2 className="font-semibold">Follow-up requests</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Latest new callbacks · urgent first
          </p>
        </div>
        <Phone aria-hidden="true" className="h-5 w-5 shrink-0 text-primary" />
      </div>
      {query.isError ? (
        <Unavailable retry={() => void query.refetch()} />
      ) : !query.data ? (
        <p role="status" className="mt-4 text-sm text-muted-foreground">
          Loading callbacks…
        </p>
      ) : requests.length === 0 ? (
        <p className="mt-5 rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
          No one is waiting for a callback.
        </p>
      ) : (
        <ul className="mt-3 divide-y">
          {requests.slice(0, 4).map((item) => (
            <li
              key={item.id}
              className="flex items-start justify-between gap-3 py-3 first:pt-0 last:pb-0"
            >
              <div className="min-w-0">
                <p className="line-clamp-2 text-sm">{item.reason}</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {item.caller_name || "Caller"} ·{" "}
                  {formatTimestamp(item.created_at, timezone)}
                </p>
              </div>
              {item.urgency === "urgent" && (
                <span className="shrink-0 rounded-full bg-rose-500/10 px-2 py-1 text-xs font-medium text-rose-600">
                  Urgent
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
      <Link
        className="mt-auto inline-flex shrink-0 items-center gap-1 pt-4 text-sm underline"
        href="/callbacks"
      >
        {canManage ? "Manage callbacks" : "View callback queue"}
        <ArrowUpRight className="h-4 w-4" />
      </Link>
    </section>
  );
}

/** Render recent filtered calls without exposing caller contact details. */
function RecentCalls({
  orgId,
  period,
  status,
  dateFrom,
  dateToExclusive,
  timezone,
  analytics,
}: RecentCallsProps) {
  const query = useCallLogs(orgId, {
    status,
    date_from: dateFrom,
    date_to_exclusive: dateToExclusive,
    page_size: 6,
  });
  const names = new Map(
    (analytics?.calls_by_agent ?? []).map((agent) => [
      agent.agent_id,
      agent.agent_name,
    ]),
  );
  return (
    <section className="min-w-0 rounded-xl border bg-card p-5 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="font-semibold">Recent calls</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {getReportingPeriodLabel(period)}
            {status ? ` · ${formatStatus(status)}` : " · all statuses"}
          </p>
        </div>
        <Link
          className="inline-flex shrink-0 items-center gap-1 text-sm underline"
          href="/calls"
        >
          Open call history <ArrowUpRight className="h-4 w-4" />
        </Link>
      </div>
      {query.isError ? (
        <Unavailable retry={() => void query.refetch()} />
      ) : !query.data ? (
        <p role="status" className="mt-4 text-sm text-muted-foreground">
          Loading calls…
        </p>
      ) : query.data.items.length === 0 ? (
        <p className="mt-5 rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
          No calls match these filters.
        </p>
      ) : (
        <div className="mt-4 min-w-0 w-full overflow-x-auto">
          <table className="w-full min-w-[460px] text-left text-sm">
            <thead>
              <tr className="border-b text-xs text-muted-foreground">
                <th className="pb-2 font-medium">When</th>
                <th className="pb-2 font-medium">Agent</th>
                <th className="pb-2 font-medium">Source</th>
                <th className="pb-2 font-medium">Status</th>
                <th className="pb-2 text-right font-medium">Duration</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {query.data.items.map((call: CallLog) => (
                <tr key={call.id}>
                  <td className="py-3 pr-3 whitespace-nowrap">
                    {formatTimestamp(call.created_at, timezone)}
                  </td>
                  <td className="max-w-40 truncate py-3 pr-3">
                    {call.agent_id
                      ? (names.get(call.agent_id) ?? "Agent")
                      : "Unassigned"}
                  </td>
                  <td className="py-3 pr-3 capitalize">
                    {call.source_type?.replaceAll("_", " ") ?? "Unknown"}
                  </td>
                  <td className="py-3 pr-3 capitalize">
                    {formatStatus(call.status)}
                  </td>
                  <td className="py-3 text-right tabular-nums">
                    {formatDuration(call.duration)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

/** Keep the workspace overview selected-org scoped for every role. */
export default function DashboardPage() {
  const { user } = useAuth();
  const { currentOrganization } = useOrganization();
  const permissions = useUserPermissions();
  const platformAdmin = Boolean(user?.hasRole("platform_admin"));
  const orgId = currentOrganization?.id ?? "";
  const timezone = currentOrganization?.timezone || "UTC";
  const [period, setPeriod] = useState<ReportingPeriod>("last_30_days");
  const [statusSelection, setStatusSelection] = useState({
    orgId: "",
    status: "",
  });
  const status = statusSelection.orgId === orgId ? statusSelection.status : "";
  const dateWindow = useMemo(() => {
    return getReportingDateWindow(period, timezone);
  }, [period, timezone]);
  const analytics = useQuery({
    queryKey: [
      "dashboard-analytics",
      user?.id,
      orgId,
      period,
      status,
      timezone,
    ],
    queryFn: () =>
      callLogService.getAnalytics(orgId, period, status || undefined, timezone),
    enabled: Boolean(user && orgId),
    staleTime: 60_000,
  });
  const data = analytics.data;
  useEffect(() => {
    if (data && status && !data.available_statuses.includes(status)) {
      setStatusSelection({ orgId, status: "" });
    }
  }, [data, orgId, status]);
  const counts = data?.calls_by_status ?? [];
  const completed =
    counts.find((item) => item.status === "completed")?.count ?? 0;
  const failed = counts
    .filter((item) => UNSUCCESSFUL_STATUSES.has(item.status))
    .reduce((sum, item) => sum + item.count, 0);
  const completionRate = data?.selected_total_calls
    ? Math.round((completed / data.selected_total_calls) * 100)
    : null;
  const latestUpdated = analytics.dataUpdatedAt
    ? new Date(analytics.dataUpdatedAt).toLocaleTimeString()
    : null;
  const statusOptions = data?.available_statuses ?? [];
  const statusWeights = data?.calls_by_status.map((item) => item.count) ?? [];

  return (
    <div className="mx-auto min-w-0 max-w-7xl space-y-6 pb-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary">
            Workspace overview
          </p>
          <h1 className="mt-1 text-3xl font-semibold tracking-tight">
            {currentOrganization?.name ?? "Dashboard"}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {currentOrganization
              ? "Voice activity, agent health and follow-up work"
              : "Select an organization in the workspace switcher to see its activity."}
          </p>
        </div>
        {orgId && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => void analytics.refetch()}
            disabled={analytics.isFetching}
          >
            <RefreshCw
              className={cn(
                "mr-2 h-4 w-4",
                analytics.isFetching && "animate-spin",
              )}
            />
            Refresh call data
          </Button>
        )}
      </header>

      {platformAdmin && user && <PlatformPulse userId={user.id} />}

      {orgId && (
        <DashboardFilters
          period={period}
          status={status}
          statusOptions={statusOptions}
          onPeriodChange={(value) => setPeriod(value)}
          onStatusChange={(value) =>
            setStatusSelection({ orgId, status: value })
          }
        />
      )}

      {!orgId ? (
        <section className="rounded-xl border border-dashed bg-card p-8 text-center">
          <Users className="mx-auto h-8 w-8 text-muted-foreground" />
          <h2 className="mt-3 font-semibold">Choose a workspace</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            The dashboard follows the organization selected in the workspace
            switcher.
          </p>
        </section>
      ) : (
        <>
          <section
            aria-label="Call performance"
            className="rounded-xl border bg-card p-5 sm:p-6"
          >
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Call performance
              </p>
              <p className="mt-1 text-sm text-muted-foreground">
                Workspace call health for the selected filters
              </p>
            </div>
            {analytics.isError ? (
              <Unavailable retry={() => void analytics.refetch()} />
            ) : !data ? (
              <p
                role="status"
                className="py-10 text-center text-sm text-muted-foreground"
              >
                Loading workspace call metrics…
              </p>
            ) : (
              <>
                <dl className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                  <Metric
                    label="Calls"
                    value={number.format(data.selected_total_calls)}
                    detail={`${getReportingPeriodLabel(period)}${status ? ` · ${formatStatus(status)}` : " · all statuses"}`}
                    icon={Phone}
                  />
                  <Metric
                    label="Completed"
                    value={number.format(completed)}
                    detail={
                      status
                        ? "Within selected status"
                        : completionRate == null
                          ? "No calls match these filters"
                          : `${completionRate}% of matching calls`
                    }
                    icon={CheckCircle2}
                  />
                  <Metric
                    label="Unsuccessful"
                    value={number.format(failed)}
                    detail="Failed, unanswered, busy or canceled outcomes"
                    icon={Activity}
                  />
                  <Metric
                    label="Avg. call duration"
                    value={formatDuration(
                      data.selected_average_duration_seconds,
                    )}
                    detail={
                      status && status !== "completed"
                        ? "No completed calls match this status"
                        : data.selected_average_duration_seconds == null
                          ? "No completed duration recorded"
                          : "Completed calls with recorded duration"
                    }
                    icon={Clock3}
                  />
                </dl>
                <p className="mt-4 text-right text-xs text-muted-foreground">
                  Includes all call sources · {timezone} · Updated{" "}
                  {latestUpdated ?? "just now"}
                </p>
              </>
            )}
          </section>

          {analytics.isError ? null : !data ? null : (
            <div className="grid min-w-0 gap-4 xl:grid-cols-12">
              <div className="min-w-0 xl:col-span-8">
                <CallVolume data={data} period={period} />
              </div>
              <div className="min-w-0 xl:col-span-4">
                <PeakHours data={data} timezone={timezone} />
              </div>
              <section className="flex h-full min-w-0 flex-col rounded-xl border bg-card p-5 sm:p-6 xl:col-span-4">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h2 className="font-semibold">Call outcomes</h2>
                    <p className="mt-1 text-sm text-muted-foreground">
                      Status mix for the selected period and filter
                    </p>
                  </div>
                  <CheckCircle2
                    aria-hidden="true"
                    className="h-5 w-5 text-primary"
                  />
                </div>
                {data.selected_total_calls === 0 ? (
                  <p className="mt-5 rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
                    No calls match these filters.
                  </p>
                ) : (
                  <>
                    <InteractiveChart
                      data={data.calls_by_status}
                      chartLabel="Call outcomes by status. Move the pointer or use the arrow keys to inspect each status."
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
                          {data.calls_by_status.map((item) => (
                            <span
                              key={item.status}
                              className={
                                STATUS_COLORS[item.status] ?? "bg-sky-500"
                              }
                              style={{
                                width: `${(item.count / data.selected_total_calls) * 100}%`,
                              }}
                            />
                          ))}
                        </div>
                      )}
                    </InteractiveChart>
                    <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-3">
                      {data.calls_by_status.map((item) => (
                        <div
                          key={item.status}
                          className="flex items-center gap-2 text-sm"
                        >
                          <span
                            aria-hidden="true"
                            className={cn(
                              "h-2.5 w-2.5 shrink-0 rounded-full",
                              STATUS_COLORS[item.status] ?? "bg-sky-500",
                            )}
                          />
                          <dt className="min-w-0 truncate capitalize text-muted-foreground">
                            {formatStatus(item.status)}
                          </dt>
                          <dd className="ml-auto tabular-nums">
                            {number.format(item.count)}
                          </dd>
                        </div>
                      ))}
                    </dl>
                  </>
                )}
              </section>
              <div className="min-w-0 xl:col-span-8">
                <AgentSnapshot
                  orgId={orgId}
                  period={period}
                  status={status || undefined}
                  canManage={permissions.canCreateAgent}
                  timezone={timezone}
                  data={data}
                />
              </div>
            </div>
          )}

          <div className="grid min-w-0 gap-4 xl:grid-cols-12">
            <div className="min-w-0 xl:col-span-12">
              <RecentCalls
                orgId={orgId}
                period={period}
                status={status || undefined}
                dateFrom={dateWindow.from}
                dateToExclusive={dateWindow.toExclusive}
                timezone={timezone}
                analytics={data}
              />
            </div>
            <div
              className={cn(
                "min-w-0",
                permissions.canManageBilling
                  ? "xl:col-span-8"
                  : "xl:col-span-12",
              )}
            >
              <FollowUp
                orgId={orgId}
                canManage={
                  permissions.isOrgAdmin || permissions.isPlatformAdmin
                }
                timezone={timezone}
              />
            </div>
            {!permissions.isLoading && permissions.canManageBilling && (
              <div className="min-w-0 xl:col-span-4">
                <AccountCapacity orgId={orgId} />
              </div>
            )}
          </div>
          {platformAdmin && (
            <section className="rounded-xl border bg-card px-5 py-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h2 className="font-semibold">Platform administration</h2>
                  <p className="text-sm text-muted-foreground">
                    Selected workspace activity stays above; these links manage
                    the wider platform.
                  </p>
                </div>
                <div className="flex flex-wrap gap-4 text-sm">
                  <Link className="underline" href="/organizations">
                    Organizations
                  </Link>
                  <Link className="underline" href="/organizations/credits">
                    Credit management
                  </Link>
                  <Link className="underline" href="/platform/phone-numbers">
                    Phone numbers
                  </Link>
                </div>
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}
