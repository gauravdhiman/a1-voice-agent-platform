import React from "react";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  getAvailablePlanVersions: vi.fn(),
  getSubscriptionPlans: vi.fn(),
  activateFreePlan: vi.fn(),
  createVersionedSubscriptionCheckout: vi.fn(),
  previewPlanChange: vi.fn(),
  confirmPlanChange: vi.fn(),
}));

vi.mock("@/services/billing-service", () => ({
  billingService: mocks,
}));

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

import { PlanSelection } from "../plan-selection";

const freePlan = {
  id: "version-free",
  plan_product_id: "product-free",
  product_slug: "free",
  product_name: "Free",
  product_description: "Start with the essentials.",
  version_number: 1,
  display_label: "Free plan",
  billing_mode: "free" as const,
  credit_grant_policy: "recurring" as const,
  price_amount_cents: 0,
  currency: "USD",
  billing_interval: "monthly",
  trial_period_days: null,
  stripe_price_id: null,
  tier_rank: 0,
  entitlements: {
    max_agents: { type: "integer", value: 1 },
  },
};

const paidPlan = {
  ...freePlan,
  id: "version-pro-month",
  plan_product_id: "product-pro",
  product_slug: "pro-month-v1",
  product_name: "Pro Plan:Month v1",
  product_description: "For growing teams.",
  display_label: "Pro Plan:Month v1",
  billing_mode: "paid" as const,
  price_amount_cents: 14900,
  billing_interval: "monthly",
  stripe_price_id: "price_pro",
  tier_rank: 20,
  entitlements: {
    max_agents: { type: "integer", value: 10 },
    premium_tools: { type: "boolean", value: true },
    included_credits_per_billing_period: { type: "integer", value: 10000 },
  },
};

const starterPlan = {
  ...freePlan,
  id: "version-starter",
  plan_product_id: "product-starter",
  product_slug: "starter",
  product_name: "Starter",
  product_description: "For small teams.",
  display_label: "Starter plan",
  billing_mode: "paid" as const,
  price_amount_cents: 4900,
  billing_interval: "monthly",
  stripe_price_id: "price_starter",
  tier_rank: 10,
  entitlements: {
    max_agents: { type: "integer", value: 5 },
  },
};

