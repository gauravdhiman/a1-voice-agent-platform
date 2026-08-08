"use client";

import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  CatalogFieldLabel,
} from "@/components/billing/catalog-help-tooltip";
import {
  PlanProductCreateSheet,
  type PlanProductCreatePayload,
} from "@/components/billing/plan-product-create-sheet";
import { PlanProductsListPanel } from "@/components/billing/plan-products-list-panel";
import { PlanPublishDialog } from "@/components/billing/plan-publish-dialog";
import { StripeSyncAlert } from "@/components/billing/stripe-sync-alert";
import { PlanVersionEntitlementDisplay } from "@/components/billing/plan-version-entitlement-display";
import { PlanVersionEntitlementEditor } from "@/components/billing/plan-version-entitlement-editor";
import { PLAN_CATALOG_FIELD_HELP } from "@/lib/billing/entitlement-catalog-help";
import {
  defaultBillingInterval,
  productHasDraft,
  type BillingCadence,
} from "@/lib/billing/plan-catalog-utils";
import {
  buildEntitlementInputs,
  parseAssignedEntitlements,
  type AssignedPlanEntitlement,
} from "@/lib/billing/plan-version-entitlements";
import { adminPlanService } from "@/services/admin-plan-service";
import type {
  EntitlementDefinition,
  PlanProductWithVersions,
  PlanVersionDetail,
  PlanVersionSummary,
} from "@/types/admin-plans";
import {
  Copy,
  Loader2,
  Plus,
  Save,
  Trash2,
  Upload,
} from "lucide-react";
import { toast } from "sonner";

