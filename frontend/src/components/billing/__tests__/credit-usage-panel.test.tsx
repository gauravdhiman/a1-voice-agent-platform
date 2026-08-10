import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { CreditUsageResponse } from "@/types/billing";
import { CreditUsagePanel } from "../credit-usage-panel";

const usage: CreditUsageResponse = {
  organization_id: "org-1",
  balance: {
    total_credits: 2400,
    subscription_credits: 1800,
    purchased_credits: 600,
    expiring_soon: 200,
    expires_at: "2026-09-01T00:00:00Z",
  },
  period_start: "2026-08-01T00:00:00Z",
  period_end: "2026-09-01T00:00:00Z",
  period_credits_granted: 3000,
  period_credits_used: 600,
  period_credits_remaining: 2400,
  usage_by_category: [],
  transactions: [
    {
      id: "transaction-1",
      organization_id: "org-1",
      amount: -100,
      balance_after: 2400,
      transaction_type: "consumed",
      source: "event_consumption",
      source_id: null,
      credit_event_id: null,
      expires_at: null,
      stripe_payment_intent_id: null,
      description: "Voice call",
      metadata: null,
      created_at: "2026-08-08T12:00:00Z",
      credit_event: null,
    },
  ],
};

describe("CreditUsagePanel", () => {
  it("renders only the balance summary in summary mode", () => {
    render(<CreditUsagePanel usage={usage} variant="summary" />);

    expect(screen.getByText("Available now")).toBeInTheDocument();
    expect(screen.queryByText("Credit ledger")).not.toBeInTheDocument();
  });

  it("renders usage details and the full ledger in details mode", () => {
    render(<CreditUsagePanel usage={usage} variant="details" />);

    expect(screen.getByText("Period burn")).toBeInTheDocument();
    expect(screen.getByText("Credit ledger")).toBeInTheDocument();
    expect(screen.getByText("Voice call")).toBeInTheDocument();
    expect(screen.queryByText("Available now")).not.toBeInTheDocument();
  });
});
