"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowRight, Check, Loader2, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
} from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { billingService } from "@/services/billing-service";
import { friendlyPlanName } from "@/components/billing/plan-card";
import type { CustomerPlanVersion } from "@/types/billing";

export interface StepPlanSelectionProps {
  /** Organization receiving the selected plan. */
  organizationId: string;
  /** Called after a free plan is active and onboarding may finish. */
  onActivated: (planVersionId: string) => void;
  /** Optional callback used by the page to return to organization details. */
  onBack?: () => void;
  /** Error state from a cancelled or failed Stripe return. */
  paymentState?: "cancelled" | "failed" | null;
  /** Test seam and optional host override for redirecting to Stripe Checkout. */
  onRedirectToCheckout?: (checkoutUrl: string) => void;
}

type BillingIntervalTab = "monthly" | "annual";

/** Metered cost of one connected call minute, matching backend billing. */
export const CREDITS_PER_CALL_MINUTE = 10;

function formatPrice(plan: CustomerPlanVersion): string {
  if (plan.billing_mode === "free" || plan.price_amount_cents === 0) {
    return "Free";
  }
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: plan.currency,
  }).format(plan.price_amount_cents / 100);
}

function formatEntitlement(
  key: string,
  rawValue: Record<string, unknown>,
): string {
  const value = rawValue.value;
  // Show estimated call minutes while preserving credits as the billing unit.
  if (typeof value === "number" && key.startsWith("included_credits")) {
    const minutes = Math.floor(value / CREDITS_PER_CALL_MINUTE);
    return `Up to ${minutes.toLocaleString()} call minutes per billing period`;
  }
  const label = key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
  if (typeof value === "boolean") return value ? label : "";
  if (typeof value === "number") return `${value.toLocaleString()} ${label}`;
  return label;
}

/**
 * Founder onboarding plan step.
 *
 * The component deliberately has separate free and paid activation paths. A
 * free plan creates an application subscription directly; a paid plan creates
 * a Stripe Checkout session and leaves the page only after that session exists.
 */
