import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  callbackService,
  type EscalationStatus,
} from "@/services/callback-service";

export const escalationQueryKeys = {
  all: ["escalations"] as const,
  list: (orgId: string, status?: EscalationStatus) =>
    [...escalationQueryKeys.all, "list", orgId, status ?? "all"] as const,
};

/**
 * Fetches callback escalations newest-first for one organization.
 *
 * @param orgId - Organization whose callbacks should be loaded.
 * @param status - Optional follow-up status filter.
 * @param enabled - Whether the query should run after the org is known.
 * @returns React Query state for the requested escalations.
 */
export function useEscalations(
  orgId: string,
  status?: EscalationStatus,
  enabled = true,
) {
  return useQuery({
    queryKey: escalationQueryKeys.list(orgId, status),
    queryFn: async () => {
      const result = await callbackService.listEscalations(orgId, status);
      if (!result.success) throw new Error(result.error);
      return result.data ?? [];
    },
    staleTime: 15 * 1000,
    refetchOnMount: "always",
    enabled: Boolean(orgId) && enabled,
  });
}

/**
 * Advances one escalation's follow-up status and refreshes the list.
 *
 * @returns React Query mutation for the status transition.
 */
export function useMarkEscalationStatus(orgId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { escalationId: string; status: EscalationStatus }) =>
      callbackService.markEscalationStatus(
        orgId,
        input.escalationId,
        input.status,
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: escalationQueryKeys.all });
    },
  });
}
