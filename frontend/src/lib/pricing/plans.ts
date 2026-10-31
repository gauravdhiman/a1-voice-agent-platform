/**
 * Single source of truth for public plan pricing and metadata.
 * 
 * These constants represent the public marketing amounts for 24x7 AI plans.
 * DO NOT change these values without GTM/billing approval.
 * 
 * Note: Live Stripe catalog may differ during transitions. The backend Plan Catalog
 * in Stripe is published separately by the founder. This module governs frontend
 * display only.
 */

export interface PlanPricing {
  /** Internal plan ID/slug (lowercase) */
  id: string;
  /** Display name for the plan */
  displayName: string;
  /** Monthly price in USD */
  monthlyUSD: number;
  /** Monthly price in cents */
  monthlyCents: number;
  /** Annual price in USD (10-for-12 discount) */
  annualUSD: number;
  /** Annual price in cents (10-for-12 discount) */
  annualCents: number;
  /** Monthly credits included */
  creditsPerMonth: number;
  /** Approximate call minutes per month (at 10 credits/min) */
  approximateMinutes: number;
}

/**
 * Public plan catalog constants.
 * Amounts locked by GTM Priority 1 (PR #174).
 */
export const PLANS: Record<string, PlanPricing> = {
  FREE: {
    id: "free",
    displayName: "Free",
    monthlyUSD: 0,
    monthlyCents: 0,
    annualUSD: 0,
    annualCents: 0,
    creditsPerMonth: 100,
    approximateMinutes: 10,
  },
  STARTER: {
    id: "starter",
    displayName: "Starter",
    monthlyUSD: 79,
    monthlyCents: 7900,
    annualUSD: 790,
    annualCents: 79000,
    creditsPerMonth: 2500,
    approximateMinutes: 250,
  },
  PRO: {
    id: "pro",
    displayName: "Pro",
    monthlyUSD: 149,
    monthlyCents: 14900,
    annualUSD: 1490,
    annualCents: 149000,
    creditsPerMonth: 10000,
    approximateMinutes: 1000,
  },
  SCALE: {
    id: "scale",
    displayName: "Scale",
    monthlyUSD: 299,
    monthlyCents: 29900,
    annualUSD: 2990,
    annualCents: 299000,
    creditsPerMonth: 21000,
    approximateMinutes: 2100,
  },
} as const;

/**
 * Format a price as USD currency.
 * @param amountUSD - Amount in dollars
 * @returns Formatted string like "$79"
 */
export function formatPriceUSD(amountUSD: number): string {
  return `$${amountUSD}`;
}

/**
 * Format a monthly price with "/month" suffix.
 * @param amountUSD - Monthly amount in dollars
 * @returns Formatted string like "$79/month"
 */
export function formatMonthlyPrice(amountUSD: number): string {
  return `$${amountUSD}/month`;
}

/**
 * Format a monthly price with "/mo" suffix (compact).
 * @param amountUSD - Monthly amount in dollars
 * @returns Formatted string like "$79/mo"
 */
export function formatMonthlyPriceCompact(amountUSD: number): string {
  return `$${amountUSD}/mo`;
}

/**
 * Get the lowest paid plan price for marketing copy.
 * @returns The Starter plan's monthly USD amount
 */
export function getLowestPaidPlanPrice(): number {
  return PLANS.STARTER.monthlyUSD;
}

/**
 * Marketing copy: "Plans from $79/month, including up to 250 call minutes"
 * Use this for consistent messaging across public surfaces.
 */
export function getStandardPricingCopy(): string {
  const starter = PLANS.STARTER;
  return `Plans from ${formatMonthlyPrice(starter.monthlyUSD)}, including up to ${starter.approximateMinutes} call minutes`;
}

/**
 * Marketing copy (compact): "Plans from $79/mo"
 * Use for space-constrained contexts.
 */
export function getCompactPricingCopy(): string {
  return `Plans from ${formatMonthlyPriceCompact(PLANS.STARTER.monthlyUSD)}`;
}

/**
 * Narrative marketing copy: "Plans start at $79 a month"
 * Use in blog and long-form public content.
 */
export function getPlansStartAtCopy(): string {
  return `Plans start at ${formatPriceUSD(PLANS.STARTER.monthlyUSD)} a month`;
}

/**
 * All plan IDs in order (Free → Starter → Pro → Scale).
 */
export const PLAN_ORDER = ["free", "starter", "pro", "scale"] as const;

/**
 * Get plan details by ID.
 * @param planId - Plan identifier (lowercase)
 * @returns Plan pricing object or undefined if not found
 */
export function getPlanById(planId: string): PlanPricing | undefined {
  return Object.values(PLANS).find((p) => p.id === planId);
}
