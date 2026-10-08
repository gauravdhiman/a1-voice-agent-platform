import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeAll, describe, expect, it } from "vitest";
import type { CustomerPlanVersion } from "@/types/billing";
import { friendlyPlanName, PlanCard, toPlanCardData } from "../plan-card";

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
    expect(screen.getByText("Up to 10 voice agents")).toBeInTheDocument();

    await user.hover(infoButton);

    expect(await screen.findByRole("tooltip")).toHaveTextContent(
      "The maximum number of voice agents your organization can create.",
    );
  });

  it("uses the catalog label and description for premium integrations", async () => {
    const user = userEvent.setup();
    const plan = toPlanCardData({
      ...planWithEntitlementMetadata,
      entitlements: {
        premium_tools: { type: "boolean", value: true },
      },
      entitlement_metadata: {
        premium_tools: {
          display_name: "Premium integrations",
          description:
            "Includes Gmail, Google Sheets, HubSpot lead capture, and Cal.com scheduling.",
        },
      },
    });

    render(<PlanCard plan={plan} />);

    expect(screen.getByText("Premium integrations")).toBeTruthy();
    await user.hover(
      screen.getByRole("button", {
        name: "More information about Premium integrations",
      }),
    );

    const tooltip = await screen.findByRole("tooltip");
    expect(tooltip.textContent).toContain("Gmail");
    expect(tooltip.textContent).toContain("Google Sheets");
    expect(tooltip.textContent).toContain("HubSpot lead capture");
    expect(tooltip.textContent).toContain("Cal.com scheduling");
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

  it("shows included credits as call minutes without inventing plan features", () => {
    render(
      <PlanCard
        plan={{
          ...toPlanCardData(planWithEntitlementMetadata),
          entitlements: [
            {
              key: "included_credits_per_billing_period",
              label: "Included credits per billing period",
              description: null,
              value: { type: "integer", value: 2500 },
            },
          ],
        }}
      />,
    );

    expect(
      screen.getByText(
        "Up to 250 call minutes per month (2,500 credits)",
      ),
    ).toBeTruthy();
    expect(screen.queryByText("One US local business number included on request")).toBeNull();
    expect(screen.queryByText("Additional call-credit packs available")).toBeNull();
    expect(screen.queryByText("Add a call widget to your website")).toBeNull();
  });

  it("hides interval and version suffixes from plan names", () => {
    expect(
      friendlyPlanName({
        product_slug: "starter-plan-month-v1",
        product_name: "Starter Plan",
        display_label: "Starter Plan:Month v1",
      }),
    ).toBe("Starter");
  });

  it("keeps a legacy Enterprise product distinct from Scale", () => {
    expect(
      friendlyPlanName({
        product_slug: "enterprise-month-v1",
        product_name: "Enterprise Plan:Month v1",
        display_label: "Enterprise Plan:Month v1",
      }),
    ).toBe("Enterprise");
  });

  it("shows Scale without its billing or version suffix", () => {
    expect(
      friendlyPlanName({
        product_slug: "scale-month-v1",
        product_name: "Scale Plan:Month v1",
        display_label: "Scale Plan:Month v1",
      }),
    ).toBe("Scale");
  });

  it("uses the product slug when a display label contains only billing cadence", () => {
    expect(
      friendlyPlanName({
        product_slug: "starter",
        product_name: "Monthly",
        display_label: "Monthly",
      }),
    ).toBe("Starter");
  });

  it("shows annual minutes as a yearly total and monthly equivalent", () => {
    render(
      <PlanCard
        plan={{
          ...toPlanCardData(planWithEntitlementMetadata),
          billing_interval: "annual",
          entitlements: [
            {
              key: "included_credits_per_billing_period",
              label: "Included credits per billing period",
              description: null,
              value: { type: "integer", value: 30000 },
            },
          ],
        }}
      />,
    );

    expect(
      screen.getByText(
        "Up to 3,000 call minutes per year (250/month average; 30,000 annual credits)",
      ),
    ).toBeTruthy();
    });
  });

  it.each([0, -1])(
    "renders non-positive agent limits as unlimited (%i)",
    (value) => {
      const plan = toPlanCardData({
        ...planWithEntitlementMetadata,
        entitlements: { max_agents: { type: "integer", value } },
      });

      expect(plan.entitlements[0].value).toEqual({ type: "unlimited" });
    },
  );
