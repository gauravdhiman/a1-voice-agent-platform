"use client";

import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { adminPlanService } from "@/services/admin-plan-service";
import type { EntitlementDefinition } from "@/types/admin-plans";
import { Loader2, Save } from "lucide-react";
import { toast } from "sonner";

/**
 * Platform admin surface for editing entitlement catalog display metadata.
 */
export function PlatformEntitlementsManager() {
  const [definitions, setDefinitions] = React.useState<EntitlementDefinition[]>(
    [],
  );
  const [loading, setLoading] = React.useState(true);
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
      {definitions.map((def) => {
        const draft = drafts[def.key];
        if (!draft) return null;
        return (
          <Card key={def.key}>
            <CardHeader className="pb-3">
              <div className="flex flex-wrap items-center gap-2">
                <CardTitle className="text-base">{def.key}</CardTitle>
                <Badge variant="outline">{def.kind}</Badge>
                <Badge variant="secondary">{def.value_type}</Badge>
                {!draft.is_active ? (
                  <Badge variant="destructive">Inactive</Badge>
                ) : null}
              </div>
              <p className="text-sm text-muted-foreground">
                Handler: {def.enforcement_handler}
              </p>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="space-y-2">
                <Label htmlFor={`display-${def.key}`}>Display name</Label>
                <Input
                  id={`display-${def.key}`}
                  value={draft.display_name}
                  onChange={(e) =>
                    setDrafts((prev) => ({
                      ...prev,
                      [def.key]: { ...prev[def.key], display_name: e.target.value },
                    }))
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor={`desc-${def.key}`}>Description</Label>
                <Input
                  id={`desc-${def.key}`}
                  value={draft.description}
                  onChange={(e) =>
                    setDrafts((prev) => ({
                      ...prev,
                      [def.key]: { ...prev[def.key], description: e.target.value },
                    }))
                  }
                />
              </div>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={draft.is_active}
                  onChange={(e) =>
                    setDrafts((prev) => ({
                      ...prev,
                      [def.key]: { ...prev[def.key], is_active: e.target.checked },
                    }))
                  }
                />
                Active in catalog
              </label>
              <Button
                size="sm"
                onClick={() => void handleSave(def.key)}
                disabled={savingKey === def.key}
              >
                {savingKey === def.key ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Save className="mr-2 h-4 w-4" />
                )}
                Save
              </Button>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
