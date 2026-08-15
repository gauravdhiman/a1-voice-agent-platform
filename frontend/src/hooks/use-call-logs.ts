import { useQuery } from "@tanstack/react-query";
import { callLogService, CallLogListParams } from "@/services/call-log-service";

export const callLogQueryKeys = {
  all: ["call-logs"] as const,
  list: (orgId: string, params: CallLogListParams) =>
    [...callLogQueryKeys.all, "list", orgId, params] as const,
  analytics: (orgId: string) =>
    [...callLogQueryKeys.all, "analytics", orgId] as const,
};

/**
 * Fetches paginated call logs with optional filters.
 *
 * @param orgId - Organization whose call logs should be loaded.
 * @param params - Optional server-side filters and pagination values.
 * @param enabled - Whether the query should run after the organization is known.
 * @returns React Query state for the requested call logs.
 */
export function useCallLogs(
  orgId: string,
  params: CallLogListParams = {},
  enabled = true,
) {
  return useQuery({
    queryKey: callLogQueryKeys.list(orgId, params),
    queryFn: () => callLogService.listCallLogs(orgId, params),
    staleTime: 30 * 1000,
    refetchOnMount: "always",
    enabled: Boolean(orgId) && enabled,
  });
}

export function useCallAnalytics(orgId: string) {
  return useQuery({
    queryKey: callLogQueryKeys.analytics(orgId),
    queryFn: () => callLogService.getAnalytics(orgId),
    staleTime: 60 * 1000,
    enabled: !!orgId,
  });
}
