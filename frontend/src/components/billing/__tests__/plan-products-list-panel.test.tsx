import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { PlanProductsListPanel } from "../plan-products-list-panel";
import type { PlanProductWithVersions } from "@/types/admin-plans";

const PRODUCT: PlanProductWithVersions = {
  id: "product-1",
  slug: "starter-plan-monthly-with-a-long-slug",
  display_name: "Starter Plan Monthly With A Long Display Name",
  description: null,
  sort_order: 1,
  is_active: true,
  stripe_product_id: null,
  created_at: "2026-08-08T00:00:00Z",
  updated_at: "2026-08-08T00:00:00Z",
  versions: [
    {
      id: "version-1",
      plan_product_id: "product-1",
      version_number: 1,
      status: "published",
      display_label: "Published version with a long label",
      billing_mode: "paid",
      credit_grant_policy: "recurring",
      price_amount_cents: 2900,
      currency: "USD",
      billing_interval: "monthly",
      trial_period_days: null,
      stripe_product_id: null,
      stripe_price_id: null,
      is_current_for_signup: true,
      published_at: "2026-08-09T00:00:00Z",
      legacy_subscription_plan_id: null,
      created_at: "2026-08-08T00:00:00Z",
      updated_at: "2026-08-08T00:00:00Z",
    },
  ],
};

describe("PlanProductsListPanel", () => {
  it("stacks long catalog actions and keeps cadence tabs horizontally scrollable", () => {
    render(
      <PlanProductsListPanel
        products={[PRODUCT]}
        cadenceTab="monthly"
        onCadenceTabChange={vi.fn()}
        selectedVersionId={null}
        onSelectVersion={vi.fn()}
        onCreateDraft={vi.fn()}
        productBillingBySlug={{}}
      />,
    );

    expect(screen.getByRole("button", { name: "Draft" })).toHaveClass(
      "w-full",
      "sm:w-auto",
    );
    expect(screen.getByRole("tab", { name: /Monthly/ })).toHaveClass(
      "whitespace-nowrap",
    );
    expect(
      screen.getByRole("button", { name: /v1.*Published version/ }),
    ).toHaveClass("flex-col", "sm:flex-row");
  });
});
