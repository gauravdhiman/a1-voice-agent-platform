"use client";

import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  CatalogFieldLabel,
  CatalogHelpTooltip,
} from "@/components/billing/catalog-help-tooltip";
import { entitlementHelpText } from "@/lib/billing/entitlement-catalog-help";
import { adminPlanService } from "@/services/admin-plan-service";
import type { EntitlementDefinition, EntitlementKind } from "@/types/admin-plans";
import { cn } from "@/lib/utils";
import { Loader2, Save } from "lucide-react";
import { toast } from "sonner";

const ENTITLEMENT_CATALOG_INTRO =
  "Platform-defined limits and features enforced by EntitlementService. Keys and handlers are code-defined; you edit display metadata and active status here.";

/**
 * Platform admin surface for editing entitlement catalog display metadata.
 *
 * Uses a master-detail layout with Limits / Features tabs to reduce visual noise.
 */
export function PlatformEntitlementsManager() {
  const [definitions, setDefinitions] = React.useState<EntitlementDefinition[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [kindTab, setKindTab] = React.useState<EntitlementKind>("limit");
  const [selectedKey, setSelectedKey] = React.useState<string | null>(null);
  const [savingKey, setSavingKey] = React.useState<string | null>(null);
  const [drafts, setDrafts] = React.useState<
    Record<string, { display_name: string; description: string; is_active: boolean }>
  >({});

  const loadDefinitions = React.useCallback(async () => {
    try {
      setLoading(true);
      const rows = await adminPlanService.listEntitlementDefinitions();
      setDefinitions(rows);
      setDrafts(
        Object.fromEntries(
          rows.map((row) => [
            row.key,
            {
              display_name: row.display_name,
              description: row.description ?? "",
              is_active: row.is_active,
            },
          ]),
        ),
      );
    } catch (error) {
      console.error("Failed to load entitlement definitions:", error);
      toast.error("Failed to load entitlement catalog");
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void loadDefinitions();
  }, [loadDefinitions]);

  const limits = definitions.filter((d) => d.kind === "limit");
  const features = definitions.filter((d) => d.kind === "feature");

  const visibleDefinitions = kindTab === "limit" ? limits : features;

  React.useEffect(() => {
    if (visibleDefinitions.length === 0) {
      setSelectedKey(null);
      return;
    }
    if (!selectedKey || !visibleDefinitions.some((d) => d.key === selectedKey)) {
      setSelectedKey(visibleDefinitions[0].key);
    }
  }, [kindTab, visibleDefinitions, selectedKey]);

  const selectedDefinition = definitions.find((d) => d.key === selectedKey);
  const selectedDraft = selectedKey ? drafts[selectedKey] : undefined;

  const handleSave = async (key: string) => {
    const draft = drafts[key];
    if (!draft) return;
    try {
      setSavingKey(key);
      await adminPlanService.updateEntitlementDefinition(key, {
        display_name: draft.display_name,
        description: draft.description || null,
        is_active: draft.is_active,
      });
      toast.success(`Updated ${key}`);
      await loadDefinitions();
    } catch (error) {
      console.error("Update entitlement failed:", error);
      toast.error("Failed to update entitlement");
    } finally {
      setSavingKey(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading entitlement catalog…
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold flex items-center gap-2">
          Entitlement catalog
          <CatalogHelpTooltip content={ENTITLEMENT_CATALOG_INTRO} />
        </h2>
        <p className="text-sm text-muted-foreground mt-1 max-w-2xl">
          {ENTITLEMENT_CATALOG_INTRO}
        </p>
      </div>

      <Tabs
        value={kindTab}
        onValueChange={(v) => setKindTab(v as EntitlementKind)}
      >
        <TabsList>
          <TabsTrigger value="limit">
            Limits
            <Badge variant="secondary" className="ml-2">
              {limits.length}
            </Badge>
          </TabsTrigger>
          <TabsTrigger value="feature">
            Features
            <Badge variant="secondary" className="ml-2">
              {features.length}
            </Badge>
          </TabsTrigger>
        </TabsList>

        {(["limit", "feature"] as const).map((kind) => (
          <TabsContent key={kind} value={kind} className="mt-4">
            <div className="grid gap-4 lg:grid-cols-[minmax(240px,1fr)_minmax(320px,1.4fr)]">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">
                    {kind === "limit" ? "Usage limits" : "Feature flags"}
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                  <ul className="max-h-[calc(100vh-320px)] overflow-y-auto divide-y">
                    {(kind === "limit" ? limits : features).map((def) => {
                      const draft = drafts[def.key];
                      const isSelected = selectedKey === def.key;
                      return (
                        <li key={def.key}>
                          <button
                            type="button"
                            onClick={() => setSelectedKey(def.key)}
                            className={cn(
                              "w-full px-4 py-3 text-left transition hover:bg-muted/50",
                              isSelected && "bg-muted/40 border-l-2 border-l-primary",
                            )}
                          >
                            <div className="flex items-start justify-between gap-2">
                              <div className="min-w-0">
                                <p className="font-medium text-sm truncate">
                                  {def.display_name}
                                </p>
                                <p className="text-xs text-muted-foreground font-mono truncate">
                                  {def.key}
                                </p>
                              </div>
                              {!def.is_active ? (
                                <Badge
                                  variant="outline"
                                  className="shrink-0 text-muted-foreground font-normal border-border/80 bg-muted/40"
                                >
                                  Inactive
                                </Badge>
                              ) : null}
                            </div>
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Definition details</CardTitle>
                </CardHeader>
                <CardContent>
                  {!selectedDefinition || !selectedDraft ? (
                    <p className="text-sm text-muted-foreground">
                      Select an entitlement to edit its catalog metadata.
                    </p>
                  ) : (
                    <EntitlementDefinitionEditor
                      definition={selectedDefinition}
                      draft={selectedDraft}
                      saving={savingKey === selectedDefinition.key}
                      onDraftChange={(patch) =>
                        setDrafts((prev) => ({
                          ...prev,
                          [selectedDefinition.key]: {
                            ...prev[selectedDefinition.key],
                            ...patch,
                          },
                        }))
                      }
                      onSave={() => void handleSave(selectedDefinition.key)}
                    />
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
}

interface EntitlementDefinitionEditorProps {
  definition: EntitlementDefinition;
  draft: { display_name: string; description: string; is_active: boolean };
  saving: boolean;
  onDraftChange: (
    patch: Partial<{ display_name: string; description: string; is_active: boolean }>,
  ) => void;
  onSave: () => void;
}

function EntitlementDefinitionEditor({
  definition,
  draft,
  saving,
  onDraftChange,
  onSave,
}: EntitlementDefinitionEditorProps) {
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-sm">{definition.key}</span>
        <Badge variant="outline">{definition.kind}</Badge>
        <Badge variant="secondary">{definition.value_type}</Badge>
        {definition.unit ? (
          <Badge variant="outline">{definition.unit}</Badge>
        ) : null}
      </div>

      <div className="rounded-md bg-muted/30 p-3 text-sm text-muted-foreground space-y-1">
        <p>{entitlementHelpText(definition.key)}</p>
        <p className="text-xs">
          Handler: <span className="font-mono">{definition.enforcement_handler}</span>
        </p>
      </div>

      <div className="space-y-2">
        <CatalogFieldLabel htmlFor={`display-${definition.key}`}>
          Display name
        </CatalogFieldLabel>
        <Input
          id={`display-${definition.key}`}
          value={draft.display_name}
          onChange={(e) => onDraftChange({ display_name: e.target.value })}
        />
      </div>

      <div className="space-y-2">
        <CatalogFieldLabel htmlFor={`desc-${definition.key}`}>
          Description (admin UI)
        </CatalogFieldLabel>
        <Input
          id={`desc-${definition.key}`}
          value={draft.description}
          onChange={(e) => onDraftChange({ description: e.target.value })}
        />
      </div>

      <div className="flex items-center gap-2">
        <Switch
          id={`active-${definition.key}`}
          checked={draft.is_active}
          onCheckedChange={(checked) => onDraftChange({ is_active: checked })}
        />
        <Label htmlFor={`active-${definition.key}`}>Active in plan catalog</Label>
        <CatalogHelpTooltip content="When off, this entitlement is hidden when assigning entitlements to plan versions. Enforcement code still exists in the platform." />
      </div>

      <Button size="sm" onClick={onSave} disabled={saving}>
        {saving ? (
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        ) : (
          <Save className="mr-2 h-4 w-4" />
        )}
        Save changes
      </Button>
    </div>
  );
}
