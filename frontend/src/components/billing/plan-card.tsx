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
    display_label: plan.display_label,
    product_name: plan.product_name,
    product_description: plan.product_description,
    billing_mode: plan.billing_mode,
    price_amount_cents: plan.price_amount_cents,
    currency: plan.currency,
    billing_interval: plan.billing_interval,
    entitlements: Object.entries(plan.entitlements).map(([key, value]) => ({
      key,
      label:
        plan.entitlement_metadata?.[key]?.display_name ??
        key.replace(/_/g, " ").replace(/\b\w/g, (character) => character.toUpperCase()),
      description: plan.entitlement_metadata?.[key]?.description?.trim() || null,
      value,
    })),
  };
}

/** Render the customer-facing plan card used by billing and admin preview. */
export function PlanCard({
  plan,
  badge,
  footer,
  className,
  testId,
}: PlanCardProps) {
  const features = plan.entitlements
    .map((entitlement): PlanCardFeature | null => {
      const { label, value } = entitlement;
      if (value.type === "unlimited") {
        return { ...entitlement, text: `${label}: Unlimited` };
      }
      if (typeof value.value === "boolean") {
        return value.value ? { ...entitlement, text: label } : null;
      }
      if (typeof value.value === "number") {
        return {
          ...entitlement,
          text: `${value.value.toLocaleString()} ${label}`,
        };
      }
      if (typeof value.value === "string" && value.value.trim()) {
        return { ...entitlement, text: `${value.value} ${label}` };
      }
      return { ...entitlement, text: label };
    })
    .filter((feature): feature is PlanCardFeature => feature !== null)
    .slice(0, 6);

  return (
    <Card className={cn("relative", className)} data-testid={testId}>
      <CardHeader>
        <CardTitle className="flex items-center justify-between gap-2">
          <span>{plan.display_label || plan.product_name}</span>
          {badge}
        </CardTitle>
        <CardDescription>
          {plan.product_description || "A plan for your organization."}
        </CardDescription>
        <div className="text-3xl font-bold">
          {formatPlanPrice(plan)}
          {plan.billing_mode === "paid" && (
            <span className="ml-1 text-sm font-normal text-muted-foreground">
              / {plan.billing_interval}
            </span>
          )}
        </div>
      </CardHeader>

      <CardContent>
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

      {footer ? <CardFooter className="flex-col gap-2">{footer}</CardFooter> : null}
    </Card>
  );
}
