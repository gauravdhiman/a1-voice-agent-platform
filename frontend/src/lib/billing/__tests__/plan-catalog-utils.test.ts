import { describe, expect, it } from "vitest";
import {
  filterProductsByCadence,
  productHasDraft,
  resolveProductBillingCadence,
} from "@/lib/billing/plan-catalog-utils";
import type { PlanProductWithVersions } from "@/types/admin-plans";

function product(
  slug: string,
  versions: PlanProductWithVersions["versions"],
): PlanProductWithVersions {
  return {
    id: slug,
    slug,
    display_name: slug,
    sort_order: 0,
    is_active: true,
    created_at: "",
    updated_at: "",
    versions,
  };
}

describe("plan-catalog-utils", () => {
  it("resolves cadence from current signup version", () => {
    const p = product("pro", [
      {
        id: "v1",
        plan_product_id: "pro",
        version_number: 2,
        status: "published",
        billing_mode: "paid",
        credit_grant_policy: "recurring",
        price_amount_cents: 1000,
        currency: "USD",
        billing_interval: "monthly",
        is_current_for_signup: false,
        created_at: "",
        updated_at: "",
      },
      {
        id: "v2",
        plan_product_id: "pro",
        version_number: 3,
        status: "published",
        billing_mode: "paid",
        credit_grant_policy: "recurring",
        price_amount_cents: 12000,
        currency: "USD",
        billing_interval: "annual",
        is_current_for_signup: true,
        created_at: "",
        updated_at: "",
      },
    ]);
    expect(resolveProductBillingCadence(p)).toBe("annual");
  });

  it("filters products by cadence tab", () => {
    const monthly = product("starter-monthly", [
      {
        id: "v1",
        plan_product_id: "starter-monthly",
        version_number: 1,
        status: "published",
        billing_mode: "free",
        credit_grant_policy: "recurring",
        price_amount_cents: 0,
        currency: "USD",
        billing_interval: "monthly",
        is_current_for_signup: true,
        created_at: "",
        updated_at: "",
      },
    ]);
    const annual = product("pro-annual", [
      {
        id: "v2",
        plan_product_id: "pro-annual",
        version_number: 1,
        status: "published",
        billing_mode: "paid",
        credit_grant_policy: "recurring",
        price_amount_cents: 9900,
        currency: "USD",
        billing_interval: "annual",
        is_current_for_signup: true,
        created_at: "",
        updated_at: "",
      },
    ]);
    expect(filterProductsByCadence([monthly, annual], "monthly")).toEqual([
      monthly,
    ]);
    expect(filterProductsByCadence([monthly, annual], "annual")).toEqual([
      annual,
    ]);
  });

  it("sorts products from the smallest catalog tier to the largest", () => {
    const products = [
      { ...product("enterprise", []), sort_order: 10 },
      { ...product("starter", []), sort_order: 10 },
      { ...product("free", []), sort_order: 10 },
      { ...product("pro", []), sort_order: 10 },
    ];

    expect(filterProductsByCadence(products, "monthly").map((p) => p.slug)).toEqual([
      "free",
      "starter",
      "pro",
      "enterprise",
    ]);
  });

  it("detects draft on product", () => {
    const p = product("x", [
      {
        id: "v1",
        plan_product_id: "x",
        version_number: 1,
        status: "draft",
        billing_mode: "paid",
        credit_grant_policy: "recurring",
        price_amount_cents: 0,
        currency: "USD",
        billing_interval: "monthly",
        is_current_for_signup: false,
        created_at: "",
        updated_at: "",
      },
    ]);
    expect(productHasDraft(p)).toBe(true);
  });
});
