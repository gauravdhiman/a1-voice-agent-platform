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
    expect(screen.getByText(/No longer in the catalog/i)).toBeInTheDocument();
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

describe("ToolCard organization API key gate", () => {
  it("shows the API key requirement before an MCP tool can be connected", () => {
    render(
      <ToolCard
        tool={baseTool}
        authStatus={AuthStatus.NOT_AUTHENTICATED}
        tokenExpiresAt={null}
        connectionStatus={ConnectionStatus.NOT_CONNECTED}
        requiresApiKey
        onClick={() => {}}
      />,
    );

    expect(
      screen.getByText("API key required before connecting"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Configure API Key" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Connect" }),
    ).not.toBeInTheDocument();
  });
});

describe("ToolCard MCP catalog state", () => {
  it("lets org admins expand long tool descriptions", async () => {
    const { userEvent } = await import("@testing-library/user-event");
    const user = userEvent.setup();
    const longDescription =
      "Connects the agent to the remote workspace and exposes the functions needed to search, inspect, and update records for this organization. ".repeat(
        2,
      );

    render(
      <ToolCard
        tool={{ ...baseTool, description: longDescription }}
        authStatus={AuthStatus.NOT_AUTHENTICATED}
        tokenExpiresAt={null}
        connectionStatus={ConnectionStatus.NOT_CONNECTED}
        onClick={() => {}}
      />,
    );

    const showDescription = screen.getByRole("button", {
      name: /show full description/i,
    });
    expect(showDescription).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByText(longDescription)).not.toBeInTheDocument();

    await user.click(showDescription);

    expect(showDescription).toHaveAttribute("aria-expanded", "true");
    const description = document.getElementById(
      showDescription.getAttribute("aria-controls") || "",
    );
    expect(description).toHaveTextContent(longDescription.trim());
  });

  it("shows when an MCP function catalog is still pending discovery", () => {
    render(
      <ToolCard
        tool={baseTool}
        authStatus={AuthStatus.NOT_AUTHENTICATED}
        tokenExpiresAt={null}
        connectionStatus={ConnectionStatus.NOT_CONNECTED}
        onClick={() => {}}
      />,
    );

    expect(
      screen.getByText(/Function catalog pending admin discovery/i),
    ).toBeInTheDocument();
  });

  it("shows the exposed function count when an MCP catalog is available", () => {
    render(
      <ToolCard
        tool={{
          ...baseTool,
          tool_functions_schema: {
            functions: [
              {
                type: "function",
                name: "read_wiki",
                description: "Read wiki content",
              },
            ],
          },
        }}
        authStatus={AuthStatus.NOT_AUTHENTICATED}
        tokenExpiresAt={null}
        connectionStatus={ConnectionStatus.NOT_CONNECTED}
        onClick={() => {}}
      />,
    );

    expect(screen.getByText(/1 exposed function/i)).toBeInTheDocument();
  });
});
