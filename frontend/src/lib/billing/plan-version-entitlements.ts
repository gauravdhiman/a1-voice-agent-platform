import type {
  EntitlementDefinition,
  PlanVersionDetail,
  PlanVersionEntitlementInput,
} from "@/types/admin-plans";

/** Entitlement explicitly assigned on a draft plan version. */
export interface AssignedPlanEntitlement {
  key: string;
  booleanValue?: boolean;
  integerValue?: number;
  unlimited?: boolean;
}

/**
 * Parse sparse entitlement rows from a plan version into editor state.
 */
export function parseAssignedEntitlements(
  version: PlanVersionDetail,
): AssignedPlanEntitlement[] {
  return version.entitlements
    .map((ent, index) => ({ ent, index }))
    .sort(
      (left, right) =>
        (left.ent.display_order ?? left.index) -
        (right.ent.display_order ?? right.index),
    )
    .map(({ ent }) => {
    const value = ent.value;
    if (value?.type === "boolean") {
      return { key: ent.entitlement_key, booleanValue: Boolean(value.value) };
    }
    if (value?.type === "unlimited") {
      return { key: ent.entitlement_key, unlimited: true };
    }
    return {
      key: ent.entitlement_key,
      integerValue: Number(value?.value ?? 0),
    };
    });
}

/**
 * Build API payload from assigned entitlements and catalog definitions.
 */
export function buildEntitlementInputs(
  assigned: AssignedPlanEntitlement[],
  definitions: EntitlementDefinition[],
): PlanVersionEntitlementInput[] {
  const defByKey = new Map(definitions.map((d) => [d.key, d]));

  return assigned.map((item, displayOrder) => {
    const def = defByKey.get(item.key);
    if (!def) {
      throw new Error(`Unknown entitlement key: ${item.key}`);
    }
    if (def.value_type === "boolean") {
      return {
        entitlement_key: item.key,
        value: { type: "boolean", value: item.booleanValue === true },
        display_order: displayOrder,
      };
    }
    if (item.unlimited || def.value_type === "unlimited") {
      return {
        entitlement_key: item.key,
        value: { type: "unlimited" },
        display_order: displayOrder,
      };
    }
    const intValue = item.integerValue ?? 0;
    if (!Number.isInteger(intValue) || intValue < 0) {
      throw new Error(`${item.key} requires a non-negative integer`);
    }
    return {
      entitlement_key: item.key,
      value: { type: "integer", value: intValue },
      display_order: displayOrder,
    };
  });
}

/**
 * Default integer value when adding a limit entitlement to a draft.
 */
export function defaultIntegerForDefinition(def: EntitlementDefinition): number {
  const absent = def.default_when_absent as { value?: number } | null | undefined;
  if (typeof absent?.value === "number") {
    return absent.value;
  }
  return 0;
}
