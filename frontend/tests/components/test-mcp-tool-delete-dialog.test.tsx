/**
 * Tests for McpToolDeleteDialog — the type-to-confirm delete wrapper for MCP
 * platform tools (RFC §6.6 delete guardrails).
 *
 * Covers:
 *  - Renders the shared DeleteConfirmationDialog with the tool name + "MCP Server".
 *  - Fetches usage on open; in-use tools surface a "Used by N agents" warning
 *    listing the agent names.
 *  - Not-in-use tools show no usage warnings (the type-to-confirm gate still
 *    applies via the shared dialog).
 *  - Confirming with the "Delete" keyword calls deletePlatformTool with
 *    `force = count > 0` (force=true when in use, force=false when not), then
 *    closes the dialog.
 *  - A backend 409 `in_use` error surfaces in the dialog's error area (the
 *    usage pre-fetch raced / direct-API safety net).
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  renderWithProviders as render,
  screen,
  waitFor,
  fireEvent,
} from "../utils/test-utils";
import { McpToolDeleteDialog } from "@/components/tools/mcp-tool-delete-dialog";
import { server } from "../mocks/server";
import { http, HttpResponse } from "msw";
import type { PlatformTool } from "@/types/agent";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const mcpTool: PlatformTool = {
  id: "tool-1",
  name: "deepwiki",
  description: "DeepWiki MCP",
  tool_source: "mcp",
  is_active: true,
  is_published: true,
  requires_auth: false,
  auth_type: null,
  config_schema: null,
  tool_functions_schema: null,
  auth_config: null,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

const usageHandler = (
  count: number,
  agents: { agent_id: string; agent_name: string | null; organization_id: string | null }[] = [],
) =>
  http.get(`${API_BASE_URL}/api/v1/tools/platform/:toolId/usage`, () =>
    HttpResponse.json({ count, agents }),
  );

describe("McpToolDeleteDialog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the shared dialog with the tool name + MCP Server type", async () => {
    server.use(usageHandler(0));
    render(
      <McpToolDeleteDialog
        open={true}
        onOpenChange={vi.fn()}
        tool={mcpTool}
        onDeleted={vi.fn()}
      />,
    );

    // Title "Delete MCP Server" (heading) and the tool name in the description.
    expect(screen.getByRole("heading", { name: /Delete MCP Server/i })).toBeInTheDocument();
    expect(screen.getByText(/deepwiki/i)).toBeInTheDocument();
  });

  it("lists usage warnings with agent names when the tool is in use", async () => {
    server.use(
      usageHandler(2, [
        { agent_id: "agent-1", agent_name: "Alex", organization_id: "org-1" },
        { agent_id: "agent-2", agent_name: "Sam", organization_id: "org-1" },
      ]),
    );
    render(
      <McpToolDeleteDialog
        open={true}
        onOpenChange={vi.fn()}
        tool={mcpTool}
        onDeleted={vi.fn()}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText(/Used by 2 agents/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/Alex/)).toBeInTheDocument();
    expect(screen.getByText(/Sam/)).toBeInTheDocument();
    expect(screen.getByText(/loses this tool on their next call/i)).toBeInTheDocument();
  });

  it("renders each affected agent name as a link to that agent's Tools tab", async () => {
    server.use(
      usageHandler(2, [
        { agent_id: "agent-1", agent_name: "Alex", organization_id: "org-1" },
        { agent_id: "agent-2", agent_name: "Sam", organization_id: "org-1" },
      ]),
    );
    render(
      <McpToolDeleteDialog
        open={true}
        onOpenChange={vi.fn()}
        tool={mcpTool}
        onDeleted={vi.fn()}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText(/Used by 2 agents/i)).toBeInTheDocument();
    });
    const alexLink = screen.getByRole("link", { name: /Alex/i });
    const samLink = screen.getByRole("link", { name: /Sam/i });
    expect(alexLink).toHaveAttribute("href", "/agents/agent-1/tools");
    expect(samLink).toHaveAttribute("href", "/agents/agent-2/tools");
    // Links open in a NEW tab so the admin can review the agent without losing the
    // delete dialog (and so same-route links from the agent's own page still work
    // — a same-tab link to the current route is a no-op navigation).
    expect(alexLink).toHaveAttribute("target", "_blank");
    expect(samLink).toHaveAttribute("target", "_blank");
    expect(alexLink).toHaveAttribute("rel", "noopener noreferrer");
    expect(samLink).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("falls back to the agent id (as link text) when agent_name is null", async () => {
    server.use(
      usageHandler(1, [
        { agent_id: "agent-9", agent_name: null, organization_id: null },
      ]),
    );
    render(
      <McpToolDeleteDialog
        open={true}
        onOpenChange={vi.fn()}
        tool={mcpTool}
        onDeleted={vi.fn()}
      />,
    );
    await waitFor(() => {
      expect(screen.getByRole("link", { name: /agent-9/i })).toHaveAttribute(
        "href",
        "/agents/agent-9/tools",
      );
    });
  });

  it("shows no usage warnings when the tool is not in use", async () => {
    server.use(usageHandler(0));
    render(
      <McpToolDeleteDialog
        open={true}
        onOpenChange={vi.fn()}
        tool={mcpTool}
        onDeleted={vi.fn()}
      />,
    );

    // Wait for the usage fetch to settle (no warnings render).
    await waitFor(() => {
      expect(screen.queryByText(/Used by/i)).not.toBeInTheDocument();
    });
    // Type-to-confirm gate is still present (the confirmation input).
    expect(screen.getByPlaceholderText("Delete")).toBeInTheDocument();
  });

  it("deletes with force=true when in use after typing Delete", async () => {
    const { userEvent } = await import("@testing-library/user-event");
    const user = userEvent.setup();
    let deleteUrl: string | null = null;
    server.use(
      usageHandler(1, [
        { agent_id: "agent-1", agent_name: "Alex", organization_id: "org-1" },
      ]),
      http.delete(`${API_BASE_URL}/api/v1/tools/platform/:toolId`, ({ request }) => {
        deleteUrl = request.url;
        return HttpResponse.json({ deleted: true });
      }),
    );
    const onOpenChange = vi.fn();
    const onDeleted = vi.fn();
    render(
      <McpToolDeleteDialog
        open={true}
        onOpenChange={onOpenChange}
        tool={mcpTool}
        onDeleted={onDeleted}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText(/Used by 1 agent/i)).toBeInTheDocument();
    });
    await user.type(screen.getByPlaceholderText("Delete"), "Delete");
    await user.click(screen.getByRole("button", { name: /Delete MCP Server/i }));

    await waitFor(() => expect(deleteUrl).not.toBeNull());
    expect(deleteUrl).toContain("force=true");
    expect(onDeleted).toHaveBeenCalled();
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("deletes with force=false when not in use after typing Delete", async () => {
    const { userEvent } = await import("@testing-library/user-event");
    const user = userEvent.setup();
    let deleteUrl: string | null = null;
    server.use(
      usageHandler(0),
      http.delete(`${API_BASE_URL}/api/v1/tools/platform/:toolId`, ({ request }) => {
        deleteUrl = request.url;
        return HttpResponse.json({ deleted: true });
      }),
    );
    render(
      <McpToolDeleteDialog
        open={true}
        onOpenChange={vi.fn()}
        tool={mcpTool}
        onDeleted={vi.fn()}
      />,
    );

    await user.type(screen.getByPlaceholderText("Delete"), "Delete");
    await user.click(screen.getByRole("button", { name: /Delete MCP Server/i }));

    await waitFor(() => expect(deleteUrl).not.toBeNull());
    expect(deleteUrl).not.toContain("force=true");
  });

  it("surfaces a backend 409 in_use error in the dialog error area", async () => {
    const { userEvent } = await import("@testing-library/user-event");
    const user = userEvent.setup();
    server.use(
      usageHandler(0),
      http.delete(`${API_BASE_URL}/api/v1/tools/platform/:toolId`, () =>
        HttpResponse.json(
          {
            error: "in_use",
            count: 1,
            agents: [{ agent_id: "agent-1", agent_name: "Alex", organization_id: "org-1" }],
            message: "Tool is in use by 1 agent. Force-delete to detach them.",
          },
          { status: 409 },
        ),
      ),
    );
    render(
      <McpToolDeleteDialog
        open={true}
        onOpenChange={vi.fn()}
        tool={mcpTool}
        onDeleted={vi.fn()}
      />,
    );

    await user.type(screen.getByPlaceholderText("Delete"), "Delete");
    await user.click(screen.getByRole("button", { name: /Delete MCP Server/i }));

    await waitFor(() => {
      expect(screen.getByText(/in use by 1 agent/i)).toBeInTheDocument();
    });
  });
});
