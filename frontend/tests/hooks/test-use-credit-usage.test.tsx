/** Tests for the useCreditUsage hook. */

import { describe, expect, it, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useCreditUsage } from "@/hooks/use-credit-usage";

vi.mock("@/contexts/organization-context", () => ({
  useOrganization: vi.fn().mockReturnValue({
    currentOrganization: { id: "selected-org" },
  }),
}));

vi.mock("@/services/billing-service", () => ({
  billingService: {
    getCreditUsage: vi.fn().mockResolvedValue({
      organization_id: "target-org",
      balance: {
        total_credits: 100,
        subscription_credits: 100,
        purchased_credits: 0,
        expiring_soon: 0,
        expires_at: null,
      },
      period_start: null,
      period_end: null,
      period_credits_granted: 100,
      period_credits_used: 0,
      period_credits_remaining: 100,
      usage_by_category: [],
      transactions: [],
    }),
  },
}));

import { billingService } from "@/services/billing-service";

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

describe("useCreditUsage", () => {
  it("uses the explicit organization id for platform-admin views", async () => {
    const { result } = renderHook(() => useCreditUsage("target-org"), {
      wrapper,
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(billingService.getCreditUsage).toHaveBeenCalledWith("target-org");
  });
});
