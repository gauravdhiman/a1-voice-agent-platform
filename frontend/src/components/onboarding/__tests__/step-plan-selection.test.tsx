import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { StepPlanSelection } from "@/components/onboarding/step-plan-selection";
import { billingService } from "@/services/billing-service";
import type { CustomerPlanVersion } from "@/types/billing";

vi.mock("@/services/billing-service", () => ({
  billingService: {
    getAvailablePlanVersions: vi.fn(),
    activateFreePlan: vi.fn(),
    createVersionedSubscriptionCheckout: vi.fn(),
  },
}));

vi.mock("sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn() },
}));

const freePlan: CustomerPlanVersion = {
  id: "version-free",
  plan_product_id: "product-free",
  product_slug: "free",
  product_name: "Free",
  product_description: "Explore the platform",
  version_number: 1,
  display_label: "Free",
  billing_mode: "free",
  credit_grant_policy: "recurring",
  price_amount_cents: 0,
  currency: "USD",
  billing_interval: "monthly",
  trial_period_days: null,
  stripe_price_id: null,
  entitlements: {
    included_credits_monthly: { type: "integer", value: 100 },
  },
};

const paidPlan: CustomerPlanVersion = {
  ...freePlan,
  id: "version-paid",
  plan_product_id: "product-paid",
  product_slug: "growth",
  product_name: "Growth",
  display_label: "Growth",
  billing_mode: "paid",
  price_amount_cents: 2900,
  stripe_price_id: "price_growth",
};

describe("StepPlanSelection", () => {
  beforeEach(() => {
    vi.mocked(billingService.getAvailablePlanVersions).mockResolvedValue([
      freePlan,
      paidPlan,
    ]);
    vi.mocked(billingService.activateFreePlan).mockResolvedValue({
      created: true,
      subscription: {
        id: "subscription-1",
        organization_id: "org-1",
        plan_version_id: "version-free",
        status: "active",
        stripe_customer_id: null,
        subscription_plan_id: null,
        stripe_subscription_id: null,
        current_period_start: null,
        current_period_end: null,
        metadata: { billing_mode: "free" },
      },
    });
    vi.mocked(
      billingService.createVersionedSubscriptionCheckout,
    ).mockResolvedValue({
      checkout_url: "https://checkout.stripe.test/session",
      session_id: "cs_test",
      plan_version_id: "version-paid",
    });
  });

  it("loads current plans and activates Free without Stripe", async () => {
    const onActivated = vi.fn();
    render(
      <StepPlanSelection organizationId="org-1" onActivated={onActivated} />,
    );

    expect(await screen.findByText("Choose a plan")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("onboarding-plan-select-version-free"));

    await waitFor(() =>
      expect(billingService.activateFreePlan).toHaveBeenCalledWith(
        "org-1",
        "version-free",
      ),
    );
    expect(
      billingService.createVersionedSubscriptionCheckout,
    ).not.toHaveBeenCalled();
    expect(onActivated).toHaveBeenCalledWith("version-free");
  });

  it("starts paid checkout with the selected version", async () => {
    const onRedirectToCheckout = vi.fn();
    render(
      <StepPlanSelection
        organizationId="org-1"
        onActivated={vi.fn()}
        onRedirectToCheckout={onRedirectToCheckout}
      />,
    );

    expect(
      await screen.findByRole("heading", { name: "Growth" }),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("onboarding-plan-select-version-paid"));

    await waitFor(() =>
      expect(
        billingService.createVersionedSubscriptionCheckout,
      ).toHaveBeenCalledWith(
        expect.objectContaining({
          organization_id: "org-1",
          plan_version_id: "version-paid",
        }),
      ),
    );
    expect(onRedirectToCheckout).toHaveBeenCalledWith(
      "https://checkout.stripe.test/session",
    );
  });

  it("preserves the plan selector when checkout is cancelled", async () => {
    render(
      <StepPlanSelection
        organizationId="org-1"
        onActivated={vi.fn()}
        paymentState="cancelled"
      />,
    );

    expect(await screen.findByText("Choose a plan")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent(/cancelled/i);
  });
});
