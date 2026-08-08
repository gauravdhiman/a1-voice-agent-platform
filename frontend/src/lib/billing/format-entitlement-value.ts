import type { AssignedPlanEntitlement } from "@/lib/billing/plan-version-entitlements";
import type { EntitlementDefinition } from "@/types/admin-plans";

/**
 * Human-readable label for an assigned entitlement value in read-only views.
 */
export function formatEntitlementDisplayValue(
  item: AssignedPlanEntitlement,
  definition?: EntitlementDefinition,
): string {
  if (item.booleanValue !== undefined) {
    return item.booleanValue ? "Enabled" : "Disabled";
  }
  if (item.unlimited) {
    return "Unlimited";
  }
  if (item.integerValue !== undefined) {
    const unit = definition?.unit ? ` ${definition.unit}` : "";
    return `${item.integerValue}${unit}`;
  }
  return "Not set";
}
