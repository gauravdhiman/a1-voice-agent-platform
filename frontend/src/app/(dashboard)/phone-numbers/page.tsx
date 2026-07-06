"use client";

/**
 * Top-level /phone-numbers page (N1 redesign).
 *
 * Phone Numbers used to live as a tab inside the organization page.
 * They're now a first-class route, which makes the link shareable and
 * gives the entry its own permissions gate (`phone_number:read` in the
 * nav config).
 *
 * The page is a thin shell over the existing `<PhoneNumberDashboard>`.
 * The dashboard is a controlled component — it does not fetch its own
 * data — so this page owns the data fetch using the same services the
 * org page tab used. That keeps the rendering and the data lifecycle
 * identical to the legacy tab.
 */

import React, { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useOrganization } from "@/contexts/organization-context";
import { useUserPermissions } from "@/hooks/use-user-permissions";
import { phoneNumberService } from "@/services/phone-number-service";
import { billingService } from "@/services/billing-service";
import { PhoneNumberWithAgent } from "@/types/phone-number";
import { PhoneNumberDashboard } from "@/components/phone-numbers/phone-number-dashboard";
import { toast } from "sonner";

export default function PhoneNumbersPage() {
  const searchParams = useSearchParams();
  const { currentOrganization } = useOrganization();
  const { isPlatformAdmin, isOrgAdmin } = useUserPermissions();

  // Prefer the URL's org_id (shareable links), fall back to the current
  // org from context (default app navigation).
  const orgId = searchParams.get("org_id") ?? currentOrganization?.id ?? null;

  const [phoneNumbers, setPhoneNumbers] = useState<PhoneNumberWithAgent[]>([]);
  const [creditBalance, setCreditBalance] = useState(0);
  const [isLoading, setIsLoading] = useState(false);

  const loadPhoneNumbers = useCallback(async () => {
    if (!orgId) return;
    setIsLoading(true);
    try {
      const [numbersRes, balanceRes] = await Promise.all([
        phoneNumberService.getOrganizationNumbers(orgId),
        billingService.getCreditBalance(orgId),
      ]);
      setPhoneNumbers(numbersRes.items);
      setCreditBalance(balanceRes.total_credits);
    } catch (error) {
      console.error("Failed to load phone numbers:", error);
      toast.error("Failed to load phone numbers");
    } finally {
      setIsLoading(false);
    }
  }, [orgId]);

  useEffect(() => {
    if (orgId) {
      loadPhoneNumbers();
    }
  }, [orgId, loadPhoneNumbers]);

  if (!orgId) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center">
        <p className="text-muted-foreground">
          Select an organization to view its phone numbers.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Phone Numbers</h1>
        <p className="text-sm text-muted-foreground">
          Manage your phone numbers, assign them to voice agents, and track
          your credit balance.
        </p>
      </div>
      <PhoneNumberDashboard
        organizationId={orgId}
        phoneNumbers={phoneNumbers}
        creditBalance={creditBalance}
        isLoading={isLoading}
        onRefresh={loadPhoneNumbers}
      />
      {!isPlatformAdmin && !isOrgAdmin ? (
        <p className="text-xs text-muted-foreground">
          You have read-only access. Contact an org admin to add or change
          phone numbers.
        </p>
      ) : null}
    </div>
  );
}