describe("PlanSelection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.getAvailablePlanVersions.mockResolvedValue([
      paidPlan,
      starterPlan,
      freePlan,
    ]);
    mocks.activateFreePlan.mockResolvedValue({ created: true });
    mocks.createVersionedSubscriptionCheckout.mockResolvedValue({
      checkout_url: "https://checkout.stripe.test/session",
      session_id: "cs_growth",
      plan_version_id: paidPlan.id,
    });
    mocks.previewPlanChange.mockResolvedValue({
      transition_id: "transition-1",
      current_plan: paidPlan,
      target_plan: starterPlan,
      effective_mode: "period_end",
      effective_at: "2026-09-01T00:00:00Z",
      price_delta_cents: 2000,
      credit_delta: null,
      proration_behavior: "none",
      purchased_credits_preserved: true,
    });
    mocks.confirmPlanChange.mockResolvedValue({
      status: "scheduled",
      target_plan_version_id: starterPlan.id,
      effective_at: "2026-09-01T00:00:00Z",
    });
  });

  it("renders the internal published plan catalog instead of legacy Stripe plans", async () => {
    render(<PlanSelection organizationId="org-1" />);

    expect(await screen.findByText("Pro")).toBeInTheDocument();
    expect(screen.getByText("For growing teams.")).toBeInTheDocument();
    expect(screen.getByText(/Up to 10 voice agents/i)).toBeInTheDocument();
    expect(mocks.getAvailablePlanVersions).toHaveBeenCalledTimes(1);
    expect(mocks.getSubscriptionPlans).not.toHaveBeenCalled();
  });

  it("keeps the free-plan payment note in the card footer", async () => {
    render(<PlanSelection organizationId="org-1" />);

    const freeCard = await screen.findByTestId(
      `billing-plan-card-${freePlan.id}`,
    );

    expect(
      within(freeCard).getByText("No payment method required"),
    ).toBeInTheDocument();
  });

  it("activates a free internal plan without Stripe", async () => {
    const user = userEvent.setup();
    const onPlanSelected = vi.fn();

    render(
      <PlanSelection organizationId="org-1" onPlanSelected={onPlanSelected} />,
    );

    await user.click(
      await screen.findByRole("button", { name: /start with free/i }),
    );

    await waitFor(() => {
      expect(mocks.activateFreePlan).toHaveBeenCalledWith("org-1", freePlan.id);
    });
    expect(mocks.createVersionedSubscriptionCheckout).not.toHaveBeenCalled();
    expect(onPlanSelected).toHaveBeenCalledWith(freePlan);
  });

  it("starts Stripe Checkout with the selected internal plan version", async () => {
    const user = userEvent.setup();
    const redirect = vi.fn();

    render(
      <PlanSelection organizationId="org-1" onRedirectToCheckout={redirect} />,
    );

    await user.click(
      within(
        await screen.findByTestId(`billing-plan-card-${paidPlan.id}`),
      ).getByRole("button", { name: /continue to payment/i }),
    );

    await waitFor(() => {
      expect(mocks.createVersionedSubscriptionCheckout).toHaveBeenCalledWith(
        expect.objectContaining({
          organization_id: "org-1",
          plan_version_id: paidPlan.id,
          success_url: expect.stringContaining(
            "plan_version_id=" + paidPlan.id,
          ),
        }),
      );
    });
    expect(redirect).toHaveBeenCalledWith(
      "https://checkout.stripe.test/session",
    );
  });

  it("sorts plan cards by tier rank instead of price", async () => {
    render(<PlanSelection organizationId="org-1" />);

    await screen.findByText("Starter");

    const cards = screen
      .getAllByTestId(/billing-plan-card-/)
      .map((card) => card.getAttribute("data-testid"));

    expect(cards).toEqual([
      `billing-plan-card-${freePlan.id}`,
      `billing-plan-card-${starterPlan.id}`,
      `billing-plan-card-${paidPlan.id}`,
    ]);
  });

  it("fits four plan cards across the desktop row", async () => {
    const scalePlan = {
      ...paidPlan,
      id: "version-scale-month",
      plan_product_id: "product-scale",
      product_slug: "scale-month-v1",
      product_name: "Scale",
      display_label: "Scale",
      tier_rank: 30,
    };
    mocks.getAvailablePlanVersions.mockResolvedValue([
      paidPlan,
      starterPlan,
      scalePlan,
      freePlan,
    ]);

    const { container } = render(<PlanSelection organizationId="org-1" />);

    expect(await screen.findByTestId(`billing-plan-card-${scalePlan.id}`)).toBeTruthy();
    expect(screen.getAllByTestId(/billing-plan-card-/)).toHaveLength(4);
    expect(container.querySelector('[class~="xl:grid-cols-4"]')).toBeTruthy();
  });

  it("offers annual billing only when it is exactly ten monthly payments", async () => {
    const monthlyForAnnual = {
      ...paidPlan,
      product_slug: "pro-monthly-v1",
    };
    const discountedAnnual = {
      ...paidPlan,
      id: "version-pro-annual",
      product_slug: "pro-annual-v1",
      product_name: "Pro Plan:Annual v1",
      display_label: "Pro Plan:Annual v1",
      billing_interval: "annual",
      price_amount_cents: paidPlan.price_amount_cents * 10,
      entitlements: {
        ...paidPlan.entitlements,
        included_credits_per_billing_period: {
          type: "integer",
          value: 120000,
        },
      },
    };
    const incorrectlyPricedAnnual = {
      ...discountedAnnual,
      id: "version-pro-annual-invalid",
      product_slug: "pro-yearly",
      price_amount_cents: paidPlan.price_amount_cents * 11,
    };
    mocks.getAvailablePlanVersions.mockResolvedValue([
      monthlyForAnnual,
      discountedAnnual,
      incorrectlyPricedAnnual,
      freePlan,
    ]);
    const user = userEvent.setup();

    render(<PlanSelection organizationId="org-1" />);

    await screen.findByText("Pro");
    await user.click(
      screen.getByRole("button", { name: /annual · 2 months free/i }),
    );

    expect(screen.getByTestId("billing-plan-card-version-pro-annual")).toBeTruthy();
    expect(
      screen.queryByTestId("billing-plan-card-version-pro-annual-invalid"),
    ).toBeNull();
    expect(screen.getByText("2 months free")).toBeTruthy();
  });

  it("lets an active organization preview and confirm a different plan", async () => {
    const user = userEvent.setup();

    render(
      <PlanSelection
        organizationId="org-1"
        currentSubscription={
          {
            status: "active",
            plan_version_id: paidPlan.id,
          } as never
        }
      />,
    );

    expect(
      await screen.findByRole("button", { name: "Current plan" }),
    ).toBeDisabled();

    const starterButton = within(
      screen.getByTestId(`billing-plan-card-${starterPlan.id}`),
    ).getByRole("button", { name: /review plan change/i });
    expect(starterButton).toBeEnabled();
    await user.click(starterButton);

    await waitFor(() => {
      expect(mocks.previewPlanChange).toHaveBeenCalledWith(
        "org-1",
        starterPlan.id,
      );
    });
    expect(
      screen.getByText(/change from pro to starter/i),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /schedule change/i }));

    await waitFor(() => {
      expect(mocks.confirmPlanChange).toHaveBeenCalledWith(
        expect.objectContaining({
          organization_id: "org-1",
          transition_id: "transition-1",
          target_plan_version_id: starterPlan.id,
        }),
      );
    });
    expect(mocks.createVersionedSubscriptionCheckout).not.toHaveBeenCalled();
  });

  it("shows the new credit allowance and when it refreshes", async () => {
    const user = userEvent.setup();
    const freePlanWithCredits = {
      ...freePlan,
      entitlements: {
        included_credits_per_billing_period: { type: "integer", value: 100 },
      },
    };
    mocks.previewPlanChange.mockResolvedValue({
      transition_id: "transition-credits",
      current_plan: freePlanWithCredits,
      target_plan: paidPlan,
      effective_mode: "immediate",
      effective_at: null,
      price_delta_cents: 2900,
      credit_delta: 900,
      proration_behavior: "create_prorations",
      purchased_credits_preserved: true,
    });

    render(
      <PlanSelection
        organizationId="org-1"
        currentSubscription={
          { status: "active", plan_version_id: freePlan.id } as never
        }
      />,
    );

    await user.click(
      within(
        await screen.findByTestId(`billing-plan-card-${paidPlan.id}`),
      ).getByRole("button", { name: /review plan change/i }),
    );

    const previewDialog = await screen.findByRole("dialog");
    expect(previewDialog.textContent).toContain(
      "10,000 included credits per billing period (up to 1,000 call minutes)",
    );
    expect(previewDialog.textContent).toContain(
      "This plan-credit balance refreshes after your next renewal payment succeeds",
    );
  });

  it("shows the credit refresh timing for an immediate billing interval change", async () => {
    const user = userEvent.setup();
    const annualPlan = {
      ...paidPlan,
      id: "version-pro-annual",
      product_slug: "pro-annual-v1",
      product_name: "Pro Plan:Annual v1",
      display_label: "Pro Plan:Annual v1",
      billing_interval: "annual",
      price_amount_cents: 149000,
      entitlements: {
        ...paidPlan.entitlements,
        included_credits_per_billing_period: { type: "integer", value: 120000 },
      },
    };
    mocks.getAvailablePlanVersions.mockResolvedValue([
      paidPlan,
      annualPlan,
      freePlan,
    ]);
    mocks.previewPlanChange.mockResolvedValue({
      transition_id: "transition-annual",
      current_plan: paidPlan,
      target_plan: annualPlan,
      effective_mode: "immediate",
      effective_at: null,
      price_delta_cents: 134100,
      credit_delta: 110000,
      proration_behavior: "create_prorations",
      purchased_credits_preserved: true,
    });

    render(
      <PlanSelection
        organizationId="org-1"
        currentSubscription={
          { status: "active", plan_version_id: paidPlan.id } as never
        }
      />,
    );

    await screen.findByText("Pro");
    await user.click(
      screen.getByRole("button", { name: /annual · 2 months free/i }),
    );
    await user.click(
      within(
        await screen.findByTestId(`billing-plan-card-${annualPlan.id}`),
      ).getByRole("button", { name: /review plan change/i }),
    );

    const previewDialog = await screen.findByRole("dialog");
    expect(previewDialog.textContent).toContain(
      "120,000 included credits per billing period (up to 12,000 call minutes)",
    );
    expect(previewDialog.textContent).toContain(
      "This plan-credit balance refreshes after payment for this plan change succeeds",
    );
  });
});
