"use client";

import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { CatalogFieldLabel } from "@/components/billing/catalog-help-tooltip";
import {
  entitlementHelpText,
  PLAN_CATALOG_FIELD_HELP,
} from "@/lib/billing/entitlement-catalog-help";
import type { AssignedPlanEntitlement } from "@/lib/billing/plan-version-entitlements";
import type { EntitlementDefinition } from "@/types/admin-plans";
import { motion, useReducedMotion } from "framer-motion";
import {
  ChevronDown,
  ChevronUp,
  GripVertical,
  Plus,
  Trash2,
} from "lucide-react";

interface PlanVersionEntitlementEditorProps {
  definitions: EntitlementDefinition[];
  assigned: AssignedPlanEntitlement[];
  onChange: (next: AssignedPlanEntitlement[]) => void;
}

/**
 * Draft-only editor: explicitly add/remove entitlements with type-appropriate controls.
 */
export function PlanVersionEntitlementEditor({
  definitions,
  assigned,
  onChange,
}: PlanVersionEntitlementEditorProps) {
  const [addKey, setAddKey] = React.useState<string>("");
  const [draggedKey, setDraggedKey] = React.useState<string | null>(null);
  const [lastDragOverKey, setLastDragOverKey] = React.useState<string | null>(
    null,
  );
  const reducedMotion = useReducedMotion();

  const activeDefinitions = definitions.filter((d) => d.is_active);
  const assignedKeys = new Set(assigned.map((a) => a.key));
  const availableToAdd = activeDefinitions.filter(
    (d) => !assignedKeys.has(d.key),
  );

  const defByKey = React.useMemo(
    () => new Map(definitions.map((d) => [d.key, d])),
    [definitions],
  );

  const updateItem = (key: string, patch: Partial<AssignedPlanEntitlement>) => {
    onChange(
      assigned.map((item) => (item.key === key ? { ...item, ...patch } : item)),
    );
  };

  const removeItem = (key: string) => {
    onChange(assigned.filter((item) => item.key !== key));
  };

  const moveItem = (fromIndex: number, toIndex: number) => {
    if (toIndex < 0 || toIndex >= assigned.length || fromIndex === toIndex)
      return;
    const next = [...assigned];
    const [moved] = next.splice(fromIndex, 1);
    next.splice(toIndex, 0, moved);
    onChange(next);
  };

  const moveDraggedItemTo = (targetKey: string) => {
    if (
      !draggedKey ||
      draggedKey === targetKey ||
      lastDragOverKey === targetKey
    ) {
      return;
    }
    const fromIndex = assigned.findIndex((item) => item.key === draggedKey);
    const targetIndex = assigned.findIndex((item) => item.key === targetKey);
    if (fromIndex >= 0 && targetIndex >= 0) {
      moveItem(fromIndex, targetIndex);
      setLastDragOverKey(targetKey);
    }
  };

  const handleDrop = (targetKey: string) => {
    moveDraggedItemTo(targetKey);
    setDraggedKey(null);
    setLastDragOverKey(null);
  };

  const handleAdd = () => {
    if (!addKey) return;
    const def = defByKey.get(addKey);
    if (!def || assignedKeys.has(addKey)) return;

    let next: AssignedPlanEntitlement = { key: addKey };
    if (def.value_type === "boolean") {
      next = { key: addKey, booleanValue: false };
    } else if (def.value_type === "unlimited") {
      next = { key: addKey, unlimited: true };
    } else {
      next = { key: addKey, integerValue: 0 };
    }
    onChange([...assigned, next]);
    setAddKey("");
  };

  return (
    <div className="space-y-4">
      <div>
        <CatalogFieldLabel help={PLAN_CATALOG_FIELD_HELP.sparseEntitlements}>
          Entitlements on this version
        </CatalogFieldLabel>
        <p className="text-xs text-muted-foreground mt-1">
          Add only what this plan includes. Removed keys are not stored and fall
          back to catalog defaults at runtime.
        </p>
      </div>

      {assigned.length === 0 ? (
        <p className="text-sm text-muted-foreground rounded-md border border-dashed p-4">
          No entitlements assigned yet. Add limits and features below.
        </p>
      ) : (
        <div
          className="space-y-3"
          role="list"
          aria-label="Entitlements in display order"
        >
          {assigned.map((item, index) => {
            const def = defByKey.get(item.key);
            if (!def) return null;
            return (
              <motion.div
                key={item.key}
                data-testid={`entitlement-item-${item.key}`}
                data-reorder-animated="true"
                draggable
                onDragStart={() => {
                  setDraggedKey(item.key);
                  setLastDragOverKey(null);
                }}
                onDragEnd={() => {
                  setDraggedKey(null);
                  setLastDragOverKey(null);
                }}
                onDragOver={(event) => {
                  event.preventDefault();
                  moveDraggedItemTo(item.key);
                }}
                onDrop={() => handleDrop(item.key)}
                role="listitem"
                layout
                transition={
                  reducedMotion
                    ? { duration: 0 }
                    : {
                        layout: {
                          duration: 0.24,
                          ease: [0.22, 1, 0.36, 1],
                        },
                      }
                }
                animate={{
                  scale: draggedKey === item.key ? 1.015 : 1,
                  opacity: draggedKey === item.key ? 0.92 : 1,
                }}
                aria-grabbed={draggedKey === item.key}
                className={`relative rounded-lg border p-3 space-y-2 bg-muted/20 ${
                  draggedKey === item.key
                    ? "z-10 border-primary/50 bg-background shadow-xl ring-2 ring-primary/20"
                    : ""
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex min-w-0 items-start gap-2">
                    <GripVertical
                      className="mt-0.5 h-4 w-4 shrink-0 cursor-grab text-muted-foreground"
                      aria-hidden="true"
                    />
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-medium text-sm">
                          {def.display_name}
                        </span>
                        <Badge variant="outline">{def.kind}</Badge>
                        <Badge variant="secondary">{def.value_type}</Badge>
                      </div>
                      <p className="text-xs text-muted-foreground mt-1">
                        {item.key}
                      </p>
                    </div>
                  </div>
                  <div className="flex shrink-0 items-center gap-1">
                    <Button
                      type="button"
                      size="icon"
                      variant="ghost"
                      aria-label={`Move ${def.display_name} up`}
                      onClick={() => moveItem(index, index - 1)}
                      disabled={index === 0}
                    >
                      <ChevronUp className="h-4 w-4" />
                    </Button>
                    <Button
                      type="button"
                      size="icon"
                      variant="ghost"
                      aria-label={`Move ${def.display_name} down`}
                      onClick={() => moveItem(index, index + 1)}
                      disabled={index === assigned.length - 1}
                    >
                      <ChevronDown className="h-4 w-4" />
                    </Button>
                    <Button
                      type="button"
                      size="icon"
                      variant="ghost"
                      aria-label={`Remove ${def.display_name}`}
                      onClick={() => removeItem(item.key)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
                <p className="text-xs text-muted-foreground">
                  {entitlementHelpText(item.key)}
                </p>

                {def.value_type === "boolean" ? (
                  <div className="flex items-center gap-2">
                    <Switch
                      id={`ent-bool-${item.key}`}
                      checked={item.booleanValue === true}
                      onCheckedChange={(checked) =>
                        updateItem(item.key, { booleanValue: checked })
                      }
                    />
                    <Label htmlFor={`ent-bool-${item.key}`}>
                      {item.booleanValue ? "Enabled" : "Disabled"}
                    </Label>
                  </div>
                ) : def.value_type === "unlimited" ? (
                  <div className="flex items-center gap-2">
                    <Switch
                      id={`ent-unlimited-${item.key}`}
                      checked={item.unlimited === true}
                      onCheckedChange={(checked) =>
                        updateItem(item.key, { unlimited: checked })
                      }
                    />
                    <Label htmlFor={`ent-unlimited-${item.key}`}>
                      Unlimited
                    </Label>
                  </div>
                ) : (
                  <div className="space-y-1">
                    <Label htmlFor={`ent-int-${item.key}`}>Limit value</Label>
                    <Input
                      id={`ent-int-${item.key}`}
                      type="number"
                      min={0}
                      step={1}
                      value={item.integerValue ?? 0}
                      onChange={(e) =>
                        updateItem(item.key, {
                          integerValue: Number(e.target.value),
                        })
                      }
                    />
                  </div>
                )}
              </motion.div>
            );
          })}
        </div>
      )}

      {availableToAdd.length > 0 ? (
        <div className="flex flex-wrap items-end gap-2 pt-2 border-t">
          <div className="space-y-1 min-w-[220px] flex-1">
            <Label htmlFor="add-entitlement">Add entitlement</Label>
            <Select value={addKey} onValueChange={setAddKey}>
              <SelectTrigger id="add-entitlement" className="w-full">
                <SelectValue placeholder="Choose from catalog…" />
              </SelectTrigger>
              <SelectContent>
                {availableToAdd.map((def) => (
                  <SelectItem key={def.key} value={def.key}>
                    {def.display_name} ({def.kind})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Button
            type="button"
            variant="outline"
            onClick={handleAdd}
            disabled={!addKey}
          >
            <Plus className="mr-1 h-4 w-4" />
            Add
          </Button>
        </div>
      ) : (
        <p className="text-xs text-muted-foreground">
          All active catalog entitlements are assigned to this version.
        </p>
      )}
    </div>
  );
}
