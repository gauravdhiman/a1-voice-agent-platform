import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PlanVersionEntitlementEditor } from "../plan-version-entitlement-editor";
import { PlanVersionEntitlementDisplay } from "../plan-version-entitlement-display";
import type { EntitlementDefinition } from "@/types/admin-plans";

const definitions: EntitlementDefinition[] = [
  {
    key: "max_agents",
    kind: "limit",
    display_name: "Maximum agents",
    value_type: "integer",
    unit: "count",
    validation_schema: {},
    enforcement_handler: "limit.max_count",
    default_when_absent: { type: "integer", value: 0 },
    is_active: true,
    description: "Maximum number of agents.",
  },
  {
    key: "payg_enabled",
    kind: "feature",
    display_name: "Pay as you go",
    value_type: "boolean",
    unit: null,
    validation_schema: {},
    enforcement_handler: "feature.flag",
    default_when_absent: { type: "boolean", value: false },
    is_active: true,
    description: "Allows pay-as-you-go usage.",
  },
];

describe("PlanVersionEntitlementEditor ordering", () => {
  it("reorders entitlement blocks with the keyboard controls", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();

    render(
      <PlanVersionEntitlementEditor
        definitions={definitions}
        assigned={[
          { key: "max_agents", integerValue: 5 },
          { key: "payg_enabled", booleanValue: true },
        ]}
        onChange={onChange}
      />,
    );

    await user.click(
      screen.getByRole("button", { name: "Move Pay as you go up" }),
    );

    expect(onChange).toHaveBeenCalledWith([
      { key: "payg_enabled", booleanValue: true },
      { key: "max_agents", integerValue: 5 },
    ]);
  });

  it("marks entitlement blocks as draggable", () => {
    render(
      <PlanVersionEntitlementEditor
        definitions={definitions}
        assigned={[{ key: "max_agents", integerValue: 5 }]}
        onChange={() => undefined}
      />,
    );

    expect(screen.getByTestId("entitlement-item-max_agents")).toHaveAttribute(
      "draggable",
      "true",
    );
  });

  it("reorders blocks through a drag-and-drop gesture", () => {
    const onChange = vi.fn();

    render(
      <PlanVersionEntitlementEditor
        definitions={definitions}
        assigned={[
          { key: "max_agents", integerValue: 5 },
          { key: "payg_enabled", booleanValue: true },
        ]}
        onChange={onChange}
      />,
    );

    fireEvent.dragStart(screen.getByTestId("entitlement-item-max_agents"));
    fireEvent.drop(screen.getByTestId("entitlement-item-payg_enabled"));

    expect(onChange).toHaveBeenCalledWith([
      { key: "payg_enabled", booleanValue: true },
      { key: "max_agents", integerValue: 5 },
    ]);
  });

  it("moves the dragged block when it crosses a drop target", () => {
    const onChange = vi.fn();

    render(
      <PlanVersionEntitlementEditor
        definitions={definitions}
        assigned={[
          { key: "max_agents", integerValue: 5 },
          { key: "payg_enabled", booleanValue: true },
        ]}
        onChange={onChange}
      />,
    );

    fireEvent.dragStart(screen.getByTestId("entitlement-item-payg_enabled"));
    fireEvent.dragOver(screen.getByTestId("entitlement-item-max_agents"));

    expect(onChange).toHaveBeenCalledWith([
      { key: "payg_enabled", booleanValue: true },
      { key: "max_agents", integerValue: 5 },
    ]);
  });

  it("offers the same order controls for an immutable published version", async () => {
    const user = userEvent.setup();
    const onReorder = vi.fn();

    render(
      <PlanVersionEntitlementDisplay
        version={
          {
            entitlements: [
              {
                id: "1",
                entitlement_key: "max_agents",
                value: { type: "integer", value: 5 },
                display_order: 0,
              },
              {
                id: "2",
                entitlement_key: "payg_enabled",
                value: { type: "boolean", value: true },
                display_order: 1,
              },
            ],
          } as never
        }
        definitions={definitions}
        onReorder={onReorder}
      />,
    );

    await user.click(
      screen.getByRole("button", { name: "Move Pay as you go up" }),
    );

    expect(onReorder).toHaveBeenCalledWith([
      { key: "payg_enabled", booleanValue: true },
      { key: "max_agents", integerValue: 5 },
    ]);
  });

  it("reorders an immutable version while dragging across a target", () => {
    const onReorder = vi.fn();

    render(
      <PlanVersionEntitlementDisplay
        version={
          {
            entitlements: [
              {
                id: "1",
                entitlement_key: "max_agents",
                value: { type: "integer", value: 5 },
                display_order: 0,
              },
              {
                id: "2",
                entitlement_key: "payg_enabled",
                value: { type: "boolean", value: true },
                display_order: 1,
              },
            ],
          } as never
        }
        definitions={definitions}
        onReorder={onReorder}
      />,
    );

    fireEvent.dragStart(screen.getByTestId("entitlement-item-payg_enabled"));
    fireEvent.dragOver(screen.getByTestId("entitlement-item-max_agents"));
    fireEvent.drop(screen.getByTestId("entitlement-item-max_agents"));

    expect(onReorder).toHaveBeenCalledWith([
      { key: "payg_enabled", booleanValue: true },
      { key: "max_agents", integerValue: 5 },
    ]);
  });
});
