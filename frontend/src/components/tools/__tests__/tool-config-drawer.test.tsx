import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ToolConfigDrawer } from "@/components/tools/tool-config-drawer";
import { AuthStatus } from "@/types/agent";

vi.mock("@/hooks/use-live-time", () => ({
  useLiveTime: () => 1_700_000_000_000,
  formatTimeUntilExpiry: () => null,
}));

Element.prototype.scrollIntoView = () => {};

const googleSheetsTool = {
  id: "tool-google-sheets",
  name: "Google_Sheets",
  description: "Manage rows in one configured Google Sheet.",
  config_schema: {
    properties: {
      spreadsheet_id: {
        title: "Spreadsheet ID",
        description:
          "Required. Paste the full Google Sheets URL or spreadsheet ID.",
      },
      default_range: {
        title: "Working area",
        description: "Use Lead submissions!A1:L1000.",
      },
      agent_columns: {
        title: "Agent fields",
        description: "Use Customer name, Items, and Quantity.",
      },
    },
  },
  tool_functions_schema: { functions: [] },
  auth_type: "oauth2",
  requires_auth: true,
} as never;

describe("ToolConfigDrawer", () => {
  it("keeps configuration guidance available in field tooltips", async () => {
    const user = userEvent.setup();

    render(
      <ToolConfigDrawer
        open
        onOpenChange={vi.fn()}
        tool={googleSheetsTool}
        agentTool={null}
        onSaveConfig={vi.fn()}
        onToggleFunction={vi.fn()}
        onToggleAllFunctions={vi.fn()}
        onOAuth={vi.fn()}
        onLogout={vi.fn()}
        onSetApiKey={vi.fn()}
        onDisconnect={vi.fn()}
        canEdit
      />,
    );

    const helpButton = screen.getByRole("button", {
      name: "Help for Spreadsheet ID",
    });
    expect(helpButton).toBeTruthy();
    expect(
      screen.getByRole("button", { name: "Help for Working area" }),
    ).toBeTruthy();
    expect(
      screen.getByRole("button", { name: "Help for Agent fields" }),
    ).toBeTruthy();
    expect(screen.getAllByText("Required", { exact: true })).toHaveLength(1);
    expect(screen.getAllByText("Optional", { exact: true })).toHaveLength(2);

    await user.hover(helpButton);

    const tooltip = await screen.findByRole("tooltip", { hidden: true });
    expect(tooltip.textContent).toContain(
      "Required. Paste the full Google Sheets URL or spreadsheet ID.",
    );
  });

  it("uses the theme foreground token for enabled function names", () => {
    const functionTool = {
      ...(googleSheetsTool as unknown as Record<string, unknown>),
      tool_functions_schema: {
        functions: [
          {
            name: "send_email",
            description: "Send an email.",
            parameters: { properties: {}, required: [] },
          },
        ],
      },
    } as never;

    render(
      <ToolConfigDrawer
        open
        onOpenChange={vi.fn()}
        tool={functionTool}
        agentTool={{ is_enabled: true, unselected_functions: [] } as never}
        onSaveConfig={vi.fn()}
        onToggleFunction={vi.fn()}
        onToggleAllFunctions={vi.fn()}
        onOAuth={vi.fn()}
        onLogout={vi.fn()}
        onSetApiKey={vi.fn()}
        onDisconnect={vi.fn()}
        canEdit
      />,
    );

    const functionName = screen.getByText("send_email");
    expect(functionName.className).toContain("text-primary-foreground");
    expect(functionName.className).not.toContain("text-white");
  });

  it("discovers headers and turns them into selectable agent fields", async () => {
    const user = userEvent.setup();
    const onDiscover = vi.fn().mockResolvedValue({
      status: "succeeded",
      provider: "google_sheets",
      sheets: [
        {
          title: "Orders",
          sheet_id: 7,
          headers: ["Customer", "Items", "Quantity"],
          header_range: "Orders!A1:C1",
          issues: [],
        },
      ],
    });

    render(
      <ToolConfigDrawer
        open
        onOpenChange={vi.fn()}
        tool={googleSheetsTool}
        agentTool={
          {
            id: "agent-tool-1",
            config: { spreadsheet_id: "sheet-id-123456" },
            auth_status: AuthStatus.AUTHENTICATED,
            token_expires_at: null,
            is_enabled: true,
            unselected_functions: [],
          } as never
        }
        onSaveConfig={vi.fn()}
        onToggleFunction={vi.fn()}
        onToggleAllFunctions={vi.fn()}
        onOAuth={vi.fn()}
        onLogout={vi.fn()}
        onSetApiKey={vi.fn()}
        onDiscoverGoogleSheetHeaders={onDiscover}
        onDisconnect={vi.fn()}
        canEdit
      />,
    );

    await user.click(screen.getByRole("button", { name: "Discover columns" }));

    expect(await screen.findByText("Choose agent fields")).toBeTruthy();
    expect(onDiscover).toHaveBeenCalledWith("agent-tool-1", "sheet-id-123456");
    expect(screen.getAllByText("Required", { exact: true }).length).toBe(3);
    expect(screen.getAllByText("Optional", { exact: true }).length).toBe(2);
    expect(
      screen.getByRole("button", { name: "Help for Agent fields" }),
    ).toBeTruthy();
    expect(
      screen.getByRole("button", { name: "Help for Required fields" }),
    ).toBeTruthy();
    expect(
      screen.getByRole("button", { name: "Help for Managed columns" }),
    ).toBeTruthy();

    const agentFields = screen.getByRole("combobox", { name: "Agent fields" });
    expect(agentFields.textContent).toContain("All 3 columns selected");
    await user.click(agentFields);
    await user.click(await screen.findByRole("option", { name: "Customer" }));
    expect(agentFields.textContent).toContain("2 of 3 columns selected");

    const requiredFields = screen.getByRole("combobox", {
      name: "Required fields",
    });
    await user.click(requiredFields);
    await user.click(await screen.findByRole("option", { name: "Items" }));
    expect(requiredFields.textContent).toContain("1 of 2 columns selected");
  });

  it("reconciles stale business and managed mappings when discovering headers", async () => {
    const user = userEvent.setup();
    const onDiscover = vi.fn().mockResolvedValue({
      status: "succeeded",
      provider: "google_sheets",
      sheets: [
        {
          title: "Restaurant Orders",
          sheet_id: 42,
          headers: [
            "Submission ID",
            "Captured at",
            "Customer Name",
            "Phone",
            "Items",
          ],
          header_range: "'Restaurant Orders'!A1:E1",
          issues: [],
        },
      ],
    });
    const onSaveConfig = vi.fn().mockResolvedValue(undefined);

    render(
      <ToolConfigDrawer
        open
        onOpenChange={vi.fn()}
        tool={googleSheetsTool}
        agentTool={
          {
            id: "agent-tool-1",
            config: {
              spreadsheet_id: "sheet-id-123456",
              agent_columns: "Customer Name, Quantity",
              required_columns: "Customer Name, Quantity",
              idempotency_column: "Submission ID",
              timestamp_column: "Captured at",
              source_column: "Old Source",
              source_value: "old source",
            },
            auth_status: AuthStatus.AUTHENTICATED,
            token_expires_at: null,
            is_enabled: true,
            unselected_functions: [],
          } as never
        }
        onSaveConfig={onSaveConfig}
        onToggleFunction={vi.fn()}
        onToggleAllFunctions={vi.fn()}
        onOAuth={vi.fn()}
        onLogout={vi.fn()}
        onSetApiKey={vi.fn()}
        onDiscoverGoogleSheetHeaders={onDiscover}
        onDisconnect={vi.fn()}
        canEdit
      />,
    );

    await user.click(screen.getByRole("button", { name: "Discover columns" }));

    const agentFields = await screen.findByRole("combobox", {
      name: "Agent fields",
    });
    expect(agentFields.textContent).toContain("All 3 columns selected");
    await user.click(screen.getByRole("button", { name: "Save" }));

    const savedConfig = onSaveConfig.mock.calls[0]?.[1] as Record<
      string,
      string
    >;
    expect(savedConfig.agent_columns).toBe("Customer Name, Phone, Items");
    expect(savedConfig.required_columns).toBe("Customer Name");
    expect(savedConfig.idempotency_column).toBe("Submission ID");
    expect(savedConfig.timestamp_column).toBe("Captured at");
    expect(savedConfig.source_column).toBe("");
    expect(savedConfig.source_value).toBe("");
  });
});
