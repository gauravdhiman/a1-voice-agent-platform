import { useQuery } from "@tanstack/react-query";
import { useOrganization } from "@/contexts/organization-context";
import { billingService } from "@/services/billing-service";
import type { CreditUsageResponse } from "@/types/billing";

/**
 * Loads the selected organization's credit balance and usage ledger.
 *
 * The query is scoped by organization id so a platform administrator changing
 * the selected organization cannot display stale usage from the previous one.
 */
export function useCreditUsage(organizationIdOverride?: string) {
  const { currentOrganization } = useOrganization();
  const organizationId = organizationIdOverride ?? currentOrganization?.id;

  return useQuery<CreditUsageResponse, Error>({
    queryKey: ["credit-usage", organizationId],
    queryFn: () => {
      if (!organizationId) {
        throw new Error("Organization ID is not available");
      }
      return billingService.getCreditUsage(organizationId);
    },
    enabled: Boolean(organizationId),
    staleTime: 30 * 1000,
    refetchOnWindowFocus: false,
  });
}
