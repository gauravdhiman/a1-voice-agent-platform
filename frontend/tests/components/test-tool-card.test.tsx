/**
 * Tests for ToolCard's `isUnpublished` visual treatment (RFC §6.6).
 *
 * A connected-but-unpublished tool keeps working at runtime (worker joins
 * `agent_tools` without an `is_published` filter) but is no longer in the
 * catalog. The card surfaces this with an amber "Unpublished" pill (like the
 * MCP badge) + an inline amber note so the org admin knows it's mapped but
 * unavailable to new agents.
 */
import { describe, it, expect } from "vitest";
import { renderWithProviders as render, screen } from "../utils/test-utils";
import { ToolCard } from "@/components/tools/tool-card";
import { AuthStatus, ConnectionStatus } from "@/types/agent";

const baseTool = {
  id: "tool-1",
  name: "ghost_tool",
  description: "a tool",
  tool_source: "mcp" as const,
};

describe("ToolCard isUnpublished", () => {
  it("renders an Unpublished pill + note when isUnpublished is true", () => {
    render(
      <ToolCard
        tool={baseTool}
        authStatus={AuthStatus.NOT_AUTHENTICATED}
        tokenExpiresAt={null}
        connectionStatus={ConnectionStatus.CONNECTED_NO_AUTH}
        isConfigured
        isUnpublished
        onClick={() => {}}
      />,
    );
    expect(screen.getByText(/Unpublished/i)).toBeInTheDocument();
    expect(
      screen.getByText(/No longer in the catalog/i),
    ).toBeInTheDocument();
  });

  it("does not render the Unpublished pill or note by default", () => {
    render(
      <ToolCard
        tool={baseTool}
        authStatus={AuthStatus.NOT_AUTHENTICATED}
        tokenExpiresAt={null}
        connectionStatus={ConnectionStatus.CONNECTED_NO_AUTH}
        isConfigured
        onClick={() => {}}
      />,
    );
    expect(screen.queryByText(/Unpublished/i)).not.toBeInTheDocument();
    expect(
      screen.queryByText(/No longer in the catalog/i),
    ).not.toBeInTheDocument();
  });

  it("still shows the MCP pill alongside the Unpublished pill for an unpublished MCP tool", () => {
    render(
      <ToolCard
        tool={baseTool}
        authStatus={AuthStatus.NOT_AUTHENTICATED}
        tokenExpiresAt={null}
        connectionStatus={ConnectionStatus.CONNECTED_NO_AUTH}
        isConfigured
        isUnpublished
        onClick={() => {}}
      />,
    );
    expect(screen.getByText("MCP")).toBeInTheDocument();
    expect(screen.getByText(/Unpublished/i)).toBeInTheDocument();
  });
});