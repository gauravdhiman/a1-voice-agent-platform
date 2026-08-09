"use client";

import { useAuth } from "@/contexts/auth-context";
import { AccessDenied } from "@/components/ui/access-denied";
import { PlatformPlansManager } from "@/components/billing/platform-plans-manager";

/**
 * Platform admin page for plan products, version drafts, entitlements, and publish.
 */
export default function PlatformPlansPage() {
  const { user } = useAuth();

  if (!user?.hasRole("platform_admin")) {
    return (
      <AccessDenied
        title="Access Denied"
        description="Only platform administrators can manage plan products and versions."
        redirectPath="/dashboard"
      />
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">
          Plan Catalog
        </h1>
        <p className="text-muted-foreground mt-1">
          Create plan products, edit draft versions with entitlements, and publish
          with grandfathering and migration policy.
        </p>
      </div>
      <PlatformPlansManager />
    </div>
  );
}
