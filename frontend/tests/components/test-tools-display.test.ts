/**
 * Tests for buildAgentToolsDisplay — the Tools-tab merge that surfaces
 * connected-but-unpublished or organization-hidden tools inline in the grid.
 *
 * The worker loads an agent's tools without filtering on `is_published`, so an
 * unpublished tool the agent already has keeps working at runtime. The
 * published-only catalog hides it; this merge adds it back (flagged) so the org
 * admin sees it's still mapped. See tools-display.ts for the full rationale.
 */
import { describe, it, expect } from "vitest";
import { buildAgentToolsDisplay } from "@/components/tools/tools-display";
import type { PlatformTool, AgentTool } from "@/types/agent";
import { AuthStatus, ConnectionStatus } from "@/types/agent";

const tool = (
  overrides: Partial<PlatformTool> & { id: string },
): PlatformTool => ({
  name: overrides.name ?? overrides.id,
  description: null,
  config_schema: null,
  tool_functions_schema: null,
  is_active: true,
  is_published: true,
  requires_auth: false,
  auth_type: null,
  auth_config: null,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  ...overrides,
});

const agentTool = (
  toolId: string,
  toolOverride: Partial<PlatformTool> & { id: string },
): AgentTool => ({
  id: `at-${toolId}`,
  agent_id: "agent-1",
  tool_id: toolId,
  config: null,
  sensitive_config: null,
  unselected_functions: null,
  is_enabled: true,
  auth_status: AuthStatus.NOT_AUTHENTICATED,
  token_expires_at: null,
  connection_status: ConnectionStatus.CONNECTED_NO_AUTH,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  tool: tool(toolOverride),
});

describe("buildAgentToolsDisplay", () => {
  it("returns the catalog as-is when the agent has no unpublished attachments", () => {
    const catalog = [tool({ id: "a", is_published: true }), tool({ id: "b", is_published: true })];
    const { allTools, unpublishedConnectedIds } = buildAgentToolsDisplay(catalog, []);
    expect(allTools.map((t) => t.id)).toEqual(["a", "b"]);
    expect(unpublishedConnectedIds.size).toBe(0);
  });

  it("surfaces a connected-but-unpublished tool inline, flagged in unpublishedConnectedIds", () => {
    const catalog = [tool({ id: "a", is_published: true })];
    const agentTools = [
      agentTool("a", { id: "a", is_published: true }),
      agentTool("u", { id: "u", name: "ghost", is_published: false }),
    ];
    const { allTools, unpublishedConnectedIds, hiddenConnectedIds } =
      buildAgentToolsDisplay(catalog, agentTools);
    // The unpublished tool "u" is appended after the catalog.
    expect(allTools.map((t) => t.id)).toEqual(["a", "u"]);
    expect(allTools[1].name).toBe("ghost");
    expect(unpublishedConnectedIds.has("u")).toBe(true);
    expect(unpublishedConnectedIds.has("a")).toBe(false);
    expect(hiddenConnectedIds.size).toBe(0);
  });

  it("surfaces a connected-but-hidden tool with a hidden status", () => {
    const catalog = [tool({ id: "a", is_published: true })];
    const agentTools = [
      agentTool("h", {
        id: "h",
        is_published: true,
        is_visible: false,
      }),
    ];

    const { allTools, hiddenConnectedIds, unpublishedConnectedIds } =
      buildAgentToolsDisplay(catalog, agentTools);

    expect(allTools.map((t) => t.id)).toEqual(["a", "h"]);
    expect(hiddenConnectedIds.has("h")).toBe(true);
    expect(unpublishedConnectedIds.has("h")).toBe(false);
  });

  it("does not add an organization-hidden tool that is not mapped to the agent", () => {
    const catalog = [tool({ id: "a", is_published: true })];
    const { allTools, hiddenConnectedIds } = buildAgentToolsDisplay(catalog, [
      agentTool("a", { id: "a", is_published: true }),
    ]);

    expect(allTools.map((t) => t.id)).toEqual(["a"]);
    expect(hiddenConnectedIds.size).toBe(0);
  });

  it("does NOT add an unpublished tool that is not mapped to the agent", () => {
    const catalog = [tool({ id: "a", is_published: true })];
    // "u" is unpublished but the agent has no attachment to it.
    const { allTools, unpublishedConnectedIds } = buildAgentToolsDisplay(catalog, [
      agentTool("a", { id: "a", is_published: true }),
    ]);
    expect(allTools.map((t) => t.id)).toEqual(["a"]);
    expect(unpublishedConnectedIds.size).toBe(0);
  });

  it("does not duplicate a tool that appears in both the catalog and the agent's attachments", () => {
    // Platform admin viewing with drafts could in theory have an unpublished
    // tool in the catalog AND attached. Dedupe by id so only one card renders.
    const catalog = [tool({ id: "u", is_published: false })];
    const agentTools = [agentTool("u", { id: "u", is_published: false })];
    const { allTools, unpublishedConnectedIds } = buildAgentToolsDisplay(catalog, agentTools);
    expect(allTools.map((t) => t.id)).toEqual(["u"]);
    expect(unpublishedConnectedIds.has("u")).toBe(true);
  });

  it("treats an agent_tool whose joined tool is missing (is_published undefined) as published", () => {
    // Defensive: a deleted platform tool cascades its agent_tools row away, so
    // `tool` is always present for live rows — but never treat undefined as
    // "unpublished" (would wrongly flag/duplicate).
    const catalog = [tool({ id: "a", is_published: true })];
    const atNoTool: AgentTool = {
      ...agentTool("a", { id: "a", is_published: true }),
      tool: undefined,
    };
    const { allTools, unpublishedConnectedIds } = buildAgentToolsDisplay(catalog, [atNoTool]);
    expect(allTools.map((t) => t.id)).toEqual(["a"]);
    expect(unpublishedConnectedIds.size).toBe(0);
  });
});
