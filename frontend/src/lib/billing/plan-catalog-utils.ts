import type {
  PlanProductWithVersions,
  PlanVersionSummary,
} from "@/types/admin-plans";

export type BillingCadence = "monthly" | "annual";

/**
 * Resolve whether a plan product belongs in the monthly or annual catalog tab.
 */
export function resolveProductBillingCadence(
  product: PlanProductWithVersions,
  overrides: Record<string, BillingCadence> = {},
): BillingCadence {
  const override = overrides[product.slug];
  if (override) return override;

  const currentSignup = product.versions.find((v) => v.is_current_for_signup);
  if (currentSignup?.billing_interval === "annual") return "annual";
  if (currentSignup?.billing_interval === "monthly") return "monthly";

  const latest = product.versions[0];
  if (latest?.billing_interval === "annual") return "annual";
  return "monthly";
}

/**
 * Filter plan products for a billing cadence tab.
 */
export function filterProductsByCadence(
  products: PlanProductWithVersions[],
  cadence: BillingCadence,
  overrides: Record<string, BillingCadence> = {},
): PlanProductWithVersions[] {
  return products.filter(
    (product) => resolveProductBillingCadence(product, overrides) === cadence,
  );
}

export function productHasDraft(product: PlanProductWithVersions): boolean {
  return product.versions.some((v) => v.status === "draft");
}

export function defaultBillingInterval(product: PlanProductWithVersions): BillingCadence {
  return resolveProductBillingCadence(product);
}

export function isVersionSummary(
  version: PlanVersionSummary,
): version is PlanVersionSummary {
  return version != null;
}
