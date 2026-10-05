"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  formatPlanPrice,
  friendlyPlanName,
  PlanCard,
  toPlanCardData,
} from "@/components/billing/plan-card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AlertTriangle, ArrowRight, Loader2 } from "lucide-react";
import { billingService } from "@/services/billing-service";
import type {
  CustomerPlanVersion,
  OrganizationSubscriptionWithPlan,
  PlanChangePreview,
} from "@/types/billing";
import { toast } from "sonner";

type BillingIntervalTab = "monthly" | "annual";

function planFamilySlug(slug: string): string {
  return slug
    .toLowerCase()
    .replace(/(?:[-_:]?(?:version|v)\d+)$/, "")
    .replace(/(?:[-_:]?(?:monthly|month|annual|annually|year|yearly))$/, "")
    .replace(/(?:[-_:]?plan)$/, "")
    .replace(/[^a-z0-9]/g, "");
}

/**
 * Props for the customer-facing internal plan catalog.
 */
export interface PlanSelectionProps {
  /** Organization that will receive the selected plan. */
  organizationId: string;
  /** Current organization subscription, when one exists. */
  currentSubscription?: OrganizationSubscriptionWithPlan | null;
  /** Called after a free plan is activated or checkout is prepared. */
  onPlanSelected?: (plan: CustomerPlanVersion) => void;
  /** Optional redirect seam for tests or hosts that own navigation. */
  onRedirectToCheckout?: (checkoutUrl: string) => void;
  /** Optional callback after a plan transition is applied or scheduled. */
  onPlanChangeConfirmed?: () => void;
}

/**
 * Customer plan selector backed by the platform plan product/version catalog.
 *
 * Free plans are activated directly in the application. Paid plans use the
 * immutable published version's Stripe Price through the version-aware
 * checkout endpoint; the browser never chooses a Stripe product or price.
 */
