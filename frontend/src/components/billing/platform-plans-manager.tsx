"use client";

import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PlanPublishDialog } from "@/components/billing/plan-publish-dialog";
import { adminPlanService } from "@/services/admin-plan-service";
import type {
  EntitlementDefinition,
  PlanProductWithVersions,
  PlanVersionDetail,
  PlanVersionEntitlementInput,
} from "@/types/admin-plans";
import {
  Copy,
  Loader2,
  Plus,
  Save,
  Upload,
} from "lucide-react";
import { toast } from "sonner";

function formatPrice(cents: number, currency: string): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: currency || "USD",
  }).format(cents / 100);
}

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
 */
export function PlatformPlansManager() {
  const [products, setProducts] = React.useState<PlanProductWithVersions[]>([]);
  const [definitions, setDefinitions] = React.useState<EntitlementDefinition[]>(
    [],
  );
  const [loading, setLoading] = React.useState(true);
  const [selectedVersion, setSelectedVersion] =
    React.useState<PlanVersionDetail | null>(null);
  const [displayLabel, setDisplayLabel] = React.useState("");
  const [priceCents, setPriceCents] = React.useState("0");
  const [entitlementValues, setEntitlementValues] = React.useState<
    Record<string, string>
  >({});
  const [saving, setSaving] = React.useState(false);
  const [publishOpen, setPublishOpen] = React.useState(false);
  const [newProductSlug, setNewProductSlug] = React.useState("");
  const [newProductName, setNewProductName] = React.useState("");

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

  const selectVersion = (version: PlanVersionDetail) => {
    setSelectedVersion(version);
    setDisplayLabel(version.display_label ?? "");
    setPriceCents(String(version.price_amount_cents));
    const values: Record<string, string> = {};
    for (const ent of version.entitlements) {
      const raw = ent.value?.value;
      values[ent.entitlement_key] =
        raw === undefined || raw === null ? "" : String(raw);
    }
    setEntitlementValues(values);
  };

  const buildEntitlementInputs = (): PlanVersionEntitlementInput[] => {
    return definitions
      .filter((def) => entitlementValues[def.key]?.trim() !== "")
      .map((def) => {
        const raw = entitlementValues[def.key]?.trim() ?? "";
        if (def.value_type === "boolean") {
          return {
            entitlement_key: def.key,
            value: { type: "boolean", value: raw === "true" },
          };
        }
        if (def.value_type === "unlimited") {
          return {
            entitlement_key: def.key,
            value: { type: "unlimited" },
          };
        }
        return {
          entitlement_key: def.key,
          value: { type: "integer", value: Number(raw) || 0 },
        };
      });
  };

  const handleSaveDraft = async () => {
    if (!selectedVersion || selectedVersion.status !== "draft") return;
    try {
      setSaving(true);
      const updated = await adminPlanService.updateDraftVersion(
        selectedVersion.id,
        {
          display_label: displayLabel || undefined,
          price_amount_cents: Number(priceCents) || 0,
          entitlements: buildEntitlementInputs(),
        },
      );
      toast.success("Draft saved");
      setSelectedVersion(updated);
      await loadCatalog();
    } catch (error) {
      console.error("Save draft failed:", error);
      toast.error("Failed to save draft");
    } finally {
      setSaving(false);
    }
  };

  const handleCreateProduct = async () => {
    if (!newProductSlug.trim() || !newProductName.trim()) {
      toast.error("Slug and display name are required");
      return;
    }
    try {
      await adminPlanService.createPlanProduct({
        slug: newProductSlug.trim(),
        display_name: newProductName.trim(),
      });
      setNewProductSlug("");
      setNewProductName("");
      toast.success("Plan product created");
      await loadCatalog();
    } catch (error) {
      console.error("Create product failed:", error);
      toast.error("Failed to create plan product");
    }
  };

  const handleCreateDraft = async (productId: string) => {
    try {
      const draft = await adminPlanService.createDraftVersion(productId, {
        display_label: "New draft",
        price_amount_cents: 0,
      });
      toast.success("Draft version created");
      await loadCatalog();
      selectVersion(draft);
    } catch (error) {
      console.error("Create draft failed:", error);
      toast.error("Failed to create draft version");
    }
  };

  const handleClone = async (versionId: string) => {
    try {
      const draft = await adminPlanService.clonePlanVersion(versionId, {});
      toast.success("Cloned to new draft");
      await loadCatalog();
      selectVersion(draft);
    } catch (error) {
      console.error("Clone failed:", error);
      toast.error("Failed to clone version");
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
    <div className="grid gap-6 lg:grid-cols-[1fr_1fr]">
      <div className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Plan products</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {products.map((product) => (
              <div key={product.id} className="rounded-lg border p-4 space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="font-medium">{product.display_name}</p>
                    <p className="text-sm text-muted-foreground">{product.slug}</p>
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => void handleCreateDraft(product.id)}
                  >
                    <Plus className="mr-1 h-3 w-3" />
                    Draft
                  </Button>
                </div>
                <div className="space-y-2">
                  {product.versions.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No versions yet.</p>
                  ) : (
                    product.versions.map((version) => (
                      <button
                        key={version.id}
                        type="button"
                        onClick={() => selectVersion(version)}
                        className={`flex w-full items-center justify-between rounded-md border px-3 py-2 text-left text-sm transition hover:bg-muted/50 ${
                          selectedVersion?.id === version.id
                            ? "border-primary bg-muted/30"
                            : ""
                        }`}
                      >
                        <span>
                          v{version.version_number}
                          {version.display_label ? ` — ${version.display_label}` : ""}
                          {version.is_current_for_signup ? " (current signup)" : ""}
                        </span>
                        <span className="flex items-center gap-2">
                          <Badge variant={statusBadgeVariant(version.status)}>
                            {version.status}
                          </Badge>
                          <span className="text-muted-foreground">
                            {formatPrice(version.price_amount_cents, version.currency)}
                          </span>
                        </span>
                      </button>
                    ))
                  )}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">New product</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-2">
              <Label htmlFor="product-slug">Slug</Label>
              <Input
                id="product-slug"
                value={newProductSlug}
                onChange={(e) => setNewProductSlug(e.target.value)}
                placeholder="pro"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="product-name">Display name</Label>
              <Input
                id="product-name"
                value={newProductName}
                onChange={(e) => setNewProductName(e.target.value)}
                placeholder="Pro"
              />
            </div>
            <Button onClick={() => void handleCreateProduct()}>Create product</Button>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Version editor</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {!selectedVersion ? (
            <p className="text-sm text-muted-foreground">
              Select a version to edit or publish.
            </p>
          ) : (
            <>
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant={statusBadgeVariant(selectedVersion.status)}>
                  {selectedVersion.status}
                </Badge>
                <span className="text-sm text-muted-foreground">
                  v{selectedVersion.version_number}
                </span>
              </div>

              {selectedVersion.status === "draft" ? (
                <>
                  <div className="space-y-2">
                    <Label htmlFor="display-label">Display label</Label>
                    <Input
                      id="display-label"
                      value={displayLabel}
                      onChange={(e) => setDisplayLabel(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="price-cents">Price (cents)</Label>
                    <Input
                      id="price-cents"
                      type="number"
                      min={0}
                      value={priceCents}
                      onChange={(e) => setPriceCents(e.target.value)}
                    />
                  </div>

                  <div className="space-y-3">
                    <p className="text-sm font-medium">Entitlements</p>
                    {definitions.map((def) => (
                      <div key={def.key} className="space-y-1">
                        <Label htmlFor={`ent-${def.key}`}>{def.display_name}</Label>
                        <Input
                          id={`ent-${def.key}`}
                          value={entitlementValues[def.key] ?? ""}
                          placeholder={
                            def.value_type === "boolean"
                              ? "true / false"
                              : def.value_type === "unlimited"
                                ? "leave empty unless unlimited"
                                : "integer limit"
                          }
                          onChange={(e) =>
                            setEntitlementValues((prev) => ({
                              ...prev,
                              [def.key]: e.target.value,
                            }))
                          }
                        />
                        <p className="text-xs text-muted-foreground">{def.key}</p>
                      </div>
                    ))}
                  </div>

                  <div className="flex flex-wrap gap-2">
                    <Button onClick={() => void handleSaveDraft()} disabled={saving}>
                      {saving ? (
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      ) : (
                        <Save className="mr-2 h-4 w-4" />
                      )}
                      Save draft
                    </Button>
                    <Button
                      variant="default"
                      onClick={() => setPublishOpen(true)}
                    >
                      <Upload className="mr-2 h-4 w-4" />
                      Publish
                    </Button>
                  </div>
                </>
              ) : (
                <div className="space-y-3">
                  <p className="text-sm text-muted-foreground">
                    Published versions are immutable. Clone to create a new draft.
                  </p>
                  <Button
                    variant="outline"
                    onClick={() => void handleClone(selectedVersion.id)}
                  >
                    <Copy className="mr-2 h-4 w-4" />
                    Clone to draft
                  </Button>
                  <ul className="text-sm space-y-1">
                    {selectedVersion.entitlements.map((ent) => (
                      <li key={ent.id}>
                        <span className="font-medium">{ent.entitlement_key}</span>:{" "}
                        {JSON.stringify(ent.value)}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      <PlanPublishDialog
        version={selectedVersion?.status === "draft" ? selectedVersion : null}
        open={publishOpen}
        onOpenChange={setPublishOpen}
        onPublished={() => {
          void loadCatalog();
          setSelectedVersion(null);
        }}
      />
    </div>
  );
}
