"use client";

import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { CatalogHelpTooltip } from "@/components/billing/catalog-help-tooltip";
import { formatEntitlementDisplayValue } from "@/lib/billing/format-entitlement-value";
import { entitlementHelpText } from "@/lib/billing/entitlement-catalog-help";
import {
  parseAssignedEntitlements,
  type AssignedPlanEntitlement,
} from "@/lib/billing/plan-version-entitlements";
import type {
  EntitlementDefinition,
  PlanVersionDetail,
} from "@/types/admin-plans";
import { motion, useReducedMotion } from "framer-motion";
import { ChevronDown, ChevronUp, GripVertical } from "lucide-react";

interface PlanVersionEntitlementDisplayProps {
  version: PlanVersionDetail;
  definitions: EntitlementDefinition[];
  onReorder?: (next: AssignedPlanEntitlement[]) => void;
  reordering?: boolean;
}

/**
 * Presentation of entitlements on a published or immutable plan version.
 * Entitlement values remain read-only, while an optional reorder callback enables
 * administrators to maintain the plan-card display sequence.
 */
export function PlanVersionEntitlementDisplay({
  version,
  definitions,
  onReorder,
  reordering = false,
}: PlanVersionEntitlementDisplayProps) {
  const parsedAssigned = React.useMemo(
    () => parseAssignedEntitlements(version),
    [version],
  );
  const [assigned, setAssigned] = React.useState(parsedAssigned);
  const [draggedKey, setDraggedKey] = React.useState<string | null>(null);
  const [lastDragOverKey, setLastDragOverKey] = React.useState<string | null>(
    null,
  );
  const dragStartOrder = React.useRef<string[]>([]);
  const dragCommitted = React.useRef(false);
  const defByKey = React.useMemo(
    () => new Map(definitions.map((d) => [d.key, d])),
    [definitions],
  );

  React.useEffect(() => {
    setAssigned(parsedAssigned);
  }, [parsedAssigned]);

  if (assigned.length === 0) {
    return (
      <p className="text-sm text-muted-foreground rounded-md border border-dashed p-4">
        No explicit entitlements on this version. Runtime uses catalog defaults
        for omitted keys.
      </p>
    );
  }

  const moveDraggedItemTo = (targetKey: string) => {
    if (
      !onReorder ||
      !draggedKey ||
      draggedKey === targetKey ||
      lastDragOverKey === targetKey
    ) {
      return null;
    }
    const fromIndex = assigned.findIndex((entry) => entry.key === draggedKey);
    const targetIndex = assigned.findIndex((entry) => entry.key === targetKey);
    if (fromIndex < 0 || targetIndex < 0) return null;
    const next = [...assigned];
    const [moved] = next.splice(fromIndex, 1);
    next.splice(targetIndex, 0, moved);
    setAssigned(next);
    setLastDragOverKey(targetKey);
    return next;
  };

  const hasOrderChanged = (next: AssignedPlanEntitlement[]) => {
    return next.some(
      (item, index) => item.key !== dragStartOrder.current[index],
    );
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Label className="text-sm font-medium">
          Entitlements on this version
        </Label>
        <CatalogHelpTooltip content="Values stored on this version. Keys not listed fall back to catalog defaults at runtime." />
      </div>
      {onReorder ? (
        <p className="text-xs text-muted-foreground">
          Entitlement values are immutable on published plans. Drag rows to
          change their display order on the plan card.
        </p>
      ) : null}
      <div
        className="space-y-2"
        role="list"
        aria-label="Entitlements in display order"
      >
        {assigned.map((item, index) => (
          <OrderedEntitlementRow
            key={item.key}
            item={item}
            index={index}
            total={assigned.length}
            definition={defByKey.get(item.key)}
            draggable={Boolean(onReorder)}
            dragging={draggedKey === item.key}
            reordering={reordering}
            onMove={(toIndex) => {
              if (!onReorder || toIndex < 0 || toIndex >= assigned.length)
                return;
              const next = [...assigned];
              const [moved] = next.splice(index, 1);
              next.splice(toIndex, 0, moved);
              setAssigned(next);
              onReorder(next);
            }}
            onDragStart={() => {
              setDraggedKey(item.key);
              setLastDragOverKey(null);
              dragStartOrder.current = assigned.map((entry) => entry.key);
              dragCommitted.current = false;
            }}
            onDragEnd={() => {
              if (!dragCommitted.current && dragStartOrder.current.length > 0) {
                const original = dragStartOrder.current
                  .map((key) => assigned.find((entry) => entry.key === key))
                  .filter(
                    (entry): entry is AssignedPlanEntitlement =>
                      entry !== undefined,
                  );
                setAssigned(original);
              }
              setDraggedKey(null);
              setLastDragOverKey(null);
              dragStartOrder.current = [];
            }}
            onDragOver={(event) => {
              event.preventDefault();
              moveDraggedItemTo(item.key);
            }}
            onDrop={() => {
              const next = moveDraggedItemTo(item.key) ?? assigned;
              if (hasOrderChanged(next)) {
                onReorder?.(next);
              }
              dragCommitted.current = true;
              setDraggedKey(null);
              setLastDragOverKey(null);
            }}
          />
        ))}
      </div>
    </div>
  );
}

