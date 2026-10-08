"use client";

import * as React from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { BillingMode, CustomerPlanVersion } from "@/types/billing";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Check, CircleHelp } from "lucide-react";

export interface PlanCardEntitlement {
  /** Stable catalog key used as the React list key. */
  key: string;
  /** Human-readable label shown to customers. */
  label: string;
  /** Optional customer-facing explanation shown in the details tooltip. */
  description: string | null;
  /** Stored catalog value object. */
  value: Record<string, unknown>;
}

export interface PlanCardData {
  id: string;
  product_slug?: string;
  display_label: string | null;
  product_name: string;
  product_description: string | null;
  billing_mode: BillingMode;
  price_amount_cents: number;
  currency: string;
  billing_interval: string;
  entitlements: PlanCardEntitlement[];
}

interface PlanCardProps {
  /** Published or draft plan data to render. */
  plan: PlanCardData;
  /** Optional badge rendered beside the plan name. */
  badge?: React.ReactNode;
  /** Optional action area rendered in the card footer. */
  footer?: React.ReactNode;
  /** Additional card classes for the host surface. */
  className?: string;
  /** Optional test id for customer and admin preview cards. */
  testId?: string;
}

type PlanCardFeature = PlanCardEntitlement & { text: string };

type PlanPriceInput = Pick<
  PlanCardData,
  "billing_mode" | "price_amount_cents" | "currency"
>;

/** Format a plan price using the same rules on customer and preview cards. */
export function formatPlanPrice(plan: PlanPriceInput): string {
  if (plan.billing_mode === "free" || plan.price_amount_cents === 0) {
    return "Free";
  }

  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: plan.currency,
  }).format(plan.price_amount_cents / 100);
}

/** Convert a customer catalog response to the shared plan-card shape. */
export function toPlanCardData(plan: CustomerPlanVersion): PlanCardData {
  return {
    id: plan.id,
    product_slug: plan.product_slug,
    display_label: plan.display_label,
    product_name: plan.product_name,
    product_description: plan.product_description,
    billing_mode: plan.billing_mode,
    price_amount_cents: plan.price_amount_cents,
    currency: plan.currency,
    billing_interval: plan.billing_interval,
    entitlements: Object.entries(plan.entitlements ?? {}).map(([key, value]) => ({
      key,
      label:
        plan.entitlement_metadata?.[key]?.display_name ??
        key.replace(/_/g, " ").replace(/\b\w/g, (character) => character.toUpperCase()),
      description: plan.entitlement_metadata?.[key]?.description?.trim() || null,
      value:
        key === "max_agents" &&
        value.type === "integer" &&
        typeof value.value === "number" &&
        value.value <= 0
          ? { type: "unlimited" }
          : value,
    })),
  };
}

const FRIENDLY_PLAN_NAMES: Record<string, string> = {
  free: "Free",
  starter: "Starter",
  pro: "Pro",
  scale: "Scale",
};

const CUSTOMER_PLAN_DESCRIPTIONS: Record<string, string> = {
  starter: "For solo owners and small shops handling a steady flow of calls.",
  pro: "For busy teams with higher call volumes and custom branding needs.",
  scale: "For larger, multi-location teams handling high call volumes.",
};

/** Reduce a versioned catalog slug to its stable plan family. */
function normalizedPlanSlug(productSlug?: string): string {
  return (productSlug ?? "")
    .toLowerCase()
    .replace(/(?:[-_:]?(?:version|v)\d+)$/, "")
    .replace(/(?:[-_:]?(?:monthly|month|annual|annually|year|yearly))$/, "")
    .replace(/(?:[-_:]?plan)$/, "")
    .replace(/[^a-z0-9]/g, "");
}

/** Return a customer-safe plan name without versioning or billing suffixes. */
export function friendlyPlanName(plan: {
  product_slug?: string;
  product_name: string;
  display_label: string | null;
}): string {
  const slug = normalizedPlanSlug(plan.product_slug);
  if (FRIENDLY_PLAN_NAMES[slug]) return FRIENDLY_PLAN_NAMES[slug];

  const rawName = plan.display_label || plan.product_name || "Plan";
  const cleaned = rawName
    .replace(/\s*[:—-]\s*(?:month|monthly|annual|annually|year|yearly)\b.*$/i, "")
    .replace(/\s+(?:month|monthly|annual|annually|year|yearly)(?:\s+v(?:ersion)?\s*\d+)?\s*$/i, "")
    .replace(/\s+v(?:ersion)?\s*\d+\b.*$/i, "")
    .replace(/\s+plan\s*$/i, "")
    .trim();
  const cleanedSlug = cleaned.toLowerCase().replace(/[^a-z0-9]/g, "");
  return FRIENDLY_PLAN_NAMES[cleanedSlug] ?? (cleaned || "Plan");
}

/** Use launch copy when a standard plan still has the generic catalog text. */
function customerPlanDescription(plan: PlanCardData): string {
  const description = plan.product_description?.trim() ?? "";
  const standardDescription = CUSTOMER_PLAN_DESCRIPTIONS[
    normalizedPlanSlug(plan.product_slug)
  ];
  const isGenericDescription =
    !description || /^a plan for your organization\.?$/i.test(description);

  if (standardDescription && isGenericDescription) return standardDescription;
  return description || "A plan for your organization.";
}

