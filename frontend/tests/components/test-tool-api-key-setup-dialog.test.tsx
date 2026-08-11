/**
 * Tests the pre-connection API-key gate for MCP tools that have no platform
 * credential fallback.
 */
import { describe, expect, it, vi } from "vitest";
import {
  renderWithProviders as render,
  screen,
  userEvent,
} from "../utils/test-utils";
import { ToolApiKeySetupDialog } from "@/components/tools/tool-api-key-setup-dialog";

describe("ToolApiKeySetupDialog", () => {
  it("requires an organization key before enabling the connect action", async () => {
    const user = userEvent.setup();
    const onConnect = vi.fn(async () => undefined);

    render(
      <ToolApiKeySetupDialog
        open
        onOpenChange={vi.fn()}
        toolName="weather_mcp"
        onConnect={onConnect}
      />,
    );

    const connectButton = screen.getByRole("button", {
      name: "Connect MCP tool",
    });
    expect(connectButton).toBeDisabled();

    await user.type(screen.getByLabelText("Organization API key"), " org-key ");
    expect(connectButton).toBeEnabled();
    await user.click(connectButton);

    expect(onConnect).toHaveBeenCalledWith("org-key");
  });
});