export function StepPlanSelection({
  organizationId,
  onActivated,
  onBack,
  paymentState = null,
  onRedirectToCheckout,
}: StepPlanSelectionProps) {
  const [plans, setPlans] = useState<CustomerPlanVersion[]>([]);
  const [loadingPlans, setLoadingPlans] = useState(true);
  const [loadingPlanId, setLoadingPlanId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeInterval, setActiveInterval] =
    useState<BillingIntervalTab>("monthly");

  useEffect(() => {
    let cancelled = false;
    setLoadingPlans(true);
    setError(null);

    void billingService
      .getAvailablePlanVersions()
      .then((availablePlans) => {
        if (!cancelled) setPlans(availablePlans);
      })
      .catch((requestError) => {
        if (cancelled) return;
        const message =
          requestError instanceof Error
            ? requestError.message
            : "We could not load the available plans.";
        setError(message);
        toast.error(message);
      })
      .finally(() => {
        if (!cancelled) setLoadingPlans(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const sortedPlans = useMemo(
    () =>
      [...plans].sort((left, right) => {
        if (left.tier_rank !== right.tier_rank) {
          return left.tier_rank - right.tier_rank;
        }
        return left.billing_interval.localeCompare(right.billing_interval);
      }),
    [plans],
  );

  const plansByInterval = useMemo(
    () => ({
      monthly: sortedPlans.filter((plan) => plan.billing_interval !== "annual"),
      annual: sortedPlans.filter((plan) => plan.billing_interval === "annual"),
    }),
    [sortedPlans],
  );

  useEffect(() => {
    if (
      plansByInterval.monthly.length === 0 &&
      plansByInterval.annual.length > 0
    ) {
      setActiveInterval("annual");
    }
  }, [plansByInterval]);

  const handlePlanSelection = async (plan: CustomerPlanVersion) => {
    setLoadingPlanId(plan.id);
    setError(null);

    try {
      if (plan.billing_mode === "free") {
        await billingService.activateFreePlan(organizationId, plan.id);
        toast.success("Your free plan is active.");
        onActivated(plan.id);
        return;
      }

      const origin = window.location.origin;
      const result = await billingService.createVersionedSubscriptionCheckout({
        organization_id: organizationId,
        plan_version_id: plan.id,
        success_url: `${origin}/onboarding?payment=success&organization_id=${encodeURIComponent(organizationId)}&session_id={CHECKOUT_SESSION_ID}`,
        cancel_url: `${origin}/onboarding?payment=cancelled&organization_id=${encodeURIComponent(organizationId)}`,
      });

      if (onRedirectToCheckout) {
        onRedirectToCheckout(result.checkout_url);
      } else {
        window.location.assign(result.checkout_url);
      }
    } catch (requestError) {
      const message =
        requestError instanceof Error
          ? requestError.message
          : "We could not start plan activation.";
      setError(message);
      toast.error(message);
    } finally {
      setLoadingPlanId(null);
    }
  };

  /**
   * Render the plan cards for the currently selected billing interval.
   *
   * @param plansForInterval - Published plan versions for monthly or annual billing
   * @returns Plan cards with the existing free and paid activation actions
   */
  const renderPlanCards = (plansForInterval: CustomerPlanVersion[]) => (
    <div className="grid gap-4 md:grid-cols-2">
      {plansForInterval.map((plan) => {
        const isLoading = loadingPlanId === plan.id;
        const features = Object.entries(plan.entitlements)
          .map(([key, value]) => formatEntitlement(key, value))
          .filter(Boolean)
          .slice(0, 4);
        return (
          <Card
            key={plan.id}
            className={
              plan.billing_mode === "free"
                ? "border-blue-200 shadow-sm"
                : "border-slate-200 shadow-sm"
            }
            data-testid={`onboarding-plan-card-${plan.id}`}
          >
            <CardHeader className="space-y-3">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="mt-1 text-xl font-semibold text-gray-900">
                    {friendlyPlanName(plan)}
                  </h3>
                </div>
                {plan.billing_mode === "free" && (
                  <Badge variant="secondary">No card required</Badge>
                )}
              </div>
              <div className="text-3xl font-bold text-gray-950">
                {formatPrice(plan)}
                {plan.billing_mode === "paid" && (
                  <span className="ml-1 text-sm font-normal text-gray-500">
                    / {plan.billing_interval}
                  </span>
                )}
              </div>
              <p className="min-h-10 text-sm text-gray-500">
                {plan.product_description || "A plan for your organization."}
              </p>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm text-gray-700">
                {features.length > 0 ? (
                  features.map((feature) => (
                    <li key={feature} className="flex items-center gap-2">
                      <Check className="h-4 w-4 text-emerald-600" />
                      {feature}
                    </li>
                  ))
                ) : (
                  <li className="flex items-center gap-2">
                    <Check className="h-4 w-4 text-emerald-600" />
                    Core workspace access
                  </li>
                )}
              </ul>
            </CardContent>
            <CardFooter>
              <Button
                className="w-full"
                disabled={loadingPlanId !== null}
                onClick={() => void handlePlanSelection(plan)}
                data-testid={`onboarding-plan-select-${plan.id}`}
              >
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    {plan.billing_mode === "free"
                      ? "Activating..."
                      : "Opening checkout..."}
                  </>
                ) : (
                  <>
                    {plan.billing_mode === "free"
                      ? "Start with Free"
                      : "Continue to payment"}
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </>
                )}
              </Button>
            </CardFooter>
          </Card>
        );
      })}
    </div>
  );

  return (
    <div className="space-y-6" data-testid="onboarding-plan-selection">
      <div>
        <div className="flex items-center gap-2 text-sm font-semibold uppercase tracking-[0.18em] text-blue-600">
          <ShieldCheck className="h-4 w-4" />
          Workspace access
        </div>
        <h2 className="mt-2 text-2xl font-bold text-gray-900">Choose a plan</h2>
        <p className="mt-1 text-gray-500">
          Activate your workspace before exploring agents, calls, and
          integrations.
        </p>
      </div>

      <div className="rounded-lg border bg-muted/40 p-4 text-sm text-muted-foreground">
        Paid plans include one US local number on request and our standard voice
        profile. Additional US local numbers use 80 credits/month ($2 equivalent)
        from the same balance as calls; other number types show their rate before
        purchase. There is no fixed number limit. Optional voice profiles may
        need a provider account, which may bill you directly. You can connect a
        Twilio number you own at no platform rental cost.
        <br />
        <Link
          className="font-medium text-primary underline underline-offset-4"
          href="/request-demo"
        >
          Need more volume or several locations? Talk with us.
        </Link>
      </div>

      {paymentState === "cancelled" && (
        <Alert className="border-amber-200 bg-amber-50 text-amber-900">
          <AlertDescription>
            Checkout was cancelled. Your organization details are saved—choose a
            plan whenever you&apos;re ready.
          </AlertDescription>
        </Alert>
      )}
      {paymentState === "failed" && (
        <Alert className="border-red-200 bg-red-50 text-red-900">
          <AlertDescription>
            We could not confirm that payment. Choose the plan again or try a
            different payment method.
          </AlertDescription>
        </Alert>
      )}
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {loadingPlans ? (
        <div className="flex items-center justify-center rounded-xl border border-blue-100 bg-blue-50/60 py-16 text-blue-700">
          <Loader2 className="h-5 w-5 animate-spin" />
          <span className="ml-2">Loading plans...</span>
        </div>
      ) : sortedPlans.length === 0 ? (
        <Alert variant="destructive">
          <AlertDescription>
            No plans are available right now. Please try again shortly.
          </AlertDescription>
        </Alert>
      ) : (
        <Tabs
          value={activeInterval}
          onValueChange={(value) =>
            setActiveInterval(value as BillingIntervalTab)
          }
          className="w-full"
        >
          <TabsList className="mb-6" aria-label="Billing interval">
            <TabsTrigger value="monthly">Monthly</TabsTrigger>
            <TabsTrigger value="annual">Annually</TabsTrigger>
          </TabsList>
          <TabsContent value="monthly">
            {plansByInterval.monthly.length > 0 ? (
              renderPlanCards(plansByInterval.monthly)
            ) : (
              <Alert>
                <AlertDescription>
                  No monthly plans are available right now.
                </AlertDescription>
              </Alert>
            )}
          </TabsContent>
          <TabsContent value="annual">
            {plansByInterval.annual.length > 0 ? (
              renderPlanCards(plansByInterval.annual)
            ) : (
              <Alert>
                <AlertDescription>
                  No annual plans are available right now.
                </AlertDescription>
              </Alert>
            )}
          </TabsContent>
        </Tabs>
      )}

      {onBack && (
        <Button
          variant="ghost"
          onClick={onBack}
          disabled={loadingPlanId !== null}
        >
          Back to organization details
        </Button>
      )}
    </div>
  );
}
