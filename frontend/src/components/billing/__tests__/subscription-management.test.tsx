import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  mockCreateCustomerPortal: vi.fn(),
  mockGetOrganizationEntitlements: vi.fn(),
}));

vi.mock("@/services/billing-service", () => ({
  billingService: {
    createCustomerPortal: mocks.mockCreateCustomerPortal,
    getOrganizationEntitlements: mocks.mockGetOrganizationEntitlements,
    cancelSubscription: vi.fn(),
    reactivateSubscription: vi.fn(),
  },
}));

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

import { SubscriptionManagement } from "../subscription-management";

const freeSubscription = {
  id: "sub-free",
  organization_id: "org-1",
  subscription_plan_id: null,
  plan_version_id: "version-free",
  stripe_subscription_id: null,
  stripe_customer_id: null,
  status: "active" as const,
  current_period_start: "2026-08-01T00:00:00Z",
  current_period_end: "2026-09-01T00:00:00Z",
  trial_start: null,
  trial_end: null,
  cancel_at_period_end: false,
  cancelled_at: null,
  metadata: { billing_mode: "free" },
  created_at: "2026-08-01T00:00:00Z",
  updated_at: "2026-08-01T00:00:00Z",
  plan: null,
};

describe("SubscriptionManagement", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.mockGetOrganizationEntitlements.mockResolvedValue({
      organization_id: "org-1",
      plan_version_id: "version-free",
      plan_product_slug: "free",
      plan_version_number: 1,
      plan_version_label: "Free",
      is_legacy_version: false,
      is_entitled: true,
      cancel_at_period_end: false,
      access_until: "2026-09-01T00:00:00Z",
      limits: {},
      features: {},
      migration: null,
    });
  });

  it("does not offer a Stripe billing portal for a free subscription", async () => {
    render(
      <SubscriptionManagement
        organizationId="org-1"
        subscription={freeSubscription}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText("Free plan")).toBeInTheDocument();
    });

    expect(
      screen.queryByRole("button", { name: /manage billing/i }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("Payment & Billing")).not.toBeInTheDocument();
    expect(
      screen.getByText(/no payment method required for the free plan/i),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /cancel subscription/i }),
    ).not.toBeInTheDocument();
    expect(mocks.mockCreateCustomerPortal).not.toHaveBeenCalled();
  });

  it("offers separate plan and credit actions from the overview", async () => {
    const onChangePlan = vi.fn();
    const onBuyCredits = vi.fn();

    render(
      <SubscriptionManagement
        organizationId="org-1"
        subscription={freeSubscription}
        onChangePlan={onChangePlan}
        onBuyCredits={onBuyCredits}
      />,
    );

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /change plan/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /buy credits/i }),
      ).toBeInTheDocument();
    });
  });
});