function statusBadgeVariant(
  status: PlanVersionDetail["status"],
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

/**
 * Platform admin manager for plan products, draft versions, entitlements, and publish.
 *
 * Loads lightweight product + version summaries first; fetches full version detail
 * (including entitlements) only when a version is selected.
 */
export function PlatformPlansManager() {
  const [products, setProducts] = React.useState<PlanProductWithVersions[]>([]);
  const [definitions, setDefinitions] = React.useState<EntitlementDefinition[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [cadenceTab, setCadenceTab] = React.useState<BillingCadence>("monthly");
  const [createSheetOpen, setCreateSheetOpen] = React.useState(false);

  const [selectedVersionId, setSelectedVersionId] = React.useState<string | null>(null);
  const [selectedVersion, setSelectedVersion] = React.useState<PlanVersionDetail | null>(
    null,
  );
  const [loadingVersion, setLoadingVersion] = React.useState(false);

  const [displayLabel, setDisplayLabel] = React.useState("");
  const [priceCents, setPriceCents] = React.useState("0");
  const [billingInterval, setBillingInterval] = React.useState<BillingCadence>("monthly");
  const [stripeProductId, setStripeProductId] = React.useState("");
  const [stripePriceId, setStripePriceId] = React.useState("");
  const [assignedEntitlements, setAssignedEntitlements] = React.useState<
    AssignedPlanEntitlement[]
  >([]);
  const [saving, setSaving] = React.useState(false);
  const [deleting, setDeleting] = React.useState(false);
  const [publishOpen, setPublishOpen] = React.useState(false);
  const [productBillingBySlug, setProductBillingBySlug] = React.useState<
    Record<string, BillingCadence>
  >({});

  const loadCatalog = React.useCallback(async () => {
    try {
      setLoading(true);
      const [productRows, definitionRows] = await Promise.all([
        adminPlanService.listPlanProducts(),
        adminPlanService.listEntitlementDefinitions(),
      ]);
      setProducts(productRows);
      setDefinitions(definitionRows);
    } catch (error) {
      console.error("Failed to load plan catalog:", error);
      toast.error("Failed to load plan catalog");
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void loadCatalog();
  }, [loadCatalog]);

  const applyVersionToForm = React.useCallback(
    (version: PlanVersionDetail, productStripeId?: string | null) => {
      setSelectedVersion(version);
      setDisplayLabel(version.display_label ?? "");
      setPriceCents(String(version.price_amount_cents));
      setBillingInterval(version.billing_interval === "annual" ? "annual" : "monthly");
      setStripeProductId(version.stripe_product_id ?? productStripeId ?? "");
      setStripePriceId(version.stripe_price_id ?? "");
      setAssignedEntitlements(parseAssignedEntitlements(version));
    },
    [],
  );

  const loadVersionDetail = React.useCallback(
    async (versionId: string) => {
      try {
        setLoadingVersion(true);
        setSelectedVersionId(versionId);
        const detail = await adminPlanService.getPlanVersion(versionId);
        const product = products.find((p) => p.id === detail.plan_product_id);
        applyVersionToForm(detail, product?.stripe_product_id);
      } catch (error) {
        console.error("Failed to load plan version:", error);
        toast.error("Failed to load plan version details");
        setSelectedVersionId(null);
        setSelectedVersion(null);
      } finally {
        setLoadingVersion(false);
      }
    },
    [applyVersionToForm, products],
  );

  const handleSelectVersion = (version: PlanVersionSummary) => {
    void loadVersionDetail(version.id);
  };

  const handleSaveDraft = async () => {
    if (!selectedVersion || selectedVersion.status !== "draft") return;
    try {
      setSaving(true);
      const entitlements = buildEntitlementInputs(assignedEntitlements, definitions);
      const updated = await adminPlanService.updateDraftVersion(selectedVersion.id, {
        display_label: displayLabel || undefined,
        price_amount_cents: Number(priceCents) || 0,
        billing_interval: billingInterval,
        stripe_product_id: stripeProductId.trim() || null,
        stripe_price_id: stripePriceId.trim() || null,
        entitlements,
      });
      applyVersionToForm(updated);
      toast.success("Draft saved");
      await loadCatalog();
    } catch (error) {
      console.error("Save draft failed:", error);
      toast.error(error instanceof Error ? error.message : "Failed to save draft");
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteDraft = async () => {
    if (!selectedVersion || selectedVersion.status !== "draft") return;
    try {
      setDeleting(true);
      await adminPlanService.deleteDraftVersion(selectedVersion.id);
      toast.success("Draft deleted");
      setSelectedVersionId(null);
      setSelectedVersion(null);
      await loadCatalog();
    } catch (error) {
      console.error("Delete draft failed:", error);
      toast.error("Failed to delete draft");
    } finally {
      setDeleting(false);
    }
  };

  const handleCreateProduct = async (payload: PlanProductCreatePayload) => {
    try {
      const result = await adminPlanService.createPlanProduct({
        slug: payload.slug,
        display_name: payload.display_name,
      });
      setProductBillingBySlug((prev) => ({
        ...prev,
        [payload.slug]: payload.billing_interval,
      }));
      setCadenceTab(payload.billing_interval);
      if (result.stripe_auto_create_error) {
        toast.warning("Plan product created — link Stripe Product manually", {
          description: result.stripe_auto_create_error,
        });
      } else {
        toast.success("Plan product created and linked to Stripe");
      }
      await loadCatalog();
    } catch (error) {
      console.error("Create product failed:", error);
      toast.error("Failed to create plan product");
      throw error;
    }
  };

  const selectedProduct = React.useMemo(
    () =>
      selectedVersion
        ? products.find((p) => p.id === selectedVersion.plan_product_id)
        : undefined,
    [products, selectedVersion],
  );

  const productStripeLinked = Boolean(
    stripeProductId.trim() ||
      selectedProduct?.stripe_product_id ||
      selectedVersion?.stripe_product_id,
  );

  const handleCreateDraft = async (product: PlanProductWithVersions) => {
    if (productHasDraft(product)) {
      toast.error("This product already has a draft. Publish or delete it first.");
      return;
    }
    try {
      const interval =
        productBillingBySlug[product.slug] ?? defaultBillingInterval(product);
      const draft = await adminPlanService.createDraftVersion(product.id, {
        display_label: "New draft",
        price_amount_cents: 0,
        billing_interval: interval,
      });
      toast.success("Draft version created");
      await loadCatalog();
      await loadVersionDetail(draft.id);
    } catch (error) {
      console.error("Create draft failed:", error);
      toast.error(
        error instanceof Error ? error.message : "Failed to create draft version",
      );
    }
  };

  const handleClone = async (versionId: string) => {
    try {
      const draft = await adminPlanService.clonePlanVersion(versionId, {});
      toast.success("Cloned to new draft");
      await loadCatalog();
      await loadVersionDetail(draft.id);
    } catch (error) {
      console.error("Clone failed:", error);
      toast.error(error instanceof Error ? error.message : "Failed to clone version");
    }
  };

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading plan catalog…
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold">Plan catalog</h2>
          <p className="text-sm text-muted-foreground">
            Manage billing products, version snapshots, and entitlements.
          </p>
        </div>
        <Button onClick={() => setCreateSheetOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          New plan product
        </Button>
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(280px,1fr)_minmax(320px,1.2fr)]">
        <PlanProductsListPanel
          products={products}
          cadenceTab={cadenceTab}
          onCadenceTabChange={setCadenceTab}
          selectedVersionId={selectedVersionId}
          onSelectVersion={handleSelectVersion}
          onCreateDraft={(product) => void handleCreateDraft(product)}
          productBillingBySlug={productBillingBySlug}
        />

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Version details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {loadingVersion ? (
              <div className="flex items-center gap-2 text-muted-foreground py-8">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading version…
              </div>
            ) : !selectedVersion ? (
              <p className="text-sm text-muted-foreground py-8 text-center">
                Select a version from the list to view or edit details.
              </p>
            ) : (
              <>
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant={statusBadgeVariant(selectedVersion.status)}>
                    {selectedVersion.status}
                  </Badge>
                  <Badge variant="outline">
                    {selectedVersion.billing_interval === "annual"
                      ? "Annual billing"
                      : "Monthly billing"}
                  </Badge>
                  <span className="text-sm text-muted-foreground">
                    v{selectedVersion.version_number}
                  </span>
                </div>

                {selectedVersion.status === "draft" ? (
                  <>
                    <div className="space-y-2">
                      <CatalogFieldLabel
                        htmlFor="display-label"
                        help={PLAN_CATALOG_FIELD_HELP.displayLabel}
                      >
                        Display label
                      </CatalogFieldLabel>
                      <Input
                        id="display-label"
                        value={displayLabel}
                        onChange={(e) => setDisplayLabel(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <CatalogFieldLabel
                        htmlFor="billing-interval"
                        help={PLAN_CATALOG_FIELD_HELP.billingInterval}
                      >
                        Billing interval
                      </CatalogFieldLabel>
                      <Select
                        value={billingInterval}
                        onValueChange={(v) =>
                          setBillingInterval(v as BillingCadence)
                        }
                      >
                        <SelectTrigger id="billing-interval" className="w-full">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="monthly">Monthly</SelectItem>
                          <SelectItem value="annual">Annual</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <CatalogFieldLabel
                        htmlFor="price-cents"
                        help={PLAN_CATALOG_FIELD_HELP.priceCents}
                      >
                        Price (cents)
                      </CatalogFieldLabel>
                      <Input
                        id="price-cents"
                        type="number"
                        min={0}
                        value={priceCents}
                        onChange={(e) => setPriceCents(e.target.value)}
                      />
                    </div>

                    {!productStripeLinked ? (
                      <StripeSyncAlert
                        title="Stripe Product not linked"
                        message="Auto-create may have failed when this plan product was added. Create a Product in Stripe Dashboard, paste prod_… below, save the draft, then publish."
                      />
                    ) : null}

                    <div className="space-y-2">
                      <CatalogFieldLabel
                        htmlFor="stripe-product-id"
                        help={PLAN_CATALOG_FIELD_HELP.stripeProductId}
                      >
                        Stripe product ID
                      </CatalogFieldLabel>
                      <Input
                        id="stripe-product-id"
                        value={stripeProductId}
                        onChange={(e) => setStripeProductId(e.target.value)}
                        placeholder="prod_…"
                      />
                    </div>
                    <div className="space-y-2">
                      <CatalogFieldLabel
                        htmlFor="stripe-price-id"
                        help={PLAN_CATALOG_FIELD_HELP.stripePriceId}
                      >
                        Stripe price ID (optional fallback)
                      </CatalogFieldLabel>
                      <Input
                        id="stripe-price-id"
                        value={stripePriceId}
                        onChange={(e) => setStripePriceId(e.target.value)}
                        placeholder="price_…"
                      />
                      <p className="text-xs text-muted-foreground">
                        Leave empty to auto-create on publish. Set manually if Stripe
                        Price creation fails.
                      </p>
                    </div>

                    <PlanVersionEntitlementEditor
                      definitions={definitions}
                      assigned={assignedEntitlements}
                      onChange={setAssignedEntitlements}
                    />

                    <div className="flex flex-wrap gap-2">
                      <Button onClick={() => void handleSaveDraft()} disabled={saving}>
                        {saving ? (
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        ) : (
                          <Save className="mr-2 h-4 w-4" />
                        )}
                        Save draft
                      </Button>
                      <Button variant="default" onClick={() => setPublishOpen(true)}>
                        <Upload className="mr-2 h-4 w-4" />
                        Publish
                      </Button>
                      <Button
                        variant="destructive"
                        onClick={() => void handleDeleteDraft()}
                        disabled={deleting}
                      >
                        {deleting ? (
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        ) : (
                          <Trash2 className="mr-2 h-4 w-4" />
                        )}
                        Delete draft
                      </Button>
                    </div>
                  </>
                ) : (
                  <div className="space-y-4">
                    <div className="grid gap-3 sm:grid-cols-2 text-sm">
                      <div>
                        <p className="text-muted-foreground">Display label</p>
                        <p className="font-medium">
                          {selectedVersion.display_label ?? "—"}
                        </p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Price</p>
                        <p className="font-medium">
                          {new Intl.NumberFormat("en-US", {
                            style: "currency",
                            currency: selectedVersion.currency || "USD",
                          }).format(selectedVersion.price_amount_cents / 100)}
                        </p>
                      </div>
                      {selectedVersion.stripe_price_id ? (
                        <div className="sm:col-span-2">
                          <p className="text-muted-foreground">Stripe price ID</p>
                          <p className="font-mono text-xs">
                            {selectedVersion.stripe_price_id}
                          </p>
                        </div>
                      ) : null}
                    </div>

                    <PlanVersionEntitlementDisplay
                      version={selectedVersion}
                      definitions={definitions}
                    />

                    <p className="text-sm text-muted-foreground">
                      Published versions are immutable. Clone to create a new draft.
                    </p>
                    <Button
                      variant="outline"
                      disabled={products.some(
                        (p) =>
                          p.id === selectedVersion.plan_product_id &&
                          productHasDraft(p),
                      )}
                      onClick={() => void handleClone(selectedVersion.id)}
                    >
                      <Copy className="mr-2 h-4 w-4" />
                      Clone to draft
                    </Button>
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>
      </div>

      <PlanProductCreateSheet
        open={createSheetOpen}
        onOpenChange={setCreateSheetOpen}
        onCreate={handleCreateProduct}
      />

      <PlanPublishDialog
        version={selectedVersion?.status === "draft" ? selectedVersion : null}
        open={publishOpen}
        onOpenChange={setPublishOpen}
        onPublished={() => {
          void loadCatalog();
          setSelectedVersionId(null);
          setSelectedVersion(null);
        }}
      />
    </div>
  );
}