export function PlanSelection({
  organizationId,
  currentSubscription,
  onPlanSelected,
  onRedirectToCheckout,
  onPlanChangeConfirmed,
}: PlanSelectionProps) {
  const [plans, setPlans] = useState<CustomerPlanVersion[]>([]);
  const [loadingPlans, setLoadingPlans] = useState(true);
  const [loadingPlanId, setLoadingPlanId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<PlanChangePreview | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [activeInterval, setActiveInterval] =
    useState<BillingIntervalTab>("monthly");
  const targetCreditValue =
    preview?.target_plan.entitlements.included_credits_per_billing_period
      ?.value;
  const targetIncludedCredits =
    typeof targetCreditValue === "number" ? targetCreditValue : null;

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
        if (left.product_slug !== right.product_slug) {
          return left.product_slug.localeCompare(right.product_slug);
        }
        return left.billing_interval.localeCompare(right.billing_interval);
      }),
    [plans],
  );

  const plansByInterval = useMemo(() => {
    const monthly = sortedPlans.filter(
      (plan) => plan.billing_mode === "paid" && plan.billing_interval !== "annual",
    );
    const annual = sortedPlans.filter((plan) => {
      if (plan.billing_mode !== "paid" || plan.billing_interval !== "annual") {
        return false;
      }
      const annualFamily = planFamilySlug(plan.product_slug);
      return monthly.some((monthlyPlan) => {
        const monthlyFamily = planFamilySlug(monthlyPlan.product_slug);
        const monthlyCredits = monthlyPlan.entitlements
          .included_credits_per_billing_period?.value;
        const annualCredits = plan.entitlements
          .included_credits_per_billing_period?.value;
        return (
          monthlyFamily === annualFamily &&
          monthlyPlan.currency.toUpperCase() === plan.currency.toUpperCase() &&
          plan.price_amount_cents === monthlyPlan.price_amount_cents * 10 &&
          typeof monthlyCredits === "number" &&
          monthlyCredits > 0 &&
          typeof annualCredits === "number" &&
          annualCredits === monthlyCredits * 12
        );
      });
    });
    return {
      monthly: sortedPlans.filter((plan) => plan.billing_interval !== "annual"),
      annual,
    };
  }, [sortedPlans]);

  useEffect(() => {
    if (
      plansByInterval.monthly.length === 0 &&
      plansByInterval.annual.length > 0
    ) {
      setActiveInterval("annual");
    }
  }, [plansByInterval]);

  const hasActiveSubscription = ["active", "trial"].includes(
    currentSubscription?.status ?? "",
  );

  const isCurrentPlan = (plan: CustomerPlanVersion): boolean =>
    currentSubscription?.plan_version_id === plan.id;

  const planLabel = (plan: CustomerPlanVersion): string => friendlyPlanName(plan);

  const handlePlanSelection = async (plan: CustomerPlanVersion) => {
    if (isCurrentPlan(plan)) return;

    setLoadingPlanId(plan.id);
    setError(null);

    try {
      if (hasActiveSubscription) {
        const nextPreview = await billingService.previewPlanChange(
          organizationId,
          plan.id,
        );
        setPreview(nextPreview);
        return;
      }

      if (plan.billing_mode === "free") {
        await billingService.activateFreePlan(organizationId, plan.id);
        toast.success("Your free plan is active.");
        onPlanSelected?.(plan);
        return;
      }

      const origin = window.location.origin;
      const result = await billingService.createVersionedSubscriptionCheckout({
        organization_id: organizationId,
        plan_version_id: plan.id,
        success_url: `${origin}/organization/billing?org_id=${encodeURIComponent(organizationId)}&tab=manage&payment=success&session_id={CHECKOUT_SESSION_ID}&plan_version_id=${encodeURIComponent(plan.id)}`,
        cancel_url: `${origin}/organization/billing?org_id=${encodeURIComponent(organizationId)}&tab=plans&payment=cancelled`,
      });

      onPlanSelected?.(plan);
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

  const handlePlanChangeConfirmation = async () => {
    if (!preview) return;

    setConfirming(true);
    setError(null);
    try {
      const origin = window.location.origin;
      const result = await billingService.confirmPlanChange({
        organization_id: organizationId,
        transition_id: preview.transition_id,
        target_plan_version_id: preview.target_plan.id,
        success_url: `${origin}/organization/billing?org_id=${encodeURIComponent(organizationId)}&tab=overview&payment=success&session_id={CHECKOUT_SESSION_ID}&plan_version_id=${encodeURIComponent(preview.target_plan.id)}`,
        cancel_url: `${origin}/organization/billing?org_id=${encodeURIComponent(organizationId)}&tab=plans&payment=cancelled`,
      });

      setPreview(null);
      onPlanSelected?.(preview.target_plan);
      onPlanChangeConfirmed?.();

      if (result.checkout_url) {
        if (onRedirectToCheckout) {
          onRedirectToCheckout(result.checkout_url);
        } else {
          window.location.assign(result.checkout_url);
        }
        return;
      }

      toast.success(
        result.status === "scheduled"
          ? "Your plan change is scheduled."
          : "Your plan has been changed.",
      );
    } catch (requestError) {
      const message =
        requestError instanceof Error
          ? requestError.message
          : "We could not confirm this plan change.";
      setError(message);
      toast.error(message);
    } finally {
      setConfirming(false);
    }
  };

  if (loadingPlans) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin" />
        <span className="ml-2">Loading available plans...</span>
      </div>
    );
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }

  if (plans.length === 0) {
    return (
      <div className="py-12 text-center">
        <p className="text-muted-foreground">
          No published plans are available right now.
        </p>
      </div>
    );
  }

  const plansForInterval = plansByInterval[activeInterval];
  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-xl font-semibold">Manage your plan</h2>
        <p className="text-sm text-muted-foreground">
          Plans are shown from the smallest to the most capable. You can choose
          any eligible plan, and we&apos;ll explain the timing and billing
          impact before confirming it.
        </p>
      </div>

      <div className="rounded-lg border bg-muted/30 p-4 text-sm text-muted-foreground">
        <p>
          Every paid plan includes one US local business number when you request
          it. Additional platform-provided US local numbers use 80 credits per
          month ($2 equivalent each) from the same balance used for calls, so
          they can reduce available call time. Paid plans do not set a fixed
          count limit for numbers. Connecting a Twilio number you already own
          has no platform rental charge.
        </p>
        <p className="mt-2">
          All plans include our standard voice profile. Optional provider voices
          use BYOK (bring your own keys): you connect your provider account, the
          provider bills you directly, and 24x7 AI does not charge for that
          provider&apos;s voice usage. Plan call minutes and platform phone-number
          rentals still use your 24x7 AI credit balance.
        </p>
        <p className="mt-2">
          Need more volume or several locations?{" "}
          <Link
            className="font-medium text-primary underline underline-offset-4"
            href={`/contact?org_id=${encodeURIComponent(organizationId)}`}
          >
            Talk with us about a tailored plan
          </Link>
          .
        </p>
      </div>

      {plansByInterval.monthly.length > 0 &&
        plansByInterval.annual.length > 0 && (
          <div className="flex justify-center gap-2">
            <Button
              variant={activeInterval === "monthly" ? "default" : "outline"}
              onClick={() => setActiveInterval("monthly")}
            >
              Monthly
            </Button>
            <Button
              variant={activeInterval === "annual" ? "default" : "outline"}
              onClick={() => setActiveInterval("annual")}
            >
              Annual · 2 months free
            </Button>
          </div>
        )}

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-4">
        {plansForInterval.map((plan) => {
          const isLoading = loadingPlanId === plan.id;
          const current = isCurrentPlan(plan);

          return (
            <PlanCard
              key={plan.id}
              plan={toPlanCardData(plan)}
              badge={
                current ? (
                  <Badge variant="default">Current plan</Badge>
                ) : plan.billing_interval === "annual" ? (
                  <Badge variant="secondary">2 months free</Badge>
                ) : null
              }
              className={current ? "border-primary shadow-lg" : undefined}
              testId={`billing-plan-card-${plan.id}`}
              footer={
                <>
                <Button
                  className="w-full"
                  disabled={loadingPlanId !== null || confirming || current}
                  onClick={() => void handlePlanSelection(plan)}
                  data-testid={`billing-plan-select-${plan.id}`}
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      {hasActiveSubscription
                        ? "Loading preview..."
                        : plan.billing_mode === "free"
                          ? "Activating..."
                          : "Opening checkout..."}
                    </>
                  ) : current ? (
                    "Current plan"
                  ) : hasActiveSubscription ? (
                    "Review plan change"
                  ) : (
                    <>
                      {plan.billing_mode === "free"
                        ? "Start with Free"
                        : "Continue to payment"}
                      <ArrowRight className="ml-2 h-4 w-4" />
                    </>
                  )}
                </Button>
                {plan.billing_mode === "free" ? (
                  <p className="text-center text-xs text-muted-foreground">
                    No payment method required
                  </p>
                ) : null}
                </>
              }
            />
          );
        })}
      </div>

      <Dialog
        open={Boolean(preview)}
        onOpenChange={(open) => {
          if (!open && !confirming) setPreview(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Review plan change</DialogTitle>
            <DialogDescription>
              {preview
                ? `Change from ${planLabel(preview.current_plan)} to ${planLabel(preview.target_plan)}`
                : "Review the plan change before confirming."}
            </DialogDescription>
          </DialogHeader>

          {preview ? (
            <div className="space-y-4 text-sm">
              <div className="grid grid-cols-2 gap-3 rounded-lg border p-4">
                <div>
                  <div className="text-muted-foreground">Current price</div>
                  <div className="font-medium">
                    {formatPlanPrice(toPlanCardData(preview.current_plan))}
                  </div>
                </div>
                <div>
                  <div className="text-muted-foreground">New price</div>
                  <div className="font-medium">
                    {formatPlanPrice(toPlanCardData(preview.target_plan))}
                  </div>
                </div>
              </div>

              <Alert>
                <AlertDescription>
                  {preview.effective_mode === "checkout"
                    ? "You will continue to secure checkout. Your new plan starts after payment succeeds and the billing webhook confirms it."
                    : preview.effective_mode === "immediate"
                      ? "Your new plan starts now. Stripe will prorate the remaining billing period."
                      : `Your current plan stays active until ${preview.effective_at ? new Date(preview.effective_at).toLocaleDateString("en-US") : "the end of the billing period"}.`}
                </AlertDescription>
              </Alert>

              {targetIncludedCredits !== null ? (
                <p>
                  <strong>
                    {targetIncludedCredits.toLocaleString()}
                  </strong>{" "}
                  included credits per billing period (up to{" "}
                  {`${Math.floor(targetIncludedCredits / 10).toLocaleString()} call minutes`}
                  {preview.effective_mode === "immediate"
                    ? preview.current_plan.billing_interval !==
                      preview.target_plan.billing_interval
                      ? "). This plan-credit balance refreshes after payment for this plan change succeeds."
                      : "). This plan-credit balance refreshes after your next renewal payment succeeds. Your current plan credits remain available until then."
                    : preview.effective_mode === "checkout"
                      ? "). These credits are added after checkout payment succeeds."
                      : "). This plan-credit balance refreshes after the first payment for the scheduled plan succeeds."}{" "}
                  Purchased credits remain available.
                </p>
              ) : (
                <p>
                  Purchased credits remain available and are not changed by this
                  plan transition.
                </p>
              )}
            </div>
          ) : null}

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setPreview(null)}
              disabled={confirming}
            >
              Keep current plan
            </Button>
            <Button
              onClick={() => void handlePlanChangeConfirmation()}
              disabled={confirming}
            >
              {confirming ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Confirming...
                </>
              ) : preview?.effective_mode === "checkout" ? (
                "Continue to payment"
              ) : preview?.effective_mode === "period_end" ? (
                "Schedule change"
              ) : (
                "Confirm plan change"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
