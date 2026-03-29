"use client";

import React, { useState, useCallback, useMemo } from "react";
import { useOrganization } from "@/contexts/organization-context";
import { useMyAgents } from "@/hooks/use-agent-queries";
import { useCallLogs } from "@/hooks/use-call-logs";
import { CallLogListParams } from "@/services/call-log-service";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Phone,
  PhoneIncoming,
  PhoneMissed,
  PhoneOff,
  ChevronLeft,
  ChevronRight,
  Loader2,
} from "lucide-react";

const STATUS_OPTIONS = [
  { value: "", label: "All Statuses" },
  { value: "initiated", label: "Initiated" },
  { value: "ringing", label: "Ringing" },
  { value: "answered", label: "Answered" },
  { value: "completed", label: "Completed" },
  { value: "missed", label: "Missed" },
  { value: "failed", label: "Failed" },
  { value: "busy", label: "Busy" },
  { value: "no-answer", label: "No Answer" },
];

function statusBadge(status: string) {
  const map: Record<string, string> = {
    completed: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
    answered: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400",
    initiated: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400",
    ringing: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400",
    missed: "bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400",
    failed: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
    busy: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
    "no-answer": "bg-gray-100 text-gray-800 dark:bg-gray-800/60 dark:text-gray-400",
  };
  const cls = map[status] ?? "bg-gray-100 text-gray-800 dark:bg-gray-800/60 dark:text-gray-400";
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${cls}`}>
      {status}
    </span>
  );
}

function StatusIcon({ status }: { status: string }) {
  if (status === "completed" || status === "answered") {
    return <PhoneIncoming className="h-4 w-4 text-green-500" />;
  }
  if (status === "missed" || status === "no-answer") {
    return <PhoneMissed className="h-4 w-4 text-orange-500" />;
  }
  if (status === "failed" || status === "busy") {
    return <PhoneOff className="h-4 w-4 text-red-500" />;
  }
  return <Phone className="h-4 w-4 text-muted-foreground" />;
}

function formatDuration(seconds: number): string {
  if (!seconds) return "—";
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

function formatDateTime(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function CallsPage() {
  const { currentOrganization } = useOrganization();
  const { data: agents = [] } = useMyAgents();

  const [agentFilter, setAgentFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [page, setPage] = useState(1);

  const params: CallLogListParams = useMemo(
    () => ({
      agent_id: agentFilter || undefined,
      status: statusFilter || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
      page,
      page_size: 25,
    }),
    [agentFilter, statusFilter, dateFrom, dateTo, page]
  );

  const orgId = currentOrganization?.id ?? "";
  const { data, isLoading, error } = useCallLogs(orgId, params);

  const handleFilterChange = useCallback(() => {
    setPage(1);
  }, []);

  // Agent name lookup map
  const agentNameMap = useMemo(
    () => Object.fromEntries(agents.map((a) => [a.id, a.name])),
    [agents]
  );

  if (!currentOrganization) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-muted-foreground">No organization selected.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center space-x-4">
        <div className="bg-primary/10 p-3 rounded-lg">
          <Phone className="h-6 w-6 text-primary" />
        </div>
        <div>
          <h1 className="text-2xl font-bold">Call Log</h1>
          <p className="text-sm text-muted-foreground">
            History of all incoming calls for {currentOrganization.name}
          </p>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Agent filter */}
            <div>
              <label className="block text-sm font-medium text-muted-foreground mb-1">
                Agent
              </label>
              <select
                value={agentFilter}
                onChange={(e) => {
                  setAgentFilter(e.target.value);
                  handleFilterChange();
                }}
                className="w-full px-3 py-2 border border-input bg-background rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="">All Agents</option>
                {agents.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Status filter */}
            <div>
              <label className="block text-sm font-medium text-muted-foreground mb-1">
                Status
              </label>
              <select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  handleFilterChange();
                }}
                className="w-full px-3 py-2 border border-input bg-background rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              >
                {STATUS_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Date from */}
            <div>
              <label className="block text-sm font-medium text-muted-foreground mb-1">
                From
              </label>
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => {
                  setDateFrom(e.target.value);
                  handleFilterChange();
                }}
                className="w-full px-3 py-2 border border-input bg-background rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            {/* Date to */}
            <div>
              <label className="block text-sm font-medium text-muted-foreground mb-1">
                To
              </label>
              <input
                type="date"
                value={dateTo}
                onChange={(e) => {
                  setDateTo(e.target.value);
                  handleFilterChange();
                }}
                className="w-full px-3 py-2 border border-input bg-background rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Table */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Recent Calls</CardTitle>
              {data && (
                <CardDescription>
                  {data.total} call{data.total !== 1 ? "s" : ""} found
                </CardDescription>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              <span className="ml-3 text-muted-foreground">Loading calls…</span>
            </div>
          ) : error ? (
            <div className="flex items-center justify-center py-16">
              <p className="text-destructive text-sm">Failed to load call logs.</p>
            </div>
          ) : !data || data.items.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16">
              <Phone className="h-12 w-12 text-muted-foreground opacity-30 mb-4" />
              <p className="text-lg font-semibold text-foreground">No calls yet</p>
              <p className="text-sm text-muted-foreground mt-1">
                Calls will appear here once your agents start receiving them.
              </p>
            </div>
          ) : (
            <>
              {/* Desktop table */}
              <div className="hidden md:block overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border bg-muted/30">
                      <th className="text-left px-6 py-3 font-medium text-muted-foreground">Date &amp; Time</th>
                      <th className="text-left px-6 py-3 font-medium text-muted-foreground">Caller</th>
                      <th className="text-left px-6 py-3 font-medium text-muted-foreground">Agent</th>
                      <th className="text-left px-6 py-3 font-medium text-muted-foreground">Status</th>
                      <th className="text-left px-6 py-3 font-medium text-muted-foreground">Duration</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {data.items.map((call) => (
                      <tr key={call.id} className="hover:bg-muted/20 transition-colors">
                        <td className="px-6 py-3 text-foreground whitespace-nowrap">
                          {formatDateTime(call.created_at)}
                        </td>
                        <td className="px-6 py-3">
                          <div className="flex items-center gap-2">
                            <StatusIcon status={call.status} />
                            <span className="font-mono text-sm">
                              {call.caller_number ?? "—"}
                            </span>
                          </div>
                        </td>
                        <td className="px-6 py-3 text-muted-foreground">
                          {call.agent_id ? (agentNameMap[call.agent_id] ?? "Unknown Agent") : "—"}
                        </td>
                        <td className="px-6 py-3">
                          {statusBadge(call.status)}
                        </td>
                        <td className="px-6 py-3 text-muted-foreground">
                          {formatDuration(call.duration)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Mobile cards */}
              <div className="md:hidden divide-y divide-border">
                {data.items.map((call) => (
                  <div key={call.id} className="px-4 py-3 space-y-1">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <StatusIcon status={call.status} />
                        <span className="font-mono text-sm font-medium">
                          {call.caller_number ?? "Unknown"}
                        </span>
                      </div>
                      {statusBadge(call.status)}
                    </div>
                    <div className="text-xs text-muted-foreground flex gap-3">
                      <span>{formatDateTime(call.created_at)}</span>
                      <span>·</span>
                      <span>{formatDuration(call.duration)}</span>
                      {call.agent_id && (
                        <>
                          <span>·</span>
                          <span>{agentNameMap[call.agent_id] ?? "Agent"}</span>
                        </>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {/* Pagination */}
              {data.total_pages > 1 && (
                <div className="flex items-center justify-between px-6 py-4 border-t border-border">
                  <p className="text-sm text-muted-foreground">
                    Page {data.page} of {data.total_pages}
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      disabled={page === 1}
                    >
                      <ChevronLeft className="h-4 w-4" />
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((p) => Math.min(data.total_pages, p + 1))}
                      disabled={page === data.total_pages}
                    >
                      Next
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
