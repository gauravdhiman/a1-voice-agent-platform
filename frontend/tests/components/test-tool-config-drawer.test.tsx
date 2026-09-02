/**
 * Tests for agent-level MCP credential affordances in ToolConfigDrawer.
 *
 * A literal platform-owned header is usable without an org credential, while
 * a templated API-key integration must expose the org key configuration flow.
 */
import { describe, expect, it, vi } from "vitest";
import { renderWithProviders as render, screen } from "../utils/test-utils";
import { ToolConfigDrawer } from "@/components/tools/tool-config-drawer";
import {
  AuthStatus,
  ConnectionStatus,
  type AgentTool,
  type PlatformTool,
} from "@/types/agent";

const makeTool = (requiresAuth: boolean): PlatformTool => ({
  id: "tool-1",
  name: "weather_mcp",
  description: "Weather MCP",
  config_schema: null,
  tool_functions_schema: null,
  is_active: true,
  is_published: true,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  auth_type: "api_key",
  requires_auth: requiresAuth,
  auth_config: null,
  tool_source: "mcp",
});

const agentTool: AgentTool = {
  id: "agent-tool-1",
  agent_id: "agent-1",
  tool_id: "tool-1",
  config: null,
  sensitive_config: null,
  unselected_functions: null,
  is_enabled: true,
  auth_status: AuthStatus.NOT_AUTHENTICATED,
  token_expires_at: null,
  connection_status: ConnectionStatus.CONNECTED_NO_AUTH,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

const drawerProps = {
  open: true,
  onOpenChange: vi.fn(),
  onSaveConfig: vi.fn(async () => undefined),
  onToggleFunction: vi.fn(async () => undefined),
  onToggleAllFunctions: vi.fn(async () => undefined),
  onOAuth: vi.fn(async () => undefined),
  onLogout: vi.fn(async () => undefined),
  onSetApiKey: vi.fn(async () => undefined),
  onDisconnect: vi.fn(),
  canEdit: true,
};

describe("ToolConfigDrawer MCP credentials", () => {
  it("offers an org key that overrides the platform fallback", () => {
    render(
      <ToolConfigDrawer
        {...drawerProps}
        tool={makeTool(false)}
        agentTool={{ ...agentTool, tool: makeTool(false) }}
      />,
    );

    expect(
      screen.getByText("Organization API Key (optional)"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Configure API Key/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/overrides the platform fallback/i),
    ).toBeInTheDocument();
  });

  it("prompts for an org API key when the platform requires one", () => {
    render(
      <ToolConfigDrawer
        {...drawerProps}
        tool={makeTool(true)}
        agentTool={{ ...agentTool, tool: makeTool(true) }}
      />,
    );

    expect(
      screen.getByText("Organization API Key Required"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Configure API Key/i }),
    ).toBeInTheDocument();
  });

  it("explains that an MCP catalog must be discovered before functions can be configured", () => {
    render(
      <ToolConfigDrawer
        {...drawerProps}
        tool={{ ...makeTool(true), auth_type: "oauth2" }}
        agentTool={{
          ...agentTool,
          tool: { ...makeTool(true), auth_type: "oauth2" },
        }}
      />,
    );

    expect(screen.getByText(/Tool catalog unavailable/i)).toBeInTheDocument();
    expect(screen.getByText(/complete OAuth discovery/i)).toBeInTheDocument();
  });

  it("progressively discloses org function details while keeping the switch visible", async () => {
    const { userEvent } = await import("@testing-library/user-event");
    const user = userEvent.setup();
    const tool = {
      ...makeTool(true),
      auth_type: "oauth2",
      tool_functions_schema: {
        functions: [
          {
            type: "function",
            name: "list_pages",
            description: "List pages from the workspace",
            parameters: {
              type: "object",
              properties: {
                query: {
                  type: "string",
                  description: "Optional search text",
                },
              },
              required: ["query"],
            },
          },
        ],
      },
    };

    render(
      <ToolConfigDrawer
        {...drawerProps}
        tool={tool}
        agentTool={{ ...agentTool, tool }}
      />,
    );

    const functionToggle = screen.getByRole("button", {
      name: /list_pages/i,
    });
    expect(functionToggle).toHaveAttribute("aria-expanded", "false");
    expect(
      screen.getByRole("switch", { name: /list_pages/i }),
    ).toBeInTheDocument();
    expect(screen.queryByText("Optional search text")).not.toBeInTheDocument();

    await user.click(functionToggle);

    expect(functionToggle).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("Optional search text")).toBeInTheDocument();
    expect(screen.getByText("query")).toBeInTheDocument();
    expect(screen.getByText("required", { exact: true })).toBeInTheDocument();
  });

  it("selects or deselects the complete function catalog in one update", async () => {
    const { userEvent } = await import("@testing-library/user-event");
    const user = userEvent.setup();
    const onToggleAllFunctions = vi.fn(async () => undefined);
    const tool = {
      ...makeTool(true),
      tool_functions_schema: {
        functions: [
          {
            type: "function",
            name: "list_pages",
            description: "List pages from the workspace",
            parameters: { type: "object", properties: {} },
          },
          {
            type: "function",
            name: "archive_page",
            description: "Archive a page in the workspace",
            parameters: { type: "object", properties: {} },
          },
        ],
      },
    };

    const view = render(
      <ToolConfigDrawer
        {...drawerProps}
        onToggleAllFunctions={onToggleAllFunctions}
        tool={tool}
        agentTool={{
          ...agentTool,
          unselected_functions: ["archive_page"],
          tool,
        }}
      />,
    );

    expect(screen.getByText("1 / 2")).toBeInTheDocument();
    await user.type(
      screen.getByRole("searchbox", { name: /search functions/i }),
      "list",
    );
    expect(screen.queryByText("archive_page")).not.toBeInTheDocument();

    const allFunctionsSwitch = screen.getByRole("switch", {
      name: /all functions/i,
    });
    await user.click(allFunctionsSwitch);
    expect(onToggleAllFunctions).toHaveBeenLastCalledWith(
      "tool-1",
      ["list_pages", "archive_page"],
      true,
    );

    view.rerender(
      <ToolConfigDrawer
        {...drawerProps}
        onToggleAllFunctions={onToggleAllFunctions}
        tool={tool}
        agentTool={{
          ...agentTool,
          unselected_functions: [],
          tool,
        }}
      />,
    );
    await user.click(
      screen.getByRole("switch", { name: /all functions/i }),
    );
    expect(onToggleAllFunctions).toHaveBeenLastCalledWith(
      "tool-1",
      ["list_pages", "archive_page"],
      false,
    );
  });

  it("lets org admins expand long function descriptions", async () => {
    const { userEvent } = await import("@testing-library/user-event");
    const user = userEvent.setup();
    const longDescription =
      "Lists pages visible to the connected workspace and includes enough context to help an agent choose the correct page before it starts a follow-up action. ".repeat(
        2,
      );
    const tool = {
      ...makeTool(true),
      auth_type: "oauth2",
      tool_functions_schema: {
        functions: [
          {
            type: "function",
            name: "list_pages",
            description: longDescription,
            parameters: {
              type: "object",
              properties: {},
            },
          },
        ],
      },
    };

    render(
      <ToolConfigDrawer
        {...drawerProps}
        tool={tool}
        agentTool={{ ...agentTool, tool }}
      />,
    );

    const showDescription = screen.getByRole("button", {
      name: /show full description/i,
    });
    expect(showDescription).toHaveAttribute("aria-expanded", "false");

    await user.click(showDescription);

    expect(showDescription).toHaveAttribute("aria-expanded", "true");
    const description = document.getElementById(
      showDescription.getAttribute("aria-controls") || "",
    );
    expect(description).toHaveTextContent(longDescription.trim());
  });

  it("lets org admins expand the long tool description in the drawer header", async () => {
    const { userEvent } = await import("@testing-library/user-event");
    const user = userEvent.setup();
    const longDescription =
      "Connects the agent to the remote workspace and exposes the functions needed to search, inspect, and update records for this organization. ".repeat(
        2,
      );
    const tool = {
      ...makeTool(true),
      description: longDescription,
      auth_type: "oauth2",
    };

    render(
      <ToolConfigDrawer
        {...drawerProps}
        tool={tool}
        agentTool={{ ...agentTool, tool }}
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

  it("filters org function cards from the drawer search", async () => {
    const { userEvent } = await import("@testing-library/user-event");
    const user = userEvent.setup();
    const tool = {
      ...makeTool(true),
      auth_type: "oauth2",
      tool_functions_schema: {
        functions: [
          {
            type: "function",
            name: "list_pages",
            description: "List pages from the workspace",
            parameters: {
              type: "object",
              properties: {
                query: {
                  type: "string",
                  description: "Optional search text",
                },
              },
            },
          },
          {
            type: "function",
            name: "archive_page",
            description: "Archive a page in the workspace",
            parameters: {
              type: "object",
              properties: {
                page_id: {
                  type: "string",
                  description: "Page identifier",
                },
              },
            },
          },
        ],
      },
    };

    render(
      <ToolConfigDrawer
        {...drawerProps}
        tool={tool}
        agentTool={{ ...agentTool, tool }}
      />,
    );

    const search = screen.getByRole("searchbox", {
      name: /search functions/i,
    });
    expect(screen.getByText("list_pages")).toBeInTheDocument();
    expect(screen.getByText("archive_page")).toBeInTheDocument();

    await user.type(search, "archive");

    expect(screen.queryByText("list_pages")).not.toBeInTheDocument();
    expect(screen.getByText("archive_page")).toBeInTheDocument();
    expect(screen.getByText(/1 of 2 functions/i)).toBeInTheDocument();
  });
});
