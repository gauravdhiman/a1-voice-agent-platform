"use client";

import React, { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  TabsContent,
  TabsList,
  TabsTrigger,
  AnimatedTabs,
} from "@/components/ui/tabs";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  CreditCard,
  Zap,
  Calendar,
  RefreshCw,
  Loader2,
  AlertTriangle,
} from "lucide-react";
import { useAuth } from "@/contexts/auth-context";
import { useOrganization } from "@/contexts/organization-context";
import { useBillingSummary } from "@/hooks/use-billing-summary";
import { useUserPermissions } from "@/hooks/use-user-permissions";
import { PlanSelection } from "@/components/billing/plan-selection";
import { friendlyPlanName } from "@/components/billing/plan-card";
import { CreditPurchase } from "@/components/billing/credit-purchase";
import { CreditUsagePanel } from "@/components/billing/credit-usage-panel";
import { SubscriptionManagement } from "@/components/billing/subscription-management";
import { toast } from "sonner";
import { useSearchParams, useRouter } from "next/navigation";
import { useOrganizationById } from "@/hooks/use-organization-by-id";
import { useCreditUsage } from "@/hooks/use-credit-usage";
import { AccessDenied } from "@/components/ui/access-denied";
import { billingService } from "@/services/billing-service";

export default function BillingPage() {
  const { loading: authLoading } = useAuth();
  const {
    currentOrganization,
    loading: orgLoading,
    setCurrentOrganization,
  } = useOrganization();
  const searchParams = useSearchParams();
  const router = useRouter();
  // Fall back to currentOrganization.id when ?org_id= is missing.
  // The sidebar nav links to bare /organization/billing (no ?org_id=),
  // and the org admin should see the page, not "Access Denied".
  const orgId = searchParams.get("org_id") ?? currentOrganization?.id ?? null;

  // Validate organization access when orgId is provided
  const {
    isValid: isOrgValid,
    loading: validationLoading,
    organization: validatedOrg,
  } = useOrganizationById(orgId);

  // Set the current organization based on the validated orgId parameter if provided.
  // Must run in an effect — calling setState during render is an
  // anti-pattern (causes re-render loops, "Cannot update a component
  // while rendering a different component" errors in React 18+).
  useEffect(() => {
    if (
      validatedOrg &&
      (!currentOrganization || currentOrganization.id !== validatedOrg.id)
    ) {
      setCurrentOrganization(validatedOrg);
    }
  }, [validatedOrg, currentOrganization, setCurrentOrganization]);

  // Page-level gate: `billing:manage` OR `billing:subscribe` (and
  // platform admin wildcard) via the useUserPermissions facade —
  // not a bare isOrgAdmin role check, so Phase 2 custom billing
  // managers are not blocked.
  const userPermissions = useUserPermissions();
  const isBillingAdmin = userPermissions.canManageBilling;

  const {
    data: billingSummary,
    isLoading: loading,
    error: queryError,
    refetch,
    isRefetching,
  } = useBillingSummary(orgId || undefined);
  const {
    data: creditUsage,
    isLoading: creditUsageLoading,
    error: creditUsageError,
    refetch: refetchCreditUsage,
  } = useCreditUsage(orgId || undefined);

  const [userSelectedTab, setUserSelectedTab] = useState<string | null>(null);
  const [checkoutConfirmation, setCheckoutConfirmation] = useState<
    "idle" | "pending" | "confirmed" | "delayed"
  >("idle");
  const [activationRetry, setActivationRetry] = useState(0);
  const paymentStatus = searchParams.get("payment");
  const checkoutPlanVersionId = searchParams.get("plan_version_id");

  useEffect(() => {
    if (paymentStatus !== "success" || !orgId || !checkoutPlanVersionId) {
      setCheckoutConfirmation("idle");
      return;
    }

    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let attempts = 0;
    setCheckoutConfirmation("pending");

    const confirmPlanActivation = async () => {
      attempts += 1;
      try {
        const activation = await billingService.getSubscriptionActivationStatus(orgId);
        if (
          !cancelled &&
          activation.plan_version_id === checkoutPlanVersionId &&
          (activation.state === "active" || activation.state === "trial")
        ) {
          setCheckoutConfirmation("confirmed");
          await Promise.all([refetch(), refetchCreditUsage()]);
          return;
        }
      } catch {
        // Stripe's webhook may still be persisting the subscription. Keep
        // checking for a bounded period and let the user refresh afterward.
      }

      if (cancelled) return;
      if (attempts >= 20) {
        setCheckoutConfirmation("delayed");
        return;
      }
      timer = setTimeout(() => void confirmPlanActivation(), 1500);
    };

    void confirmPlanActivation();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [
    paymentStatus,
    orgId,
    checkoutPlanVersionId,
    activationRetry,
    refetch,
    refetchCreditUsage,
  ]);

  const error = queryError
    ? queryError instanceof Error
      ? queryError.message
      : "Unknown error"
    : null;

  const hasActiveSubscription =
    billingSummary?.subscription &&
    ["active", "trial"].includes(billingSummary.subscription.status);

  const isFreePlan =
    billingSummary?.subscription?.metadata?.billing_mode === "free";
  const currentPlan = billingSummary?.subscription?.plan;
  const currentPlanVersion = billingSummary?.subscription?.plan_version;
  const currentPlanName = currentPlanVersion
    ? friendlyPlanName({
        product_slug: currentPlanVersion.product_slug,
        product_name: currentPlanVersion.product_name,
        display_label: currentPlanVersion.display_label,
      })
    : currentPlan
      ? friendlyPlanName({ product_name: currentPlan.name, display_label: null })
    : isFreePlan
      ? "Free"
      : "No Plan";

  const activeTab =
    userSelectedTab ?? (hasActiveSubscription ? "overview" : "plans");
  const focusCreditPurchase =
    activeTab === "credits" && searchParams.get("section") === "purchase";

  // Sync tab state with URL
  useEffect(() => {
    const tabParam = searchParams.get("tab");
    if (
      tabParam &&
      ["overview", "manage", "plans", "credits"].includes(tabParam)
    ) {
      setUserSelectedTab(tabParam === "manage" ? "overview" : tabParam);
    }
  }, [searchParams]);

  const handleTabChange = (value: string) => {
    setUserSelectedTab(value);
    router.push(`/organization/billing?org_id=${orgId}&tab=${value}`, {
      scroll: false,
    });
  };

  const handleBuyCredits = () => {
    setUserSelectedTab("credits");
    router.push(
      `/organization/billing?org_id=${orgId}&tab=credits&section=purchase`,
      { scroll: false },
    );
  };

  // Make orgId mandatory - if not provided, redirect to organizations page
  if (!orgId) {
    return (
      <AccessDenied
        title="Organization ID Required"
        description="Organization ID is required to access this page. Please select an organization from the organizations page."
        redirectPath="/organizations"
      />
    );
  }

  // Page-level admin gate.
  if (!isBillingAdmin) {
    return (
      <AccessDenied
        title="Access Denied"
        description="Only organization admins and platform admins can manage billing."
        redirectPath="/dashboard"
      />
    );
  }

  const refresh = async () => {
    await Promise.all([refetch(), refetchCreditUsage()]);
    toast.success("Billing data refreshed");
  };

  const formatCurrency = (amount: number, currency = "USD") => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: currency,
    }).format(amount / 100);
  };

  const formatDate = (date: string | Date) => {
    return new Date(date).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  if (
    authLoading ||
    orgLoading ||
    validationLoading ||
    loading ||
    creditUsageLoading
  ) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin mr-2 text-muted-foreground" />
        <span className="text-muted-foreground">
          Loading billing information...
        </span>
      </div>
    );
  }

  // Check if orgId is invalid (provided but validation failed)
  if (!isOrgValid) {
    return (
      <AccessDenied
        title="Access Denied"
        description="You do not have permission to access this organization. Please contact your organization administrator or platform admin for access."
        redirectPath="/organizations"
      />
    );
  }

  if (error) {
    return (
      <div className="py-8">
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <h1 className="text-xl font-bold text-foreground sm:text-2xl">
              Billing & Subscriptions
            </h1>
            <p className="text-sm text-muted-foreground">
              Manage your subscription, credits, and billing information
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="w-full sm:w-auto"
            onClick={refresh}
            disabled={isRefetching}
          >
            {isRefetching ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <RefreshCw className="w-4 h-4 mr-2" />
            )}
            Refresh
          </Button>
        </div>

        {/* Organization Info */}
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <span>Organization:</span>
          <span className="font-medium text-foreground">
            {validatedOrg?.name}
          </span>
        </div>
      </div>

      {paymentStatus === "cancelled" ? (
        <Alert>
          <AlertDescription>
            Checkout was cancelled. Your current plan and billing have not changed.
          </AlertDescription>
        </Alert>
      ) : null}

      {checkoutConfirmation === "pending" ? (
        <Alert>
          <Loader2 className="h-4 w-4 animate-spin" />
          <AlertDescription>
            Payment completed. We&apos;re confirming the selected plan with the
            billing system. This page will refresh when activation is confirmed;
            don&apos;t submit the payment again.
          </AlertDescription>
        </Alert>
      ) : checkoutConfirmation === "confirmed" ? (
        <Alert className="border-green-200 bg-green-50 text-green-900">
          <AlertDescription>
            Your selected plan is active and the billing information has been refreshed.
          </AlertDescription>
        </Alert>
      ) : checkoutConfirmation === "delayed" ? (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            Payment completed, but plan activation is still pending. Your account
            will continue to show the current plan until confirmation arrives.
            Don&apos;t pay again.{" "}
            <button
              className="font-medium underline"
              onClick={() => {
                setCheckoutConfirmation("pending");
                setActivationRetry((retry) => retry + 1);
                void Promise.all([refetch(), refetchCreditUsage()]);
              }}
              type="button"
            >
              Check activation again
            </button>
          </AlertDescription>
        </Alert>
      ) : null}

      {/* Overview Cards */}
      {billingSummary && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Current Plan */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 p-4 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Current Plan
              </CardTitle>
              <CreditCard className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent className="p-4 pt-0">
              <div className="text-2xl font-bold">{currentPlanName}</div>
              <p className="text-xs text-muted-foreground mt-1">
                {billingSummary.subscription?.status && (
                  <Badge variant="outline" className="capitalize font-normal">
                    {billingSummary.subscription.status}
                  </Badge>
                )}
              </p>
            </CardContent>
          </Card>

          {/* Credit Balance */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 p-4 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Credit Balance
              </CardTitle>
              <Zap className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent className="p-4 pt-0">
              <div className="text-2xl font-bold">
                {billingSummary.credit_balance?.toLocaleString() || "0"}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                Available credits
              </p>
            </CardContent>
          </Card>

          {/* Next Billing */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 p-4 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Next Billing
              </CardTitle>
              <Calendar className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent className="p-4 pt-0">
              <div className="text-2xl font-bold">
                {billingSummary.next_billing_date
                  ? formatDate(billingSummary.next_billing_date)
                  : "N/A"}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                {billingSummary.amount_due
                  ? formatCurrency(billingSummary.amount_due)
                  : "No amount due"}
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Main Content Tabs */}
      <AnimatedTabs
        value={activeTab}
        onValueChange={handleTabChange}
        className="space-y-6"
      >
        <TabsList className="w-full justify-start overflow-x-auto">
          <TabsTrigger className="shrink-0 px-3 sm:px-6" value="overview">Overview</TabsTrigger>
          <TabsTrigger className="shrink-0 px-3 sm:px-6" value="plans">Plans</TabsTrigger>
          <TabsTrigger className="shrink-0 px-3 sm:px-6" value="credits">Credits</TabsTrigger>
        </TabsList>

        {/* Plans Tab */}
        <TabsContent value="plans" className="space-y-6">
          {validatedOrg && (
            <PlanSelection
              organizationId={validatedOrg.id}
              currentSubscription={billingSummary?.subscription}
              onPlanSelected={() => refetch()}
            />
          )}
        </TabsContent>

        {/* Credits Tab */}
        <TabsContent value="credits" className="space-y-6">
          {validatedOrg && (
            <>
              {creditUsage ? (
                <CreditUsagePanel usage={creditUsage} variant="summary" />
              ) : null}

              <CreditPurchase
                organizationId={validatedOrg.id}
                autoFocusPurchase={focusCreditPurchase}
                onCreditsPurchased={() => {
                  void Promise.all([refetch(), refetchCreditUsage()]);
                }}
              />

              {creditUsageError ? (
                <Alert variant="destructive">
                  <AlertTriangle className="h-4 w-4" />
                  <AlertDescription>
                    Unable to load credit usage reporting. Please refresh and
                    try again.
                  </AlertDescription>
                </Alert>
              ) : creditUsage ? (
                <CreditUsagePanel usage={creditUsage} variant="details" />
              ) : null}
            </>
          )}
        </TabsContent>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-6">
          {billingSummary?.subscription && validatedOrg ? (
            <SubscriptionManagement
              organizationId={validatedOrg.id}
              subscription={billingSummary.subscription}
              onSubscriptionUpdated={() => refetch()}
              onChangePlan={() => handleTabChange("plans")}
              onBuyCredits={handleBuyCredits}
            />
          ) : (
            <Card>
              <CardContent className="p-6 text-sm text-muted-foreground">
                Choose a plan to start billing for this organization.
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </AnimatedTabs>
    </div>
  );
}
