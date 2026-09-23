"use client";

import { useAuth } from "@/contexts/auth-context";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { AccessDenied } from "@/components/ui/access-denied";
import { PlatformPlansManager } from "@/components/billing/platform-plans-manager";
import { PlatformEntitlementsManager } from "@/components/billing/platform-entitlements-manager";
import { PlatformUsagePricingManager } from "@/components/billing/platform-usage-pricing-manager";
import { buildTabHref, resolveTab } from "@/lib/navigation/tab-state";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";

const PLAN_CATALOG_TABS = ["plans", "entitlements", "usage"] as const;
type PlanCatalogTab = (typeof PLAN_CATALOG_TABS)[number];

/**
 * Platform admin catalog for plan products, entitlements, and usage pricing.
 */
export default function PlatformPlansPage() {
  const { user } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const activeTab = resolveTab<PlanCatalogTab>(
    searchParams.get("tab"),
    PLAN_CATALOG_TABS,
    "plans",
  );

  const handleTabChange = (value: string) => {
    if (!PLAN_CATALOG_TABS.includes(value as PlanCatalogTab)) return;
    router.replace(
      buildTabHref(pathname, searchParams.toString(), value, "plans"),
      { scroll: false },
    );
  };

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
        <h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
          Plan Catalog
        </h1>
        <p className="text-muted-foreground mt-1">
          Manage plan terms, platform entitlements, and activity pricing from one
          place. Changes to usage rates apply to newly metered activity.
        </p>
      </div>
      <Tabs
        value={activeTab}
        onValueChange={handleTabChange}
        className="space-y-5"
      >
        <TabsList className="max-w-full overflow-x-auto">
          <TabsTrigger className="shrink-0 px-3 sm:px-6" value="plans">Plans</TabsTrigger>
          <TabsTrigger className="shrink-0 px-3 sm:px-6" value="entitlements">Entitlements</TabsTrigger>
          <TabsTrigger className="shrink-0 px-3 sm:px-6" value="usage">Usage pricing</TabsTrigger>
        </TabsList>
        <TabsContent value="plans" className="mt-0">
          <PlatformPlansManager />
        </TabsContent>
        <TabsContent value="entitlements" className="mt-0">
          <PlatformEntitlementsManager />
        </TabsContent>
        <TabsContent value="usage" className="mt-0">
          <PlatformUsagePricingManager />
        </TabsContent>
      </Tabs>
    </div>
  );
}
