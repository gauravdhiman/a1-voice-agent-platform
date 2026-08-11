import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeAll, describe, expect, it } from "vitest";
import type { CustomerPlanVersion } from "@/types/billing";
import { PlanCard, toPlanCardData } from "../plan-card";

const planWithEntitlementMetadata: CustomerPlanVersion = {
  id: "version-growth",
  plan_product_id: "product-growth",
  tier_rank: 10,
  product_slug: "growth",
  product_name: "Growth",
  product_description: "For growing teams.",
  version_number: 1,
  display_label: "Growth plan",
  billing_mode: "paid",
  credit_grant_policy: "recurring",
  price_amount_cents: 2900,
  currency: "USD",
  billing_interval: "monthly",
  trial_period_days: null,
  stripe_price_id: "price-growth",
  entitlements: {
    max_agents: { type: "integer", value: 10 },
  },
  entitlement_metadata: {
    max_agents: {
      display_name: "Maximum agents",
      description: "The maximum number of voice agents your organization can create.",
    },
  },
};

describe("PlanCard", () => {
  beforeAll(() => {
    globalThis.ResizeObserver = class {
      observe() {}
      unobserve() {}
      disconnect() {}
    };
  });

  it("uses customer-facing entitlement metadata for labels and descriptions", () => {
    const plan = toPlanCardData(planWithEntitlementMetadata);

    expect(plan.entitlements).toEqual([
      {
        key: "max_agents",
        label: "Maximum agents",
        description:
          "The maximum number of voice agents your organization can create.",
        value: { type: "integer", value: 10 },
      },
    ]);
  });

  it("shows entitlement descriptions in accessible tooltips", async () => {
    const user = userEvent.setup();
    render(<PlanCard plan={toPlanCardData(planWithEntitlementMetadata)} />);

    const infoButton = screen.getByRole("button", {
      name: "More information about Maximum agents",
    });
    expect(screen.getByText("10 Maximum agents")).toBeInTheDocument();

    await user.hover(infoButton);

    expect(await screen.findByRole("tooltip")).toHaveTextContent(
      "The maximum number of voice agents your organization can create.",
    );
  });

  it("does not render an empty tooltip when an entitlement has no description", () => {
    render(
      <PlanCard
        plan={{
          ...toPlanCardData(planWithEntitlementMetadata),
          entitlements: [
            {
              key: "max_agents",
              label: "Maximum agents",
              description: null,
              value: { type: "integer", value: 10 },
            },
          ],
        }}
      />,
    );

    expect(
      screen.queryByRole("button", {
        name: "More information about Maximum agents",
      }),
    ).not.toBeInTheDocument();
  });
});
