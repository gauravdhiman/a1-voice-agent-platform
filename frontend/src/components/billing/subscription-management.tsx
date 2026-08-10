"use client";

import React, { useEffect, useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Calendar,
  Users,
  Zap,
  AlertTriangle,
  CheckCircle,
  Coins,
  ExternalLink,
  Settings,
  Loader2,
  Info,
  ArrowRight,
} from "lucide-react";
import { billingService } from "@/services/billing-service";
import { CancelSubscriptionDialog } from "@/components/billing/cancel-subscription-dialog";
import { PlanMigrationBanner } from "@/components/billing/plan-migration-banner";
import { OrganizationSubscriptionWithPlan } from "@/types/billing";
import type { OrgEntitlements } from "@/types/billing";
import { toast } from "sonner";
import { format } from "date-fns";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface SubscriptionManagementProps {
  organizationId: string;
  subscription: OrganizationSubscriptionWithPlan;
  onSubscriptionUpdated?: () => void;
  /** Opens the internal plan catalog for any eligible plan change. */
  onChangePlan?: () => void;
  /** Opens the Credits tab at the purchase section. */
  onBuyCredits?: () => void;
}

export function SubscriptionManagement({
  organizationId,
  subscription,
  onSubscriptionUpdated,
  onChangePlan,
  onBuyCredits,
}: SubscriptionManagementProps) {
  const [cancelingSubscription, setCancelingSubscription] = useState(false);
  const [reactivatingSubscription, setReactivatingSubscription] =
    useState(false);
  const [openingPortal, setOpeningPortal] = useState(false);
  const [cancelDialogOpen, setCancelDialogOpen] = useState(false);
  const [entitlements, setEntitlements] = useState<OrgEntitlements | null>(
    null,
  );

  useEffect(() => {
    let cancelled = false;
    billingService
      .getOrganizationEntitlements(organizationId)
      .then((data) => {
        if (!cancelled) setEntitlements(data);
      })
      .catch((error) => {
        console.error("Failed to load entitlements:", error);
      });
    return () => {
      cancelled = true;
    };
  }, [organizationId, subscription.updated_at]);

  const refreshEntitlements = () => {
    billingService
      .getOrganizationEntitlements(organizationId)
      .then(setEntitlements)
      .catch((error) =>
        console.error("Failed to refresh entitlements:", error),
      );
  };

  const handleCancelSubscription = async () => {
    setCancelDialogOpen(true);
  };

  const handleCancelConfirm = async () => {
    try {
      setCancelingSubscription(true);
      await billingService.cancelSubscription(organizationId);
      toast.success(
        "Subscription will be cancelled at end of your billing period",
      );
      setCancelDialogOpen(false);
      onSubscriptionUpdated?.();
    } catch (error) {
      console.error("Failed to cancel subscription:", error);
      toast.error("Failed to cancel subscription");
      throw error;
    } finally {
      setCancelingSubscription(false);
    }
  };

  const handleReactivateSubscription = async () => {
    setReactivatingSubscription(true);

    try {
      await billingService.reactivateSubscription(organizationId);
      toast.success("Subscription reactivated successfully");
      onSubscriptionUpdated?.();
    } catch (error) {
      console.error("Failed to reactivate subscription:", error);
      toast.error("Failed to reactivate subscription");
    } finally {
      setReactivatingSubscription(false);
    }
  };

  const handleOpenCustomerPortal = async () => {
    setOpeningPortal(true);

    try {
      const { portal_url } = await billingService.createCustomerPortal(
        organizationId,
        window.location.href,
      );
      window.open(portal_url, "_blank");
    } catch (error) {
      console.error("Failed to open customer portal:", error);
      toast.error("Failed to open billing portal");
    } finally {
      setOpeningPortal(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "active":
        return "bg-green-100 text-green-800 border-green-200";
      case "trial":
        return "bg-blue-100 text-blue-800 border-blue-200";
      case "past_due":
        return "bg-yellow-100 text-yellow-800 border-yellow-200";
      case "cancelled":
      case "expired":
        return "bg-red-100 text-red-800 border-red-200";
      default:
        return "bg-gray-100 text-gray-800 border-gray-200";
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "active":
        return <CheckCircle className="w-4 h-4" />;
      case "trial":
        return <Zap className="w-4 h-4" />;
      case "past_due":
      case "cancelled":
      case "expired":
        return <AlertTriangle className="w-4 h-4" />;
      default:
        return null;
    }
  };

  const formatDate = (date: Date | string | null) => {
    if (!date) return "N/A";
    return format(new Date(date), "MMM dd, yyyy");
  };

  const isTrialActive =
    subscription.status === "trial" &&
    subscription.trial_end &&
    new Date(subscription.trial_end) > new Date();
  const isSubscriptionCancelled = subscription.cancel_at_period_end;
  const isSubscriptionActive = ["active", "trial"].includes(
    subscription.status,
  );
  const isFreePlan = subscription.metadata?.billing_mode === "free";
  const planName =
    subscription.plan?.name ?? (isFreePlan ? "Free plan" : "No plan");
  const canManageBilling =
    Boolean(subscription.stripe_customer_id) && !isFreePlan;

  return (
    <div className="space-y-6">
      {entitlements ? (
        <PlanMigrationBanner
          organizationId={organizationId}
          entitlements={entitlements}
          onMigrated={() => {
            refreshEntitlements();
            onSubscriptionUpdated?.();
          }}
        />
      ) : null}

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2 flex-wrap">
                Current Subscription
                <Badge
                  className={`${getStatusColor(
                    subscription.status,
                  )} flex items-center gap-1`}
                >
                  {getStatusIcon(subscription.status)}
                  {subscription.status.charAt(0).toUpperCase() +
                    subscription.status.slice(1)}
                </Badge>
                {entitlements?.plan_version_label ? (
                  <Badge variant="outline" className="font-normal">
                    {entitlements.plan_version_label}
                    {entitlements.is_legacy_version ? " (legacy)" : ""}
                  </Badge>
                ) : null}
              </CardTitle>
              <CardDescription>
                Manage your subscription plan and billing settings
              </CardDescription>
            </div>
            <div className="flex flex-wrap items-center justify-end gap-2">
              {onChangePlan ? (
                <Button onClick={onChangePlan}>
                  Change plan
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              ) : null}
              {onBuyCredits ? (
                <Button variant="outline" onClick={onBuyCredits}>
                  <Coins className="mr-2 h-4 w-4" />
                  Buy credits
                </Button>
              ) : null}
              {canManageBilling ? (
                <TooltipProvider delayDuration={300}>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant="outline"
                        onClick={handleOpenCustomerPortal}
                        disabled={openingPortal}
                      >
                        {openingPortal ? (
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        ) : (
                          <Settings className="w-4 h-4 mr-2" />
                        )}
                        Manage billing
                        <ExternalLink className="w-4 h-4 ml-2" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent className="max-w-xs text-sm">
                      Open Stripe to update payment methods, invoices, billing
                      address, or the subscription.
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              ) : null}
            </div>
          </div>
        </CardHeader>

        <CardContent className="space-y-6">
          {/* Plan Details */}
          {subscription.plan || isFreePlan ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="space-y-2">
                <div className="text-sm text-muted-foreground">Plan</div>
                <div className="font-semibold">{planName}</div>
              </div>

              {subscription.plan ? (
                <div className="space-y-2">
                  <div className="text-sm text-muted-foreground">Price</div>
                  <div className="font-semibold">
                    ${(subscription.plan.price_amount / 100).toFixed(2)}/
                    {subscription.plan.interval}
                  </div>
                </div>
              ) : null}

              {subscription.plan ? (
                <div className="space-y-2">
                  <div className="text-sm text-muted-foreground flex items-center gap-1">
                    <Zap className="w-4 h-4" />
                    Credits Included
                  </div>
                  <div className="font-semibold">
                    {subscription.plan.included_credits.toLocaleString()}
                  </div>
                </div>
              ) : null}

              {subscription.plan?.max_users && (
                <div className="space-y-2">
                  <div className="text-sm text-muted-foreground flex items-center gap-1">
                    <Users className="w-4 h-4" />
                    Max Users
                  </div>
                  <div className="font-semibold">
                    {subscription.plan.max_users}
                  </div>
                </div>
              )}
            </div>
          ) : null}

          {/* Billing Dates */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {subscription.current_period_start && (
              <div className="space-y-2">
                <div className="text-sm text-muted-foreground flex items-center gap-1">
                  <Calendar className="w-4 h-4" />
                  Current Period Start
                </div>
                <div className="font-semibold">
                  {formatDate(subscription.current_period_start)}
                </div>
              </div>
            )}

            {subscription.current_period_end && (
              <div className="space-y-2">
                <div className="text-sm text-muted-foreground flex items-center gap-1">
                  <Calendar className="w-4 h-4" />
                  {isSubscriptionCancelled
                    ? "Cancellation Date"
                    : "Next Billing Date"}
                </div>
                <div className="font-semibold">
                  {formatDate(subscription.current_period_end)}
                </div>
              </div>
            )}
          </div>

          {/* Trial Information */}
          {isTrialActive && (
            <Alert>
              <Zap className="h-4 w-4" />
              <AlertDescription>
                You&apos;re currently in your free trial period. Your trial ends
                on {formatDate(subscription.trial_end)} and you&apos;ll be
                charged for your subscription.
              </AlertDescription>
            </Alert>
          )}

          {/* Cancellation Warning */}
          {isSubscriptionCancelled && (
            <Alert className="border-yellow-200 bg-yellow-50">
              <AlertTriangle className="h-4 w-4 text-yellow-600" />
              <AlertDescription className="text-yellow-800">
                Your subscription is scheduled to be cancelled on{" "}
                {formatDate(subscription.current_period_end)}. You can
                reactivate it anytime before then.
              </AlertDescription>
            </Alert>
          )}

          {/* Action Buttons */}
          <div className="flex gap-3 pt-4">
            {isSubscriptionActive &&
              !isFreePlan &&
              !isSubscriptionCancelled && (
                <Button
                  variant="outline"
                  onClick={handleCancelSubscription}
                  disabled={cancelingSubscription}
                  className="text-red-600 border-red-200 hover:bg-red-50"
                >
                  <AlertTriangle className="w-4 h-4 mr-2" />
                  Cancel Subscription
                </Button>
              )}

            {isSubscriptionCancelled && (
              <Button
                onClick={handleReactivateSubscription}
                disabled={reactivatingSubscription}
                className="bg-green-600 hover:bg-green-700"
              >
                {reactivatingSubscription ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <CheckCircle className="w-4 h-4 mr-2" />
                )}
                Reactivate Subscription
              </Button>
            )}
          </div>

          {isFreePlan ? (
            <div className="flex items-center gap-2 border-t pt-4 text-xs text-muted-foreground">
              <Info className="h-4 w-4" />
              <span>No payment method required for the Free plan.</span>
            </div>
          ) : null}
        </CardContent>
      </Card>

      <CancelSubscriptionDialog
        open={cancelDialogOpen}
        onOpenChange={setCancelDialogOpen}
        onCancel={handleCancelConfirm}
        accessUntil={subscription.current_period_end}
      />
    </div>
  );
}
