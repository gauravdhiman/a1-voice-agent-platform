import { describe, expect, it } from "vitest";
import {
  buildEntitlementInputs,
  parseAssignedEntitlements,
} from "@/lib/billing/plan-version-entitlements";
import type {
  EntitlementDefinition,
  PlanVersionDetail,
} from "@/types/admin-plans";

const booleanDef: EntitlementDefinition = {
  key: "payg_enabled",
  kind: "feature",
  display_name: "Pay as you go",
  value_type: "boolean",
  unit: null,
  validation_schema: {},
  enforcement_handler: "feature.flag",
  default_enforcement: "hard",
  default_when_absent: { type: "boolean", value: false },
  is_active: true,
  description: null,
};

const integerDef: EntitlementDefinition = {
  key: "max_agents",
  kind: "limit",
  display_name: "Maximum agents",
  value_type: "integer",
  unit: "count",
  validation_schema: {},
  enforcement_handler: "limit.max_count",
  default_enforcement: "hard",
  default_when_absent: { type: "integer", value: 0 },
  is_active: true,
  description: null,
};

describe("plan-version-entitlements", () => {
  it("parseAssignedEntitlements maps version rows in display order", () => {
    const version = {
      entitlements: [
        {
          id: "1",
          entitlement_key: "payg_enabled",
          value: { type: "boolean", value: true },
          display_order: 1,
        },
        {
          id: "2",
          entitlement_key: "max_agents",
          value: { type: "integer", value: 3 },
          display_order: 0,
        },
      ],
    } as unknown as PlanVersionDetail;

    expect(parseAssignedEntitlements(version)).toEqual([
      { key: "max_agents", integerValue: 3 },
      { key: "payg_enabled", booleanValue: true },
    ]);
  });

  it("buildEntitlementInputs produces sparse API payload", () => {
    const payload = buildEntitlementInputs(
      [
        { key: "max_agents", integerValue: 2 },
        { key: "payg_enabled", booleanValue: false },
      ],
      [integerDef, booleanDef],
    );
    expect(payload).toEqual([
      {
        entitlement_key: "max_agents",
        value: { type: "integer", value: 2 },
        display_order: 0,
      },
      {
        entitlement_key: "payg_enabled",
        value: { type: "boolean", value: false },
        display_order: 1,
      },
    ]);
  });

  it("buildEntitlementInputs rejects negative integers", () => {
    expect(() =>
      buildEntitlementInputs([{ key: "max_agents", integerValue: -1 }], [
        integerDef,
      ]),
    ).toThrow(/non-negative integer/);
  });
});
