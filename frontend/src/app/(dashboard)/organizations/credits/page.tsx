"use client";

import Link from "next/link";
import { ArrowLeft, Building2, Loader2, ShieldCheck } from "lucide-react";

import { useAuth } from "@/contexts/auth-context";
import { useSearchParams } from "next/navigation";
import { useCreditUsage } from "@/hooks/use-credit-usage";
import { useOrganizationById } from "@/hooks/use-organization-by-id";
import { AccessDenied } from "@/components/ui/access-denied";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { AdminCreditGrant } from "@/components/billing/admin-credit-grant";
import { CreditUsagePanel } from "@/components/billing/credit-usage-panel";

/**
 * Platform-admin workspace for organization-specific credit operations.
 *
 * The page keeps platform mutations separate from organization Billing while
 * retaining the same usage reporting context. It is intentionally scoped by
 * `org_id`, which lets future entitlement overrides live beside credit grants
 * without adding platform controls to the organization-admin workflow.
 */
export default function PlatformOrganizationCreditsPage() {
  const { user } = useAuth();
  const searchParams = useSearchParams();
  const organizationId = searchParams.get("org_id");
  const {
    isValid,
    loading: organizationLoading,
    organization,
  } = useOrganizationById(organizationId);
  const {
    data: creditUsage,
    isLoading: creditUsageLoading,
    error: creditUsageError,
    refetch: refetchCreditUsage,
  } = useCreditUsage(organizationId ?? undefined);

  if (!user?.hasRole("platform_admin")) {
    return (
      <AccessDenied
        title="Access Denied"
        description="Only platform administrators can manage organization credits."
        redirectPath="/dashboard"
      />
    );
  }

  if (!organizationId) {
    return (
      <AccessDenied
        title="Organization ID Required"
        description="Select an organization from the platform organization directory before opening credit controls."
        redirectPath="/organizations"
      />
    );
  }

  if (organizationLoading || creditUsageLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="mr-2 h-8 w-8 animate-spin text-muted-foreground" />
        <span className="text-muted-foreground">
          Loading organization credit controls...
        </span>
      </div>
    );
  }

  if (!isValid || !organization) {
    return (
      <AccessDenied
        title="Organization Not Available"
        description="This organization could not be loaded. Return to the platform organization directory and choose another organization."
        redirectPath="/organizations"
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <Button asChild variant="ghost" className="mb-3 -ml-3">
            <Link href="/organizations">
              <ArrowLeft className="h-4 w-4" />
              Organizations
            </Link>
          </Button>
          <p className="text-sm font-medium text-primary">Platform Admin</p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
            Credits &amp; entitlements
          </h1>
          <p className="mt-2 max-w-2xl text-muted-foreground">
            Review credit consumption and apply platform-level adjustments for
            one organization. Subscription and purchased-credit settings remain
            in the organization&apos;s Billing area.
          </p>
        </div>
        <div className="flex min-w-0 items-center gap-2 rounded-lg border border-border/70 bg-muted/20 px-3 py-2 text-sm">
          <Building2 className="h-4 w-4 text-muted-foreground" />
          <span className="truncate font-medium">{organization.name}</span>
        </div>
      </div>

      <Alert>
        <ShieldCheck className="h-4 w-4" />
        <AlertDescription>
          Platform allocations are auditable, non-expiring bonus credits. They
          do not change the organization&apos;s subscribed plan or purchased
          pool.
        </AlertDescription>
      </Alert>

      {creditUsageError ? (
        <Alert variant="destructive">
          <AlertDescription>
            Unable to load credit usage reporting. You can still review the
            organization identity and try again later.
          </AlertDescription>
        </Alert>
      ) : creditUsage ? (
        <CreditUsagePanel usage={creditUsage} />
      ) : null}

      <AdminCreditGrant
        organizationId={organization.id}
        onGranted={() => {
          void refetchCreditUsage();
        }}
      />
    </div>
  );
}
