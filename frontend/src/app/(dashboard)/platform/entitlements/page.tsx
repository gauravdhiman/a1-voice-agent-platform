"use client";

import { useAuth } from "@/contexts/auth-context";
import { AccessDenied } from "@/components/ui/access-denied";
import { PlatformEntitlementsManager } from "@/components/billing/platform-entitlements-manager";

/**
 * Platform admin page for entitlement definition catalog metadata.
 */
export default function PlatformEntitlementsPage() {
  const { user } = useAuth();

  if (!user?.hasRole("platform_admin")) {
    return (
      <AccessDenied
        title="Access Denied"
        description="Only platform administrators can manage the entitlement catalog."
        redirectPath="/dashboard"
      />
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">
          Entitlement Catalog
        </h1>
        <p className="text-muted-foreground mt-1">
          Edit display names and descriptions for platform entitlement keys. Limit
          values are assigned per plan version on the Plan Catalog page.
        </p>
      </div>
      <PlatformEntitlementsManager />
    </div>
  );
}
