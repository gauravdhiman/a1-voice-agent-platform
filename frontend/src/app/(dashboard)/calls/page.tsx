"use client";

import React, { useState, useCallback, useMemo, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { useOrganization } from "@/contexts/organization-context";
import { useMyAgents } from "@/hooks/use-agent-queries";
import { useCallLogs } from "@/hooks/use-call-logs";
import { useOrganizationById } from "@/hooks/use-organization-by-id";
import { callLogService, CallLogListParams } from "@/services/call-log-service";
import { ApiRequestError } from "@/lib/api/client";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Phone,
  PhoneIncoming,
  PhoneMissed,
  PhoneOff,
  Zap,
  ChevronLeft,
  ChevronRight,
  Loader2,
  AlertTriangle,
  RefreshCw,
  Headphones,
  ShieldCheck,
} from "lucide-react";
import { useUserPermissions } from "@/hooks/use-user-permissions";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

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
    completed:
      "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
    answered:
      "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400",
    initiated:
      "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400",
    ringing:
      "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400",
    missed:
      "bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400",
    failed: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
    busy: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
    "no-answer":
      "bg-gray-100 text-gray-800 dark:bg-gray-800/60 dark:text-gray-400",
  };
  const cls =
    map[status] ??
    "bg-gray-100 text-gray-800 dark:bg-gray-800/60 dark:text-gray-400";
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${cls}`}
    >
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

function formatDuration(seconds: number | null): string {
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
  const { currentOrganization, setCurrentOrganization } = useOrganization();
  const searchParams = useSearchParams();
  const requestedOrgId = searchParams.get("org_id");
  const orgId = requestedOrgId ?? currentOrganization?.id ?? "";
  const {
    isValid: isOrgValid,
    loading: organizationLoading,
    organization: validatedOrganization,
  } = useOrganizationById(orgId || null);
  const { data: agents = [] } = useMyAgents();
  const { isOrgAdmin, isPlatformAdmin } = useUserPermissions();

  const [agentFilter, setAgentFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [page, setPage] = useState(1);
  const [recordingOpen, setRecordingOpen] = useState(false);
  const [recordingCallId, setRecordingCallId] = useState<string | null>(null);
  const [recordingUrl, setRecordingUrl] = useState<string | null>(null);
  const [recordingLoadingId, setRecordingLoadingId] = useState<string | null>(
    null,
  );
  const [recordingError, setRecordingError] = useState<string | null>(null);
  const [recordingUnavailableIds, setRecordingUnavailableIds] = useState<
    Set<string>
  >(() => new Set());

  const params: CallLogListParams = useMemo(
    () => ({
      agent_id: agentFilter || undefined,
      status: statusFilter || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
      recording_only: true,
      page,
      page_size: 25,
    }),
    [agentFilter, statusFilter, dateFrom, dateTo, page],
  );

  useEffect(() => {
    if (
      validatedOrganization &&
      validatedOrganization.id !== currentOrganization?.id
    ) {
      setCurrentOrganization(validatedOrganization);
    }
  }, [validatedOrganization, currentOrganization, setCurrentOrganization]);

  const { data, isLoading, isFetching, error, refetch } = useCallLogs(
    orgId,
    params,
  );

  const handleFilterChange = useCallback(() => {
    setPage(1);
  }, []);

  const handleListen = useCallback(async (callId: string) => {
    setRecordingCallId(callId);
    setRecordingLoadingId(callId);
    setRecordingError(null);
    try {
      const blob = await callLogService.downloadRecording(callId);
      setRecordingUrl((previousUrl) => {
        if (previousUrl) URL.revokeObjectURL(previousUrl);
        return URL.createObjectURL(blob);
      });
      setRecordingOpen(true);
    } catch (error) {
      const recordingUnavailable =
        error instanceof ApiRequestError && [404, 410].includes(error.status);
      if (recordingUnavailable) {
        setRecordingUnavailableIds((previous) => {
          const next = new Set(previous);
          next.add(callId);
          return next;
        });
      }
      setRecordingUrl(null);
      setRecordingOpen(true);
      setRecordingError(
        recordingUnavailable
          ? "This recording is no longer available. It may have reached the retention limit or been removed from storage."
          : "This recording could not be loaded. Please try again later.",
      );
    } finally {
      setRecordingLoadingId(null);
    }
  }, []);

  const handleRecordingOpenChange = useCallback((open: boolean) => {
    setRecordingOpen(open);
    if (!open) {
      setRecordingUrl(null);
      setRecordingCallId(null);
      setRecordingError(null);
    }
  }, []);

  useEffect(() => {
    return () => {
      if (recordingUrl) URL.revokeObjectURL(recordingUrl);
    };
  }, [recordingUrl]);

  // Agent name lookup map
  const agentNameMap = useMemo(
    () => Object.fromEntries(agents.map((a) => [a.id, a.name])),
    [agents],
  );

  if (!orgId) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-muted-foreground">No organization selected.</p>
      </div>
    );
  }

  if (organizationLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        <p className="ml-2 text-muted-foreground">Loading organization…</p>
      </div>
    );
  }

  if (!isOrgValid) {
    return (
      <Alert variant="destructive">
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription>
          You do not have access to this organization&apos;s call reports.
        </AlertDescription>
      </Alert>
    );
  }

  const organizationName =
    validatedOrganization?.name ??
    currentOrganization?.name ??
    "the organization";

  return (
    <div className="space-y-6" data-tour="calls-page">
      {/* Header */}
      <div className="flex items-center space-x-4">
        <div className="bg-primary/10 p-3 rounded-lg">
          <Phone className="h-6 w-6 text-primary" />
        </div>
        <div>
          <h1 className="text-2xl font-bold">Call Recordings</h1>
          <p className="text-sm text-muted-foreground">
            Recorded calls across all agents for {organizationName}
          </p>
        </div>
      </div>

      {isOrgAdmin || isPlatformAdmin ? (
        <Alert className="border-primary/20 bg-primary/5">
          <ShieldCheck className="h-4 w-4 text-primary" />
          <AlertDescription>
            <p className="font-medium text-foreground">
              Recording privacy, security, and retention
            </p>
            <p className="mt-1">
              Recordings are private and available only to organization and
              platform admins through authenticated access. Staging and
              production recordings use private, provider-encrypted storage;
              local development recordings stay in the ignored local data
              directory. Recordings are retained according to the configured
              policy, which defaults to 90 days, and may be removed earlier.
              Ensure callers are notified and consent requirements are met
              before using recordings, including any applicable regulatory
              requirements for your jurisdiction.
            </p>
          </AlertDescription>
        </Alert>
      ) : null}

      {/* Filters */}
      <Card data-tour="calls-filters">
        <CardHeader>
          <CardTitle className="text-base">Filter recordings</CardTitle>
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
              <label
                htmlFor="call-date-from"
                className="block text-sm font-medium text-muted-foreground mb-1"
              >
                From
              </label>
              <input
                id="call-date-from"
                type="date"
                value={dateFrom}
                onChange={(e) => {
                  const nextFrom = e.target.value;
                  setDateFrom(nextFrom);
                  if (nextFrom && dateTo && dateTo < nextFrom) {
                    setDateTo("");
                  }
                  handleFilterChange();
                }}
                className="w-full px-3 py-2 border border-input bg-background rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            {/* Date to */}
            <div>
              <label
                htmlFor="call-date-to"
                className="block text-sm font-medium text-muted-foreground mb-1"
              >
                To
              </label>
              <input
                id="call-date-to"
                type="date"
                value={dateTo}
                min={dateFrom || undefined}
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
      <Card data-tour="calls-results">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Recorded Calls</CardTitle>
              {data && (
                <CardDescription>
                  {data.total} recording{data.total !== 1 ? "s" : ""} found
                </CardDescription>
              )}
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => void refetch()}
              disabled={isFetching}
              aria-label="Refresh"
              data-tour="calls-refresh"
            >
              <RefreshCw
                className={`h-4 w-4 ${isFetching ? "animate-spin" : ""}`}
              />
              <span className="ml-2">Refresh</span>
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              <span className="ml-3 text-muted-foreground">
                Loading recordings…
              </span>
            </div>
          ) : error ? (
            <div className="flex items-center justify-center py-16">
              <p className="text-destructive text-sm">
                Failed to load call logs.
              </p>
            </div>
          ) : !data || data.items.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16">
              <Phone className="h-12 w-12 text-muted-foreground opacity-30 mb-4" />
              <p className="text-lg font-semibold text-foreground">
                No recordings yet
              </p>
              <p className="text-sm text-muted-foreground mt-1">
                Recorded calls will appear here once your agents start handling them.
              </p>
            </div>
          ) : (
            <>
              {/* Desktop table */}
              <div className="hidden md:block overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border bg-muted/30">
                      <th className="text-left px-6 py-3 font-medium text-muted-foreground">
                        Date &amp; Time
                      </th>
                      <th className="text-left px-6 py-3 font-medium text-muted-foreground">
                        Caller
                      </th>
                      <th className="text-left px-6 py-3 font-medium text-muted-foreground">
                        Agent
                      </th>
                      <th className="text-left px-6 py-3 font-medium text-muted-foreground">
                        Status
                      </th>
                      <th className="text-left px-6 py-3 font-medium text-muted-foreground">
                        Duration
                      </th>
                      <th className="text-right px-6 py-3 font-medium text-muted-foreground">
                        Credits
                      </th>
                      {isOrgAdmin || isPlatformAdmin ? (
                        <th className="text-right px-6 py-3 font-medium text-muted-foreground">
                          Recording
                        </th>
                      ) : null}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {data.items.map((call) => (
                      <tr
                        key={call.id}
                        className="hover:bg-muted/20 transition-colors"
                      >
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
                          {call.agent_id
                            ? (agentNameMap[call.agent_id] ?? "Unknown Agent")
                            : "—"}
                        </td>
                        <td className="px-6 py-3">
                          {statusBadge(call.status)}
                        </td>
                        <td className="px-6 py-3 text-muted-foreground">
                          {formatDuration(call.duration)}
                        </td>
                        <td className="px-6 py-3 text-right font-mono text-xs text-muted-foreground">
                          <span className="inline-flex items-center gap-1">
                            <Zap className="h-3 w-3 text-amber-500" />
                            {call.credits_consumed || 0}
                          </span>
                        </td>
                        {isOrgAdmin || isPlatformAdmin ? (
                          <td className="px-6 py-3 text-right">
                            {call.recording_available &&
                            !recordingUnavailableIds.has(call.id) ? (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => void handleListen(call.id)}
                                disabled={recordingLoadingId === call.id}
                                aria-label={`Listen to recording for call ${call.id}`}
                              >
                                {recordingLoadingId === call.id ? (
                                  <Loader2 className="h-4 w-4 animate-spin" />
                                ) : (
                                  <Headphones className="h-4 w-4" />
                                )}
                                <span className="ml-1">Listen</span>
                              </Button>
                            ) : (
                              <span className="text-xs text-muted-foreground">
                                Unavailable
                              </span>
                            )}
                          </td>
                        ) : null}
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
                      <span>·</span>
                      <span>{call.credits_consumed || 0} credits</span>
                      {isOrgAdmin || isPlatformAdmin ? (
                        <>
                          <span>·</span>
                          {call.recording_available &&
                          !recordingUnavailableIds.has(call.id) ? (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-6 px-1 text-xs"
                              onClick={() => void handleListen(call.id)}
                              disabled={recordingLoadingId === call.id}
                              aria-label={`Listen to recording for call ${call.id}`}
                            >
                              {recordingLoadingId === call.id ? (
                                <Loader2 className="h-3 w-3 animate-spin" />
                              ) : (
                                <Headphones className="h-3 w-3" />
                              )}
                              <span className="ml-1">Listen</span>
                            </Button>
                          ) : (
                            <span>Recording unavailable</span>
                          )}
                        </>
                      ) : null}
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
                      onClick={() =>
                        setPage((p) => Math.min(data.total_pages, p + 1))
                      }
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

      <Dialog open={recordingOpen} onOpenChange={handleRecordingOpenChange}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Headphones className="h-5 w-5 text-primary" />
              Call recording
            </DialogTitle>
            <DialogDescription>
              {recordingCallId
                ? `Private recording for call ${recordingCallId}`
                : "Private call recording"}
            </DialogDescription>
          </DialogHeader>
          {recordingError ? (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>{recordingError}</AlertDescription>
            </Alert>
          ) : recordingUrl ? (
            <audio
              key={recordingUrl}
              className="w-full"
              controls
              autoPlay
              src={recordingUrl}
            >
              Your browser does not support audio playback.
            </audio>
          ) : (
            <div className="flex items-center justify-center py-6 text-sm text-muted-foreground">
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Loading recording…
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
