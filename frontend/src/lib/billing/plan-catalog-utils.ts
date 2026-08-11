import type {
  PlanProductWithVersions,
  PlanVersionSummary,
} from "@/types/admin-plans";

export type BillingCadence = "monthly" | "annual";

/** Return true when a plan product is the platform's non-Stripe free tier. */
export function isFreePlanProduct(
  product: Pick<PlanProductWithVersions, "slug"> | string,
): boolean {
  return (
    (typeof product === "string" ? product : product.slug).trim().toLowerCase() ===
    "free"
  );
}

/** Sort catalog products from the smallest tier to the largest tier. */
export function sortProductsByCatalogOrder(
  products: PlanProductWithVersions[],
): PlanProductWithVersions[] {
  return [...products].sort(
    (left, right) =>
      catalogTierRank(left) - catalogTierRank(right) ||
      left.display_name.localeCompare(right.display_name) ||
      left.slug.localeCompare(right.slug),
  );
}

/**
 * Resolve the legacy default rank used by the initial plan backfill.
 *
 * New custom ranks remain authoritative. Legacy paid rows all used 10, so the
 * known plan names need the same compatibility ordering as the customer API.
 */
function catalogTierRank(product: PlanProductWithVersions): number {
  if (product.sort_order !== 10) return product.sort_order;

  const slug = product.slug.toLowerCase();
  for (const [keyword, rank] of [
    ["enterprise", 30],
    ["pro", 20],
    ["growth", 20],
    ["starter", 10],
    ["free", 0],
  ] as const) {
    if (slug.includes(keyword)) return rank;
  }
  return product.sort_order;
}

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
  return sortProductsByCatalogOrder(
    products.filter(
      (product) => resolveProductBillingCadence(product, overrides) === cadence,
    ),
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
