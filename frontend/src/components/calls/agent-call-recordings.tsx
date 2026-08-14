"use client";

import React from "react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { ApiRequestError } from "@/lib/api/client";
import { useCallLogs } from "@/hooks/use-call-logs";
import { callLogService } from "@/services/call-log-service";
import {
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  Headphones,
  Loader2,
  PhoneIncoming,
  RefreshCw,
} from "lucide-react";

interface AgentCallRecordingsProps {
  /** Organization that owns the agent and its call records. */
  organizationId: string;
  /** Agent whose completed recordings should be displayed. */
  agentId: string;
  /** Agent name used in the panel description and empty state. */
  agentName: string;
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
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Displays completed recordings for one agent and streams playback through
 * the authenticated call-recording endpoint.
 *
 * The query is server-filtered before pagination, so calls without recordings
 * do not displace recordings from later pages.
 */
export function AgentCallRecordings({
  organizationId,
  agentId,
  agentName,
}: AgentCallRecordingsProps) {
  const [page, setPage] = React.useState(1);
  const [recordingOpen, setRecordingOpen] = React.useState(false);
  const [recordingCallId, setRecordingCallId] = React.useState<string | null>(null);
  const [recordingUrl, setRecordingUrl] = React.useState<string | null>(null);
  const [recordingLoadingId, setRecordingLoadingId] = React.useState<string | null>(null);
  const [recordingError, setRecordingError] = React.useState<string | null>(null);
  const [recordingUnavailableIds, setRecordingUnavailableIds] = React.useState<Set<string>>(
    () => new Set(),
  );

  const { data, isLoading, isFetching, error, refetch } = useCallLogs(
    organizationId,
    {
      agent_id: agentId,
      recording_only: true,
      page,
      page_size: 25,
    },
  );

  const handleListen = React.useCallback(async (callId: string) => {
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

  const handleRecordingOpenChange = React.useCallback((open: boolean) => {
    setRecordingOpen(open);
    if (!open) {
      setRecordingUrl(null);
      setRecordingCallId(null);
      setRecordingError(null);
    }
  }, []);

  React.useEffect(() => {
    return () => {
      if (recordingUrl) URL.revokeObjectURL(recordingUrl);
    };
  }, [recordingUrl]);

  return (
    <>
      <Card data-tour="agent-detail-recordings">
        <CardHeader className="p-5 pb-3">
          <div className="flex items-center justify-between gap-4">
            <div>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Headphones className="h-5 w-5" />
                Call Recordings
              </CardTitle>
              <CardDescription>
                Recorded calls handled by {agentName}
                {data ? ` · ${data.total} recording${data.total === 1 ? "" : "s"}` : ""}
              </CardDescription>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => void refetch()}
              disabled={isFetching}
              aria-label="Refresh recordings"
            >
              <RefreshCw className={`h-4 w-4 ${isFetching ? "animate-spin" : ""}`} />
              <span className="ml-2 hidden sm:inline">Refresh</span>
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              <span className="ml-3 text-muted-foreground">Loading recordings…</span>
            </div>
          ) : error ? (
            <div className="flex items-center justify-center py-16">
              <p className="text-destructive text-sm">Failed to load call recordings.</p>
            </div>
          ) : !data || data.items.length === 0 ? (
            <div className="flex flex-col items-center justify-center px-6 py-16 text-center">
              <Headphones className="mb-4 h-12 w-12 text-muted-foreground opacity-30" />
              <p className="text-lg font-semibold text-foreground">No recordings yet</p>
              <p className="mt-1 max-w-md text-sm text-muted-foreground">
                Recordings of {agentName}&apos;s calls will appear here after the agent handles a recorded call.
              </p>
            </div>
          ) : (
            <>
              <div className="divide-y divide-border">
                {data.items.map((call) => (
                  <div
                    key={call.id}
                    className="flex flex-col gap-3 px-5 py-4 transition-colors hover:bg-muted/20 sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div className="flex min-w-0 items-center gap-3">
                      <div className="rounded-full bg-primary/10 p-2">
                        <PhoneIncoming className="h-4 w-4 text-primary" />
                      </div>
                      <div className="min-w-0">
                        <p className="truncate font-medium">
                          {call.caller_number ?? "Unknown caller"}
                        </p>
                        <p className="text-sm text-muted-foreground">
                          {formatDateTime(call.created_at)} · {formatDuration(call.duration)}
                        </p>
                      </div>
                    </div>
                    {call.recording_available && !recordingUnavailableIds.has(call.id) ? (
                      <Button
                        variant="outline"
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
                        <span className="ml-2">Listen</span>
                      </Button>
                    ) : (
                      <span className="text-xs text-muted-foreground">Unavailable</span>
                    )}
                  </div>
                ))}
              </div>

              {data.total_pages > 1 && (
                <div className="flex items-center justify-between border-t border-border px-5 py-4">
                  <p className="text-sm text-muted-foreground">
                    Page {data.page} of {data.total_pages}
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((current) => Math.max(1, current - 1))}
                      disabled={page === 1}
                    >
                      <ChevronLeft className="h-4 w-4" />
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((current) => Math.min(data.total_pages, current + 1))}
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
              {recordingCallId ? `Private recording for call ${recordingCallId}` : "Private call recording"}
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