function OrderedEntitlementRow({
  item,
  index,
  total,
  definition,
  draggable,
  dragging,
  reordering,
  onMove,
  onDragStart,
  onDragEnd,
  onDragOver,
  onDrop,
}: {
  item: AssignedPlanEntitlement;
  index: number;
  total: number;
  definition?: EntitlementDefinition;
  draggable: boolean;
  dragging: boolean;
  reordering: boolean;
  onMove: (toIndex: number) => void;
  onDragStart: () => void;
  onDragEnd: () => void;
  onDragOver: (event: React.DragEvent<HTMLDivElement>) => void;
  onDrop: () => void;
}) {
  const reducedMotion = useReducedMotion();

  return (
    <motion.div
      data-testid={`entitlement-item-${item.key}`}
      data-reorder-animated="true"
      draggable={draggable}
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
      onDragOver={onDragOver}
      onDrop={onDrop}
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
        scale: dragging ? 1.015 : 1,
        opacity: dragging ? 0.92 : 1,
      }}
      aria-grabbed={dragging}
      className={`relative flex min-w-0 flex-col gap-2 sm:flex-row sm:items-start ${
        dragging
          ? "z-10 rounded-lg border border-primary/50 bg-background shadow-xl ring-2 ring-primary/20"
          : ""
      }`}
    >
      <div className="flex min-w-0 flex-1 items-start gap-2">
        {draggable ? (
          <GripVertical
            className="mt-3 h-4 w-4 shrink-0 cursor-grab text-muted-foreground"
            aria-hidden="true"
          />
        ) : null}
        <div className="min-w-0 flex-1">
          <EntitlementReadOnlyRow item={item} definition={definition} />
        </div>
      </div>
      {draggable ? (
        <div className="flex w-full shrink-0 justify-end gap-1 sm:w-auto sm:pt-1">
          <Button
            type="button"
            size="icon"
            variant="ghost"
            aria-label={`Move ${definition?.display_name ?? item.key} up`}
            onClick={() => onMove(index - 1)}
            disabled={index === 0 || reordering}
          >
            <ChevronUp className="h-4 w-4" />
          </Button>
          <Button
            type="button"
            size="icon"
            variant="ghost"
            aria-label={`Move ${definition?.display_name ?? item.key} down`}
            onClick={() => onMove(index + 1)}
            disabled={index === total - 1 || reordering}
          >
            <ChevronDown className="h-4 w-4" />
          </Button>
        </div>
      ) : null}
    </motion.div>
  );
}

function EntitlementReadOnlyRow({
  item,
  definition,
}: {
  item: AssignedPlanEntitlement;
  definition?: EntitlementDefinition;
}) {
  const displayName = definition?.display_name ?? item.key;
  const valueType = definition?.value_type ?? "integer";

  return (
    <div className="min-w-0 space-y-1.5 rounded-lg border bg-muted/10 px-3 py-2.5">
      <div className="flex min-w-0 flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          <span className="max-w-full break-words text-sm font-medium sm:truncate">
            {displayName}
          </span>
          {definition ? (
            <>
              <Badge variant="outline">{definition.kind}</Badge>
              <Badge variant="secondary">{definition.value_type}</Badge>
            </>
          ) : null}
          <CatalogHelpTooltip content={entitlementHelpText(item.key)} />
        </div>
        <div className="max-w-full shrink-0 self-start sm:self-auto">
          <EntitlementValuePreview
            item={item}
            definition={definition}
            valueType={valueType}
          />
        </div>
      </div>
      <p className="break-all font-mono text-xs text-muted-foreground">
        {item.key}
      </p>
    </div>
  );
}

function EntitlementValuePreview({
  item,
  definition,
  valueType,
}: {
  item: AssignedPlanEntitlement;
  definition?: EntitlementDefinition;
  valueType: string;
}) {
  if (valueType === "boolean") {
    return (
      <div className="flex max-w-full flex-wrap items-center gap-2">
        <Switch checked={item.booleanValue === true} disabled aria-readonly />
        <span className="break-words text-sm text-muted-foreground">
          {item.booleanValue ? "Enabled" : "Disabled"}
        </span>
      </div>
    );
  }

  if (valueType === "unlimited" || item.unlimited) {
    return (
      <div className="flex max-w-full flex-wrap items-center gap-2">
        <Switch checked={item.unlimited === true} disabled aria-readonly />
        <span className="break-words text-sm font-medium">Unlimited</span>
      </div>
    );
  }

  return (
    <span className="max-w-full break-words text-sm font-semibold tabular-nums">
      {formatEntitlementDisplayValue(item, definition)}
    </span>
  );
}
