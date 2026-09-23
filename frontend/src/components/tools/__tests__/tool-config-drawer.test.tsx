import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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

    expect(
      screen.getByText(
        "Discover columns to verify this spreadsheet before saving.",
      ),
    ).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Discover columns" }));

    expect(await screen.findByText("Choose agent fields")).toBeTruthy();
    expect(
      await screen.findByText(
        "Setup verified. Save changes to apply this configuration.",
      ),
    ).toBeTruthy();
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

  it("keeps Save enabled while valid required and managed fields are configured", async () => {
    const user = userEvent.setup();
    const onDiscover = vi.fn().mockResolvedValue({
      status: "succeeded",
      provider: "google_sheets",
      sheets: [
        {
          title: "Orders",
          sheet_id: 7,
          headers: [
            "Submission ID",
            "Captured at",
            "Order source",
            "Status",
            "Customer name",
            "Phone",
          ],
          header_range: "Orders!A1:F1",
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
            config: { spreadsheet_id: "sheet-id-123456" },
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
    const requiredFields = await screen.findByRole("combobox", {
      name: "Required fields",
    });
    const saveButton = screen.getByRole("button", { name: "Save" });
    await waitFor(() => expect((saveButton as HTMLButtonElement).disabled).toBe(false));

    await user.click(requiredFields);
    await user.click(screen.getByRole("button", { name: "Select all" }));
    await user.keyboard("{Escape}");
    expect(requiredFields.textContent).toContain("All 6 columns selected");
    expect((saveButton as HTMLButtonElement).disabled).toBe(false);

    const managedSelections = [
      ["Duplicate check", "Submission ID"],
      ["Captured at", "Captured at"],
      ["Source", "Order source"],
      ["Status", "Status"],
    ] as const;
    for (const [label, header] of managedSelections) {
      const selector = screen.getByRole("combobox", { name: label });
      selector.focus();
      await user.keyboard("{Enter}");
      await user.keyboard(header);
      await user.keyboard("{Enter}");
      expect(selector.textContent).toContain(header);
      expect((saveButton as HTMLButtonElement).disabled).toBe(false);
    }

    await user.type(await screen.findByLabelText("Source value"), "Demo call");
    await user.type(await screen.findByLabelText("Initial status"), "New");
    expect((saveButton as HTMLButtonElement).disabled).toBe(false);

    await user.click(saveButton);
    await waitFor(() => {
      expect(onSaveConfig).toHaveBeenCalledWith(
        "agent-tool-1",
        expect.objectContaining({
          agent_columns: "Customer name, Phone",
          required_columns: "Customer name, Phone",
          idempotency_column: "Submission ID",
          timestamp_column: "Captured at",
          source_column: "Order source",
          source_value: "Demo call",
          status_column: "Status",
          status_value: "New",
        }),
      );
    });
  });

  it("restores saved column settings and revalidates them when reopened", async () => {
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
    const drawerProps = {
      open: true,
      onOpenChange: vi.fn(),
      tool: googleSheetsTool,
      agentTool: {
        id: "agent-tool-1",
        config: {
          spreadsheet_id: "sheet-id-123456",
          selected_sheet_id: "7",
          default_range: "Orders!A1:C1000",
          header_range: "Orders!A1:C1",
          agent_columns: "Customer, Items",
          required_columns: "Customer",
        },
        auth_status: AuthStatus.AUTHENTICATED,
        token_expires_at: null,
        is_enabled: true,
        unselected_functions: [],
      } as never,
      onSaveConfig: vi.fn(),
      onToggleFunction: vi.fn(),
      onToggleAllFunctions: vi.fn(),
      onOAuth: vi.fn(),
      onLogout: vi.fn(),
      onSetApiKey: vi.fn(),
      onDiscoverGoogleSheetHeaders: onDiscover,
      onDisconnect: vi.fn(),
      canEdit: true,
    };
    const { rerender } = render(<ToolConfigDrawer {...drawerProps} />);

    let agentFields = await screen.findByRole("combobox", {
      name: "Agent fields",
    });
    expect(agentFields.textContent).toContain("2 of 3 columns selected");
    expect(
      screen.getByRole("combobox", { name: "Required fields" }).textContent,
    ).toContain("1 of 2 columns selected");
    expect(
      await screen.findByText(
        "Configured: the selected fields match the current sheet.",
      ),
    ).toBeTruthy();

    rerender(<ToolConfigDrawer {...drawerProps} open={false} />);
    await waitFor(() => {
      expect(
        screen.queryByRole("combobox", { name: "Agent fields" }),
      ).toBeNull();
    });
    rerender(<ToolConfigDrawer {...drawerProps} open />);

    agentFields = await screen.findByRole("combobox", {
      name: "Agent fields",
    });
    expect(agentFields.textContent).toContain("2 of 3 columns selected");
    expect(onDiscover).toHaveBeenCalledTimes(2);
  });

  it("marks an empty agent-field selection incomplete and prevents saving", async () => {
    const user = userEvent.setup();
    const onDiscover = vi.fn().mockResolvedValue({
      status: "succeeded",
      provider: "google_sheets",
      sheets: [
        {
          title: "Orders",
          sheet_id: 7,
          headers: ["Customer", "Items"],
          header_range: "Orders!A1:B1",
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
    const agentFields = await screen.findByRole("combobox", {
      name: "Agent fields",
    });
    await user.click(agentFields);
    await user.click(screen.getByRole("button", { name: "Clear" }));

    expect(
      await screen.findByText("Select at least one Agent field."),
    ).toBeTruthy();
    const saveButton = screen.getByRole("button", { name: "Save" });
    expect(
      (saveButton as HTMLButtonElement).disabled,
    ).toBe(true);
    await user.hover(saveButton.parentElement as HTMLElement);
    expect((await screen.findByRole("tooltip")).textContent).toContain(
      "Select at least one Agent field.",
    );
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

    const agentFields = await screen.findByRole("combobox", {
      name: "Agent fields",
    });
    expect(onDiscover).toHaveBeenCalledWith("agent-tool-1", "sheet-id-123456");
    expect(agentFields.textContent).toContain("All 3 columns selected");
    expect(
      await screen.findByText(
        "Setup verified. Save changes to apply this configuration.",
      ),
    ).toBeTruthy();
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

  it("refreshes the available fields when the sheet headers change", async () => {
    const user = userEvent.setup();
    const onDiscover = vi
      .fn()
      .mockResolvedValueOnce({
        status: "succeeded",
        provider: "google_sheets",
        sheets: [
          {
            title: "Orders",
            sheet_id: 7,
            headers: ["Customer", "Phone", "Quantity"],
            header_range: "Orders!A1:C1",
            issues: [],
          },
        ],
      })
      .mockResolvedValueOnce({
        status: "succeeded",
        provider: "google_sheets",
        sheets: [
          {
            title: "Orders",
            sheet_id: 7,
            headers: ["Customer", "Special Instructions"],
            header_range: "Orders!A1:B1",
            issues: [],
          },
        ],
      })
      .mockRejectedValueOnce(new Error("Spreadsheet request failed."));
    const onSaveConfig = vi.fn().mockResolvedValue(undefined);

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
    let agentFields = await screen.findByRole("combobox", {
      name: "Agent fields",
    });
    expect(agentFields.textContent).toContain("All 3 columns selected");

    await user.click(screen.getByRole("button", { name: "Discover columns" }));
    agentFields = await screen.findByRole("combobox", {
      name: "Agent fields",
    });
    await waitFor(() => {
      expect(agentFields.textContent).toContain("All 2 columns selected");
    });

    await user.click(agentFields);
    expect(
      screen.queryByRole("option", { name: "Quantity" }),
    ).toBeNull();
    expect(
      screen.getByRole("option", { name: "Special Instructions" }),
    ).toBeTruthy();

    await user.keyboard("{Escape}");
    await user.click(screen.getByRole("button", { name: "Discover columns" }));
    expect(await screen.findByText("Spreadsheet request failed.")).toBeTruthy();
    expect(
      screen.queryByRole("combobox", { name: "Agent fields" }),
    ).toBeNull();

    await user.clear(
      screen.getByRole("textbox", { name: "Google Sheets URL or spreadsheet ID" }),
    );
    await user.type(
      screen.getByRole("textbox", { name: "Google Sheets URL or spreadsheet ID" }),
      "another-sheet-id-123456",
    );
    expect(
      screen.queryByRole("combobox", { name: "Agent fields" }),
    ).toBeNull();
    expect(
      screen.getByText(
        "Discover the current columns and select agent fields before saving this spreadsheet.",
      ),
    ).toBeTruthy();
    expect(
      (screen.getByRole("button", { name: "Save" }) as HTMLButtonElement)
        .disabled,
    ).toBe(true);
    expect(onSaveConfig).not.toHaveBeenCalled();
  });

  it("does not carry discovered columns over to another agent attachment", async () => {
    const user = userEvent.setup();
    const jordanHeaders = [
      "Submission ID",
      "Captured at",
      "Lead source",
      "Caller name",
      "Caller email",
      "Caller phone",
      "Service needed",
      "Issue summary",
      "Service address",
      "Urgency",
      "Preferred callback window",
      "Status",
    ];
    const sofiaHeaders = [
      "Submission ID",
      "Captured at",
      "Order source",
      "Caller Name",
      "Phone",
      "Email",
      "Order details",
      "Special Instructions",
    ];
    const onDiscover = vi
      .fn()
      .mockResolvedValueOnce({
        status: "succeeded",
        provider: "google_sheets",
        sheets: [
          {
            title: "Lead submissions",
            sheet_id: 7,
            headers: jordanHeaders,
            header_range: "'Lead submissions'!A1:L1",
            issues: [],
          },
        ],
      })
      .mockResolvedValueOnce({
        status: "succeeded",
        provider: "google_sheets",
        sheets: [
          {
            title: "Lead submissions",
            sheet_id: 7,
            headers: jordanHeaders,
            header_range: "'Lead submissions'!A1:L1",
            issues: [],
          },
          {
            title: "Restaurant Orders",
            sheet_id: 8,
            headers: sofiaHeaders,
            header_range: "'Restaurant Orders'!A1:H1",
            issues: [],
          },
        ],
      });
    const drawerProps = {
      open: true,
      onOpenChange: vi.fn(),
      tool: googleSheetsTool,
      onSaveConfig: vi.fn(),
      onToggleFunction: vi.fn(),
      onToggleAllFunctions: vi.fn(),
      onOAuth: vi.fn(),
      onLogout: vi.fn(),
      onSetApiKey: vi.fn(),
      onDiscoverGoogleSheetHeaders: onDiscover,
      onDisconnect: vi.fn(),
      canEdit: true,
    };
    const { rerender } = render(
      <ToolConfigDrawer
        {...drawerProps}
        agentTool={
          {
            id: "jordan-sheets-tool",
            config: {
              spreadsheet_id: "jordan-sheet-id-123456",
              selected_sheet_id: "7",
              default_range: "'Lead submissions'!A1:L1000",
            },
            auth_status: AuthStatus.AUTHENTICATED,
            token_expires_at: null,
            is_enabled: true,
            unselected_functions: [],
          } as never
        }
      />,
    );

    expect(
      await screen.findByText("All 12 columns selected"),
    ).toBeTruthy();

    rerender(
      <ToolConfigDrawer
        {...drawerProps}
        agentTool={
          {
            id: "sofia-sheets-tool",
            config: {
              spreadsheet_id: "sofia-sheet-id-123456",
              // An unverified default range must not silently select a tab.
              default_range: "'Lead submissions'!A1:L1000",
              // Legacy configurations also need to confirm their tab once.
              header_range: "'Lead submissions'!A1:L1",
              agent_columns:
                "Caller name, Caller email, Caller phone, Service needed, Issue summary",
            },
            auth_status: AuthStatus.AUTHENTICATED,
            token_expires_at: null,
            is_enabled: true,
            unselected_functions: [],
          } as never
        }
      />,
    );

    await waitFor(() => {
      expect(
        screen.queryByRole("combobox", { name: "Agent fields" }),
      ).toBeNull();
      expect(
        (
          screen.getByRole("textbox", {
            name: "Google Sheets URL or spreadsheet ID",
          }) as HTMLInputElement
        ).value,
      ).toBe("sofia-sheet-id-123456");
    });
    expect(
      await screen.findByText(/Choose the tab for this workflow/),
    ).toBeTruthy();
    expect(
      screen.getByText("Choose the data tab for this workflow."),
    ).toBeTruthy();
    const tabSelector = screen.getByRole("combobox", {
      name: "Spreadsheet tab",
    });
    tabSelector.focus();
    await user.keyboard("{Enter}");
    expect(
      screen.getByRole("option", { name: "Lead submissions (12 columns)" }),
    ).toBeTruthy();
    fireEvent.click(
      screen.getByRole("option", { name: "Restaurant Orders (8 columns)" }),
    );
    const agentFields = await screen.findByRole("combobox", {
      name: "Agent fields",
    });
    expect(agentFields.textContent).toContain("All 8 columns selected");
    expect(
      (screen.getByRole("button", { name: "Save" }) as HTMLButtonElement)
        .disabled,
    ).toBe(false);
    await user.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => {
      expect(drawerProps.onSaveConfig).toHaveBeenCalledWith(
        "sofia-sheets-tool",
        expect.objectContaining({ selected_sheet_id: "8" }),
      );
    });
    onDiscover.mockResolvedValue({
      status: "succeeded",
      provider: "google_sheets",
      sheets: [
        {
          title: "Lead submissions",
          sheet_id: 7,
          headers: jordanHeaders,
          header_range: "'Lead submissions'!A1:L1",
          issues: [],
        },
        {
          title: "Restaurant Orders",
          sheet_id: 8,
          headers: sofiaHeaders,
          header_range: "'Restaurant Orders'!A1:H1",
          issues: [],
        },
      ],
    });
    await user.click(screen.getByRole("button", { name: "Discover columns" }));
    expect(
      (await screen.findByRole("combobox", { name: "Agent fields" })).textContent,
    ).toContain("All 8 columns selected");
    expect(onDiscover).toHaveBeenLastCalledWith(
      "sofia-sheets-tool",
      "sofia-sheet-id-123456",
    );
  });
});
