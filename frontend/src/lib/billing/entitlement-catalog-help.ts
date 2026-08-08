/**
 * Admin-facing help text for entitlement catalog keys and plan catalog fields.
 */

export const ENTITLEMENT_CATALOG_HELP: Record<
  string,
  { summary: string; enforcement: string }
> = {
  max_agents: {
    summary: "Caps how many voice agents an organization can create.",
    enforcement:
      "Hard block on agent creation when the org is at the limit. Existing agents are kept.",
  },
  max_org_members: {
    summary: "Caps how many users can belong to the organization.",
    enforcement:
      "Hard block on inviting or adding members beyond the limit.",
  },
  max_phone_numbers: {
    summary: "Caps purchased Twilio phone numbers for the org.",
    enforcement:
      "Hard block on buying or assigning additional numbers.",
  },
  max_concurrent_calls: {
    summary: "Caps simultaneous active voice sessions.",
    enforcement:
      "Hard block when starting a new call would exceed the concurrent limit.",
  },
  included_credits_per_billing_period: {
    summary:
      "Credits included each billing period (monthly or annual, per Stripe subscription).",
    enforcement:
      "Granted on invoice paid / renewal. Does not block usage by itself — works with PAYG and credit balance rules.",
  },
  payg_credit_cap: {
    summary:
      "Maximum negative credit balance allowed when pay-as-you-go is enabled.",
    enforcement:
      "Hard block on usage that would exceed the PAYG cap.",
  },
  payg_enabled: {
    summary: "Allows usage after included credits are exhausted (billed as overage).",
    enforcement:
      "When off, voice usage stops once included credits are used unless top-up credits exist.",
  },
  credit_topup_enabled: {
    summary: "Allows purchasing one-time credit packs from billing UI.",
    enforcement: "Hides or disables credit pack checkout when off.",
  },
  premium_tools: {
    summary: "Grants access to premium platform tools on agents.",
    enforcement:
      "Tool connection or runtime checks reject premium tools when off.",
  },
  embed_widget: {
    summary: "Enables the public embeddable call button for the org.",
    enforcement: "Embed routes and widget config unavailable when off.",
  },
  custom_branding: {
    summary: "Enables white-label branding on the public org page.",
    enforcement: "Branding settings and public page customization gated when off.",
  },
};

export const PLAN_CATALOG_FIELD_HELP = {
  slug: "Stable identifier used in URLs, Stripe metadata, and APIs. Lowercase, no spaces.",
  displayName: "Customer-facing plan family name shown in admin and billing UI.",
  billingInterval:
    "How often Stripe bills this plan (monthly or annual). Stored on each version and used when creating the Stripe Price on publish.",
  displayLabel:
    "Version label for admins and legacy subscribers (e.g. “Starter v2 — March 2026”).",
  priceCents:
    "Price in cents for this version. A new Stripe Price is created on publish when none is linked yet.",
  stripeProductId:
    "Stripe Product ID (prod_…). Auto-created when you add a plan product. If auto-create failed, create the product in Stripe Dashboard and paste the ID here.",
  stripePriceId:
    "Stripe Price ID (price_…). Auto-created on publish. If auto-create failed, create the price in Stripe and paste the ID here before publishing.",
  draftSingle:
    "Only one draft version is allowed per plan product. Publish or delete the current draft before creating another.",
  sparseEntitlements:
    "Only entitlements you explicitly add are stored on this version. Omitted keys use catalog defaults at runtime.",
} as const;

export function entitlementHelpText(key: string): string {
  const entry = ENTITLEMENT_CATALOG_HELP[key];
  if (!entry) {
    return "Platform-defined limit or feature enforced by EntitlementService.";
  }
  return `${entry.summary} ${entry.enforcement}`;
}
