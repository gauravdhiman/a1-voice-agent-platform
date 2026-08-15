"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { ApiRequestError } from "@/lib/api/client";
import { callLogService } from "@/services/call-log-service";
import type { CallLog, CallLogsResponse } from "@/services/call-log-service";
import {
  Alert,
  AlertDescription,
} from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  Headphones,
  Loader2,
  Phone,
  PhoneIncoming,
  PhoneMissed,
  PhoneOff,
  RefreshCw,
  Zap,
} from "lucide-react";

const STATUS_BADGE_CLASSES: Record<string, string> = {
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

/** Props for the shared responsive call-log list. */
export interface CallLogListProps {
  /** Paginated call data returned by the call-log API. */
  data?: CallLogsResponse;
  /** Whether the first page is loading. */
  isLoading: boolean;
  /** Whether a refresh or page transition is in progress. */
  isFetching: boolean;
  /** Query error, if loading failed. */
  error: unknown;
  /** Refreshes the current query. */
  onRefresh: () => void | Promise<unknown>;
  /** Changes the current result page. */
  onPageChange: (page: number) => void;
  /** Agent names used by the organization-wide view. */
  agentNameMap?: Record<string, string>;
  /** Whether to include the Agent column and mobile agent label. */
  showAgentColumn?: boolean;
  /** Whether the current user may play private recordings. */
  canViewRecordings: boolean;
  /** Card title shown above the list. */
  title?: string;
  /** Optional context text shown before the result count. */
  subtitle?: string;
  /** Empty-state heading. */
  emptyTitle?: string;
  /** Empty-state supporting copy. */
  emptyDescription?: string;
  /** Optional product-tour hook for the card. */
  dataTour?: string;
}

function statusBadge(status: string) {
  const cls =
    STATUS_BADGE_CLASSES[status] ??
    "bg-gray-100 text-gray-800 dark:bg-gray-800/60 dark:text-gray-400";
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}
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
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  return minutes > 0 ? `${minutes}m ${remainder}s` : `${remainder}s`;
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

/**
 * Renders the shared responsive call list used by the organization Calls page
 * and the agent-specific Call History tab.
 *
 * It owns private recording playback so both views have identical recording
 * behavior, including retention errors and authenticated audio loading.
 */
export function CallLogList({
  data,
  isLoading,
  isFetching,
  error,
  onRefresh,
  onPageChange,
  agentNameMap = {},
  showAgentColumn = true,
  canViewRecordings,
  title = "Recent Calls",
  subtitle,
  emptyTitle = "No calls yet",
  emptyDescription = "Calls will appear here once your agents start receiving them.",
  dataTour = "calls-results",
}: CallLogListProps) {
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

  const resultCount = useMemo(() => {
    if (!data) return "";
    return `${data.total} call${data.total !== 1 ? "s" : ""} found`;
  }, [data]);

  return (
    <>
      <Card data-tour={dataTour}>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>{title}</CardTitle>
              {data && (
                <CardDescription>
                  {subtitle ? `${subtitle} · ` : ""}
                  {resultCount}
                </CardDescription>
              )}
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => void onRefresh()}
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
              <span className="ml-3 text-muted-foreground">Loading calls…</span>
            </div>
          ) : error ? (
            <div className="flex items-center justify-center py-16">
              <p className="text-sm text-destructive">Failed to load call logs.</p>
            </div>
          ) : !data || data.items.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16">
              <Phone className="mb-4 h-12 w-12 text-muted-foreground opacity-30" />
              <p className="text-lg font-semibold text-foreground">{emptyTitle}</p>
              <p className="mt-1 text-sm text-muted-foreground">
                {emptyDescription}
              </p>
            </div>
          ) : (
            <>
              <div className="hidden overflow-x-auto md:block">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border bg-muted/30">
                      <th className="px-6 py-3 text-left font-medium text-muted-foreground">
                        Date &amp; Time
                      </th>
                      <th className="px-6 py-3 text-left font-medium text-muted-foreground">
                        Caller
                      </th>
                      {showAgentColumn && (
                        <th className="px-6 py-3 text-left font-medium text-muted-foreground">
                          Agent
                        </th>
                      )}
                      <th className="px-6 py-3 text-left font-medium text-muted-foreground">
                        Status
                      </th>
                      <th className="px-6 py-3 text-left font-medium text-muted-foreground">
                        Duration
                      </th>
                      <th className="px-6 py-3 text-right font-medium text-muted-foreground">
                        Credits
                      </th>
                      {canViewRecordings && (
                        <th className="px-6 py-3 text-right font-medium text-muted-foreground">
                          Recording
                        </th>
                      )}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {data.items.map((call) => (
                      <CallLogTableRow
                        key={call.id}
                        call={call}
                        agentNameMap={agentNameMap}
                        showAgentColumn={showAgentColumn}
                        canViewRecordings={canViewRecordings}
                        recordingUnavailableIds={recordingUnavailableIds}
                        recordingLoadingId={recordingLoadingId}
                        onListen={handleListen}
                      />
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="divide-y divide-border md:hidden">
                {data.items.map((call) => (
                  <CallLogMobileCard
                    key={call.id}
                    call={call}
                    agentNameMap={agentNameMap}
                    showAgentColumn={showAgentColumn}
                    canViewRecordings={canViewRecordings}
                    recordingUnavailableIds={recordingUnavailableIds}
                    recordingLoadingId={recordingLoadingId}
                    onListen={handleListen}
                  />
                ))}
              </div>

              {data.total_pages > 1 && (
                <div className="flex items-center justify-between border-t border-border px-6 py-4">
                  <p className="text-sm text-muted-foreground">
                    Page {data.page} of {data.total_pages}
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onPageChange(Math.max(1, data.page - 1))}
                      disabled={data.page === 1}
                    >
                      <ChevronLeft className="h-4 w-4" />
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() =>
                        onPageChange(Math.min(data.total_pages, data.page + 1))
                      }
                      disabled={data.page === data.total_pages}
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
    </>
  );
}

interface CallLogRowProps {
  call: CallLog;
  agentNameMap: Record<string, string>;
  showAgentColumn: boolean;
  canViewRecordings: boolean;
  recordingUnavailableIds: Set<string>;
  recordingLoadingId: string | null;
  onListen: (callId: string) => void;
}

function CallLogRecordingAction({
  call,
  canViewRecordings,
  recordingUnavailableIds,
  recordingLoadingId,
  onListen,
}: Pick<CallLogRowProps, "call" | "canViewRecordings" | "recordingUnavailableIds" | "recordingLoadingId" | "onListen">) {
  if (!canViewRecordings) return null;
  if (!call.recording_available || recordingUnavailableIds.has(call.id)) {
    return <span className="text-xs text-muted-foreground">Unavailable</span>;
  }
  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={() => onListen(call.id)}
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
  );
}

function CallLogTableRow({
  call,
  agentNameMap,
  showAgentColumn,
  canViewRecordings,
  recordingUnavailableIds,
  recordingLoadingId,
  onListen,
}: CallLogRowProps) {
  return (
    <tr className="transition-colors hover:bg-muted/20">
      <td className="whitespace-nowrap px-6 py-3 text-foreground">
        {formatDateTime(call.created_at)}
      </td>
      <td className="px-6 py-3">
        <div className="flex items-center gap-2">
          <StatusIcon status={call.status} />
          <span className="font-mono text-sm">{call.caller_number ?? "—"}</span>
        </div>
      </td>
      {showAgentColumn && (
        <td className="px-6 py-3 text-muted-foreground">
          {call.agent_id
            ? agentNameMap[call.agent_id] ?? "Unknown Agent"
            : "—"}
        </td>
      )}
      <td className="px-6 py-3">{statusBadge(call.status)}</td>
      <td className="px-6 py-3 text-muted-foreground">
        {formatDuration(call.duration)}
      </td>
      <td className="px-6 py-3 text-right font-mono text-xs text-muted-foreground">
        <span className="inline-flex items-center gap-1">
          <Zap className="h-3 w-3 text-amber-500" />
          {call.credits_consumed || 0}
        </span>
      </td>
      {canViewRecordings && (
        <td className="px-6 py-3 text-right">
          <CallLogRecordingAction
            call={call}
            canViewRecordings={canViewRecordings}
            recordingUnavailableIds={recordingUnavailableIds}
            recordingLoadingId={recordingLoadingId}
            onListen={onListen}
          />
        </td>
      )}
    </tr>
  );
}

function CallLogMobileCard({
  call,
  agentNameMap,
  showAgentColumn,
  canViewRecordings,
  recordingUnavailableIds,
  recordingLoadingId,
  onListen,
}: CallLogRowProps) {
  return (
    <div className="space-y-1 px-4 py-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <StatusIcon status={call.status} />
          <span className="font-mono text-sm font-medium">
            {call.caller_number ?? "Unknown"}
          </span>
        </div>
        {statusBadge(call.status)}
      </div>
      <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
        <span>{formatDateTime(call.created_at)}</span>
        <span>·</span>
        <span>{formatDuration(call.duration)}</span>
        <span>·</span>
        <span>{call.credits_consumed || 0} credits</span>
        {canViewRecordings && (
          <>
            <span>·</span>
            <CallLogRecordingAction
              call={call}
              canViewRecordings={canViewRecordings}
              recordingUnavailableIds={recordingUnavailableIds}
              recordingLoadingId={recordingLoadingId}
              onListen={onListen}
            />
          </>
        )}
        {showAgentColumn && call.agent_id && (
          <>
            <span>·</span>
            <span>{agentNameMap[call.agent_id] ?? "Agent"}</span>
          </>
        )}
      </div>
    </div>
  );
}
