import { useQuery } from "@tanstack/react-query";
import { callLogService, CallLogListParams } from "@/services/call-log-service";

export const callLogQueryKeys = {
  all: ["call-logs"] as const,
  list: (orgId: string, params: CallLogListParams) =>
    [...callLogQueryKeys.all, "list", orgId, params] as const,
  analytics: (orgId: string) =>
    [...callLogQueryKeys.all, "analytics", orgId] as const,
};

export function useCallLogs(orgId: string, params: CallLogListParams = {}) {
  return useQuery({
    queryKey: callLogQueryKeys.list(orgId, params),
    queryFn: () => callLogService.listCallLogs(orgId, params),
    staleTime: 30 * 1000,
    enabled: !!orgId,
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