/** Remove internal interval/version labels from an entitlement label. */
export function friendlyPlanLabel(
  label: string | null | undefined,
  productSlug?: string | null,
): string {
  if (!label?.trim()) return "Plan";
  return friendlyPlanName({
    product_slug: productSlug ?? undefined,
    product_name: label,
    display_label: label,
  });
}

function entitlementFeatureText(
  entitlement: PlanCardEntitlement,
  billingInterval: string,
): string | null {
  const { key, label, value } = entitlement;
  if (value.type === "unlimited") {
    if (key === "max_phone_numbers") return "Unlimited phone numbers";
    return `${label}: Unlimited`;
  }
  if (typeof value.value === "boolean") {
    if (!value.value) return null;
    const knownFeatureLabels: Record<string, string> = {
      credit_topup_enabled: "Additional call credits available",
      embed_widget: "Website call widget",
      custom_branding: "Custom branding",
      payg_enabled: "Continue usage with pay-as-you-go credits",
    };
    return knownFeatureLabels[key] ?? label;
  }
  if (typeof value.value === "number") {
    if (value.value <= 0) return null;
    if (key === "included_credits_per_billing_period") {
      const minutes = Math.floor(value.value / 10);
      if (billingInterval === "annual") {
        const monthlyAverage = Math.floor(minutes / 12);
        return `Up to ${minutes.toLocaleString()} call minutes per year (${monthlyAverage.toLocaleString()}/month average; ${value.value.toLocaleString()} annual credits)`;
      }
      return `Up to ${minutes.toLocaleString()} call minutes per month (${value.value.toLocaleString()} credits)`;
    }
    if (key === "max_agents") {
      return `Up to ${value.value} voice agent${value.value === 1 ? "" : "s"}`;
    }
    if (key === "max_org_members") {
      return `Up to ${value.value} team member${value.value === 1 ? "" : "s"}`;
    }
    if (key === "max_phone_numbers") return `Up to ${value.value} phone numbers`;
    return `${value.value.toLocaleString()} ${label}`;
  }
  if (typeof value.value === "string" && value.value.trim()) {
    return `${value.value} ${label}`;
  }
  return label;
}

/** Render the customer-facing plan card used by billing and admin preview. */
export function PlanCard({
  plan,
  badge,
  footer,
  className,
  testId,
}: PlanCardProps) {
  const entitledFeatures = plan.entitlements
    .map((entitlement): PlanCardFeature | null => {
      const text = entitlementFeatureText(entitlement, plan.billing_interval);
      return text ? { ...entitlement, text } : null;
    })
    .filter((feature): feature is PlanCardFeature => feature !== null);
  // Only advertise capabilities the published plan version explicitly grants.
  const features = entitledFeatures.slice(0, 6);

  return (
    <Card
      className={cn("relative h-full flex-col", className)}
      data-testid={testId}
    >
      <CardHeader className="flex min-h-[13rem] flex-col">
        <CardTitle className="flex min-h-6 items-center justify-between gap-2">
          <span>{friendlyPlanName(plan)}</span>
          {badge}
        </CardTitle>
        <CardDescription className="line-clamp-3 min-h-[3.75rem]">
          {customerPlanDescription(plan)}
        </CardDescription>
        <div className="mt-auto whitespace-nowrap text-3xl font-bold leading-none">
          {formatPlanPrice(plan)}
          {plan.billing_mode === "paid" && (
            <span className="ml-1 text-sm font-normal text-muted-foreground">
              / {plan.billing_interval === "annual" ? "year" : "month"}
            </span>
          )}
        </div>
      </CardHeader>

      <CardContent className="flex-1">
        <TooltipProvider delayDuration={300}>
          <ul className="space-y-2 text-sm text-muted-foreground">
            {features.length > 0 ? (
              features.map((feature) => (
                <li key={feature.key} className="flex items-center gap-2">
                  <Check className="h-4 w-4 text-emerald-600" />
                  <span>{feature.text}</span>
                  {feature.description ? (
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <button
                          type="button"
                          className="inline-flex shrink-0 text-muted-foreground transition-colors hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                          aria-label={`More information about ${feature.label}`}
                        >
                          <CircleHelp className="h-3.5 w-3.5" aria-hidden="true" />
                        </button>
                      </TooltipTrigger>
                      <TooltipContent className="max-w-xs text-sm leading-relaxed">
                        {feature.description}
                      </TooltipContent>
                    </Tooltip>
                  ) : null}
                </li>
              ))
            ) : (
              <li className="flex items-center gap-2">
                <Check className="h-4 w-4 text-emerald-600" />
                Core workspace access
              </li>
            )}
          </ul>
        </TooltipProvider>
      </CardContent>

      {footer ? (
        <CardFooter
          className="mt-auto min-h-[5rem] flex-col items-stretch justify-start gap-2 pt-0"
        >
          {footer}
        </CardFooter>
      ) : null}
    </Card>
  );
}
