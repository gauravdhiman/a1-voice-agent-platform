"use client";

import * as React from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { CatalogFieldLabel } from "@/components/billing/catalog-help-tooltip";
import { PLAN_CATALOG_FIELD_HELP } from "@/lib/billing/entitlement-catalog-help";
import type { BillingCadence } from "@/lib/billing/plan-catalog-utils";
import { Loader2 } from "lucide-react";

export interface PlanProductCreatePayload {
  slug: string;
  display_name: string;
  billing_interval: BillingCadence;
}

interface PlanProductCreateSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreate: (payload: PlanProductCreatePayload) => Promise<void>;
}

/**
 * Side sheet for creating a new plan product (matches other platform admin patterns).
 */
export function PlanProductCreateSheet({
  open,
  onOpenChange,
  onCreate,
}: PlanProductCreateSheetProps) {
  const [slug, setSlug] = React.useState("");
  const [displayName, setDisplayName] = React.useState("");
  const [billingInterval, setBillingInterval] =
    React.useState<BillingCadence>("monthly");
  const [submitting, setSubmitting] = React.useState(false);

  const reset = React.useCallback(() => {
    setSlug("");
    setDisplayName("");
    setBillingInterval("monthly");
  }, []);

  React.useEffect(() => {
    if (!open) reset();
  }, [open, reset]);

  const handleSubmit = async () => {
    if (!slug.trim() || !displayName.trim()) return;
    try {
      setSubmitting(true);
      await onCreate({
        slug: slug.trim().toLowerCase(),
        display_name: displayName.trim(),
        billing_interval: billingInterval,
      });
      onOpenChange(false);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        className="flex h-[100dvh] max-h-[100dvh] w-full flex-col gap-0 overflow-hidden p-0 sm:max-w-md"
        onOpenAutoFocus={(event) => {
          event.preventDefault();
          document.getElementById("create-product-slug")?.focus();
        }}
      >
        <SheetHeader className="shrink-0 space-y-2 border-b px-4 pb-4 pr-12 pt-5 text-left sm:px-6 sm:pr-14 sm:pt-6">
          <SheetTitle>New plan product</SheetTitle>
          <SheetDescription>
            Create a billing family (e.g. Starter monthly). A matching Stripe
            Product is created automatically when Stripe is configured.
          </SheetDescription>
        </SheetHeader>

        <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 py-4 sm:px-6">
          <div className="space-y-4">
            <div className="space-y-2">
              <CatalogFieldLabel
                htmlFor="create-product-slug"
                help={PLAN_CATALOG_FIELD_HELP.slug}
              >
                Slug
              </CatalogFieldLabel>
              <Input
                id="create-product-slug"
                value={slug}
                onChange={(e) => setSlug(e.target.value)}
                placeholder="pro-monthly"
              />
            </div>
            <div className="space-y-2">
              <CatalogFieldLabel
                htmlFor="create-product-name"
                help={PLAN_CATALOG_FIELD_HELP.displayName}
              >
                Display name
              </CatalogFieldLabel>
              <Input
                id="create-product-name"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="Pro (Monthly)"
              />
            </div>
            <div className="space-y-2">
              <CatalogFieldLabel help={PLAN_CATALOG_FIELD_HELP.billingInterval}>
                Billing cadence
              </CatalogFieldLabel>
              <Select
                value={billingInterval}
                onValueChange={(v) => setBillingInterval(v as BillingCadence)}
              >
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="monthly">Monthly</SelectItem>
                  <SelectItem value="annual">Annual</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Determines which catalog tab this product appears under. Applied
                to the first draft you create.
              </p>
            </div>
          </div>
        </div>

        <SheetFooter className="mt-auto shrink-0 gap-2 border-t bg-background/95 px-4 py-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] backdrop-blur sm:px-6">
          <Button
            type="button"
            className="w-full sm:w-auto"
            onClick={() => void handleSubmit()}
            disabled={submitting || !slug.trim() || !displayName.trim()}
          >
            {submitting ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : null}
            Create product
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
