'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { TabsContent, TabsList, TabsTrigger, AnimatedTabs } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  CreditCard,
  Zap,
  Calendar,
  RefreshCw,
  Loader2,
  AlertTriangle
} from 'lucide-react';
import { useAuth } from '@/contexts/auth-context';
import { useOrganization } from '@/contexts/organization-context';
import { useBillingSummary } from '@/hooks/use-billing-summary';
import { PlanSelection } from '@/components/billing/plan-selection';
import { CreditPurchase } from '@/components/billing/credit-purchase';
import { SubscriptionManagement } from '@/components/billing/subscription-management';
import { toast } from 'sonner';
import { useSearchParams, useRouter } from 'next/navigation';
import { useOrganizationById } from '@/hooks/use-organization-by-id';
import { AccessDenied } from '@/components/ui/access-denied';

export default function BillingPage() {
  const { loading: authLoading } = useAuth();
  const { currentOrganization, loading: orgLoading, setCurrentOrganization } = useOrganization();
  const searchParams = useSearchParams();
  const router = useRouter();
  const orgId = searchParams.get('org_id');

  // Validate organization access when orgId is provided
  const { isValid: isOrgValid, loading: validationLoading, organization: validatedOrg } = useOrganizationById(orgId);

  // Set the current organization based on the validated orgId parameter if provided
  if (validatedOrg && (!currentOrganization || currentOrganization.id !== validatedOrg.id)) {
    setCurrentOrganization(validatedOrg);
  }

  const {
    data: billingSummary,
    isLoading: loading,
    error: queryError,
    refetch,
    isRefetching
  } = useBillingSummary(orgId || undefined);

  const [userSelectedTab, setUserSelectedTab] = useState<string | null>(null);

  const error = queryError ? (queryError instanceof Error ? queryError.message : 'Unknown error') : null;

  const hasActiveSubscription = billingSummary?.subscription &&
    ['active', 'trial'].includes(billingSummary.subscription.status);

  const activeTab = userSelectedTab ?? (hasActiveSubscription ? 'overview' : 'plans');

  // Sync tab state with URL
  useEffect(() => {
    const tabParam = searchParams.get('tab');
    if (tabParam && ['overview', 'plans', 'credits', 'manage'].includes(tabParam)) {
      setUserSelectedTab(tabParam);
    }
  }, [searchParams]);

  const handleTabChange = (value: string) => {
    setUserSelectedTab(value);
    router.push(`/organization/billing?org_id=${orgId}&tab=${value}`, { scroll: false });
  };

  // Make orgId mandatory - if not provided, redirect to organizations page
  if (!orgId) {
    return <AccessDenied
      title="Organization ID Required"
      description="Organization ID is required to access this page. Please select an organization from the organizations page."
      redirectPath="/organizations"
    />;
  }

  const refresh = async () => {
    await refetch();
    toast.success('Billing data refreshed');
  };

  const formatCurrency = (amount: number, currency = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency
    }).format(amount / 100);
  };

  const formatDate = (date: string | Date) => {
    return new Date(date).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  if (authLoading || orgLoading || validationLoading || loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin mr-2 text-muted-foreground" />
        <span className="text-muted-foreground">Loading billing information...</span>
      </div>
    );
  }

  // Check if orgId is invalid (provided but validation failed)
  if (!isOrgValid) {
    return <AccessDenied
      title="Access Denied"
      description="You do not have permission to access this organization. Please contact your organization administrator or platform admin for access."
      redirectPath="/organizations"
    />;
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
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Billing & Subscriptions</h1>
            <p className="text-sm text-muted-foreground">
              Manage your subscription, credits, and billing information
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
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
          <span className="font-medium text-foreground">{validatedOrg?.name}</span>
        </div>
      </div>

      {/* Overview Cards */}
      {billingSummary && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Current Plan */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 p-4 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Current Plan</CardTitle>
              <CreditCard className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent className="p-4 pt-0">
              <div className="text-2xl font-bold">
                {billingSummary.subscription?.plan?.name || 'No Plan'}
              </div>
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
              <CardTitle className="text-sm font-medium text-muted-foreground">Credit Balance</CardTitle>
              <Zap className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent className="p-4 pt-0">
              <div className="text-2xl font-bold">
                {billingSummary.credit_balance?.toLocaleString() || '0'}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                Available credits
              </p>
            </CardContent>
          </Card>

          {/* Next Billing */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 p-4 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Next Billing</CardTitle>
              <Calendar className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent className="p-4 pt-0">
              <div className="text-2xl font-bold">
                {billingSummary.next_billing_date
                  ? formatDate(billingSummary.next_billing_date)
                  : 'N/A'
                }
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                {billingSummary.amount_due
                  ? formatCurrency(billingSummary.amount_due)
                  : 'No amount due'
                }
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Main Content Tabs */}
      <AnimatedTabs value={activeTab} onValueChange={handleTabChange} className="space-y-6">
        <TabsList className="w-full">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="plans">Plans</TabsTrigger>
          <TabsTrigger value="credits">Credits</TabsTrigger>
          {hasActiveSubscription && (
            <TabsTrigger value="manage">Manage</TabsTrigger>
          )}
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-6">
          {hasActiveSubscription ? (
            <div className="space-y-6">
              <Card>
                <CardHeader className="p-5 pb-3">
                  <CardTitle className="text-lg">Subscription Overview</CardTitle>
                  <CardDescription>
                    Current subscription details and usage information
                  </CardDescription>
                </CardHeader>
                <CardContent className="p-5 pt-0">
                  {billingSummary?.subscription && (
                    <div className="space-y-4">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                          <h4 className="font-semibold text-sm mb-2">Plan Details</h4>
                          <div className="space-y-1 text-sm">
                            <p><span className="text-muted-foreground">Plan:</span> {billingSummary.subscription.plan?.name}</p>
                            <p><span className="text-muted-foreground">Status:</span> {billingSummary.subscription.status}</p>
                          </div>
                        </div>
                        <div>
                          <h4 className="font-semibold text-sm mb-2">Usage This Period</h4>
                          <div className="space-y-1 text-sm">
                            <p><span className="text-muted-foreground">Credits Used:</span> {billingSummary.current_period_usage?.toLocaleString() || '0'}</p>
                            <p><span className="text-muted-foreground">Credits Remaining:</span> {billingSummary.credit_balance?.toLocaleString() || '0'}</p>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          ) : (
            <Card>
              <CardHeader className="p-5 pb-3">
                <CardTitle className="text-lg">Welcome to Billing</CardTitle>
                <CardDescription>
                  Choose a plan to get started with your subscription
                </CardDescription>
              </CardHeader>
              <CardContent className="p-5 pt-0">
                <p className="text-muted-foreground mb-4 text-sm">
                  You don&apos;t have an active subscription yet. Browse our plans to get started.
                </p>
                <Button onClick={() => handleTabChange('plans')} size="sm">
                  View Plans
                </Button>
              </CardContent>
            </Card>
          )}
        </TabsContent>

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
            <CreditPurchase
              organizationId={validatedOrg.id}
              onCreditsPurchased={() => refetch()}
            />
          )}
        </TabsContent>

        {/* Manage Tab */}
        {hasActiveSubscription && (
          <TabsContent value="manage" className="space-y-6">
            {billingSummary?.subscription && validatedOrg && (
              <SubscriptionManagement
                organizationId={validatedOrg.id}
                subscription={billingSummary.subscription}
                onSubscriptionUpdated={() => refetch()}
              />
            )}
          </TabsContent>
        )}
      </AnimatedTabs>
    </div>
  );
}
