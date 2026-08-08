"use client";

import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { CatalogHelpTooltip } from "@/components/billing/catalog-help-tooltip";
import { formatEntitlementDisplayValue } from "@/lib/billing/format-entitlement-value";
import { entitlementHelpText } from "@/lib/billing/entitlement-catalog-help";
import {
  parseAssignedEntitlements,
  type AssignedPlanEntitlement,
} from "@/lib/billing/plan-version-entitlements";
import type { EntitlementDefinition, PlanVersionDetail } from "@/types/admin-plans";

interface PlanVersionEntitlementDisplayProps {
  version: PlanVersionDetail;
  definitions: EntitlementDefinition[];
}

/**
 * Read-only presentation of entitlements on a published or immutable plan version.
 */
export function PlanVersionEntitlementDisplay({
  version,
  definitions,
}: PlanVersionEntitlementDisplayProps) {
  const assigned = parseAssignedEntitlements(version);
  const defByKey = React.useMemo(
    () => new Map(definitions.map((d) => [d.key, d])),
    [definitions],
  );

  if (assigned.length === 0) {
    return (
      <p className="text-sm text-muted-foreground rounded-md border border-dashed p-4">
        No explicit entitlements on this version. Runtime uses catalog defaults for
        omitted keys.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Label className="text-sm font-medium">Entitlements on this version</Label>
        <CatalogHelpTooltip content="Values stored on this version. Keys not listed fall back to catalog defaults at runtime." />
      </div>
      <div className="space-y-2">
        {assigned.map((item) => (
          <EntitlementReadOnlyRow
            key={item.key}
            item={item}
            definition={defByKey.get(item.key)}
          />
        ))}
      </div>
    </div>
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
    <div className="rounded-lg border bg-muted/10 px-3 py-2.5 space-y-1.5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2 min-w-0">
          <span className="font-medium text-sm truncate">{displayName}</span>
          {definition ? (
            <>
              <Badge variant="outline">{definition.kind}</Badge>
              <Badge variant="secondary">{definition.value_type}</Badge>
            </>
          ) : null}
          <CatalogHelpTooltip content={entitlementHelpText(item.key)} />
        </div>
        <EntitlementValuePreview
          item={item}
          definition={definition}
          valueType={valueType}
        />
      </div>
      <p className="text-xs text-muted-foreground font-mono">{item.key}</p>
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
      <div className="flex items-center gap-2 shrink-0">
        <Switch checked={item.booleanValue === true} disabled aria-readonly />
        <span className="text-sm text-muted-foreground">
          {item.booleanValue ? "Enabled" : "Disabled"}
        </span>
      </div>
    );
  }

  if (valueType === "unlimited" || item.unlimited) {
    return (
      <div className="flex items-center gap-2 shrink-0">
        <Switch checked={item.unlimited === true} disabled aria-readonly />
        <span className="text-sm font-medium">Unlimited</span>
      </div>
    );
  }

  return (
    <span className="text-sm font-semibold tabular-nums shrink-0">
      {formatEntitlementDisplayValue(item, definition)}
    </span>
  );
}
