"use client";

import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { CatalogHelpTooltip } from "@/components/billing/catalog-help-tooltip";
import {
  filterProductsByCadence,
  productHasDraft,
  type BillingCadence,
} from "@/lib/billing/plan-catalog-utils";
import { PLAN_CATALOG_FIELD_HELP } from "@/lib/billing/entitlement-catalog-help";
import type {
  PlanProductWithVersions,
  PlanVersionDetail,
  PlanVersionStatus,
  PlanVersionSummary,
} from "@/types/admin-plans";
import { Plus } from "lucide-react";

function formatPrice(cents: number, currency: string): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: currency || "USD",
  }).format(cents / 100);
}

function statusBadgeVariant(
  status: PlanVersionStatus,
): "default" | "secondary" | "outline" | "destructive" {
  switch (status) {
    case "published":
      return "default";
    case "draft":
      return "secondary";
    case "deprecated":
      return "outline";
    default:
      return "destructive";
  }
}

interface PlanProductsListPanelProps {
  products: PlanProductWithVersions[];
  cadenceTab: BillingCadence;
  onCadenceTabChange: (cadence: BillingCadence) => void;
  selectedVersionId: string | null;
  onSelectVersion: (version: PlanVersionSummary) => void;
  onCreateDraft: (product: PlanProductWithVersions) => void;
  productBillingBySlug: Record<string, BillingCadence>;
}

/**
 * Left panel: monthly/annual tabs with plan products and version list.
 */
export function PlanProductsListPanel({
  products,
  cadenceTab,
  onCadenceTabChange,
  selectedVersionId,
  onSelectVersion,
  onCreateDraft,
  productBillingBySlug,
}: PlanProductsListPanelProps) {
  const monthlyProducts = filterProductsByCadence(
    products,
    "monthly",
    productBillingBySlug,
  );
  const annualProducts = filterProductsByCadence(
    products,
    "annual",
    productBillingBySlug,
  );

  const renderProductList = (
    items: PlanProductWithVersions[],
    cadence: BillingCadence,
  ) => {
    if (items.length === 0) {
      return (
        <p className="text-sm text-muted-foreground py-6 text-center">
          No {cadence} plans yet. Create a product with this billing cadence.
        </p>
      );
    }

    return (
      <div className="space-y-4">
        {items.map((product) => {
          const hasDraft = productHasDraft(product);
          return (
            <div key={product.id} className="space-y-2 rounded-lg border p-3">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                <div className="min-w-0">
                  <p className="break-words font-medium sm:truncate">
                    {product.display_name}
                  </p>
                  <p className="break-all text-xs text-muted-foreground sm:truncate">
                    {product.slug}
                  </p>
                </div>
                <Button
                  size="sm"
                  className="w-full shrink-0 sm:w-auto"
                  variant="outline"
                  disabled={hasDraft}
                  title={
                    hasDraft ? PLAN_CATALOG_FIELD_HELP.draftSingle : undefined
                  }
                  onClick={() => onCreateDraft(product)}
                >
                  <Plus className="mr-1 h-3 w-3" />
                  Draft
                </Button>
              </div>
              <div className="space-y-1">
                {product.versions.length === 0 ? (
                  <p className="text-xs text-muted-foreground">
                    No versions yet.
                  </p>
                ) : (
                  product.versions.map((version) => (
                    <button
                      key={version.id}
                      type="button"
                      onClick={() => onSelectVersion(version)}
                      className={`flex w-full flex-col items-start gap-2 rounded-md border px-2.5 py-2 text-left text-sm transition hover:bg-muted/50 sm:flex-row sm:items-center sm:justify-between ${
                        selectedVersionId === version.id
                          ? "border-primary bg-muted/30"
                          : ""
                      }`}
                    >
                      <span className="min-w-0 max-w-full break-words pr-2">
                        v{version.version_number}
                        {version.display_label
                          ? ` — ${version.display_label}`
                          : ""}
                        {version.is_current_for_signup ? " · current" : ""}
                      </span>
                      <span className="flex w-full shrink-0 items-center justify-between gap-1.5 sm:w-auto sm:justify-end">
                        <Badge variant={statusBadgeVariant(version.status)}>
                          {version.status}
                        </Badge>
                        <span className="whitespace-nowrap text-xs text-muted-foreground">
                          {formatPrice(
                            version.price_amount_cents,
                            version.currency,
                          )}
                        </span>
                      </span>
                    </button>
                  ))
                )}
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <Card className="h-full">
      <CardHeader className="pb-2">
        <CardTitle className="flex flex-wrap items-center gap-2 text-lg">
          Plan catalog
          <CatalogHelpTooltip content="Each product is a billing family. Versions hold immutable price and entitlement snapshots." />
        </CardTitle>
      </CardHeader>
      <CardContent className="min-w-0 p-4 sm:p-6">
        <Tabs
          value={cadenceTab}
          onValueChange={(v) => onCadenceTabChange(v as BillingCadence)}
        >
          <TabsList className="mb-4 w-full justify-start overflow-x-auto">
            <TabsTrigger
              className="shrink-0 whitespace-nowrap px-3 sm:px-4"
              value="monthly"
            >
              Monthly
              <Badge variant="secondary" className="ml-2">
                {monthlyProducts.length}
              </Badge>
            </TabsTrigger>
            <TabsTrigger
              className="shrink-0 whitespace-nowrap px-3 sm:px-4"
              value="annual"
            >
              Annual
              <Badge variant="secondary" className="ml-2">
                {annualProducts.length}
              </Badge>
            </TabsTrigger>
          </TabsList>
          <TabsContent
            value="monthly"
            className="mt-0 min-h-0 max-h-[calc(100dvh-280px)] overflow-y-auto"
          >
            {renderProductList(monthlyProducts, "monthly")}
          </TabsContent>
          <TabsContent
            value="annual"
            className="mt-0 min-h-0 max-h-[calc(100dvh-280px)] overflow-y-auto"
          >
            {renderProductList(annualProducts, "annual")}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}

export type { PlanVersionSummary, PlanVersionDetail };
