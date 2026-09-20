import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ToolConfigDrawer } from "@/components/tools/tool-config-drawer";

vi.mock("@/hooks/use-live-time", () => ({
  useLiveTime: () => 1_700_000_000_000,
  formatTimeUntilExpiry: () => null,
}));

const googleSheetsTool = {
  id: "tool-google-sheets-lead",
  name: "Google_Sheets_lead_capture",
  description: "Capture a confirmed service inquiry.",
  config_schema: {
    properties: {
      spreadsheet_id: {
        title: "Spreadsheet ID",
        description:
          "Required. Paste the full Google Sheets URL or spreadsheet ID.",
      },
      append_range: {
        title: "Append range",
        description: "Use Lead submissions!A:L.",
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
      screen.getByRole("button", { name: "Help for Append range" }),
    ).toBeTruthy();

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
});
