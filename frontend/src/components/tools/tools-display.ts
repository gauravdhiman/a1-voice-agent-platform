import type { PlatformTool, AgentTool } from "@/types/agent";

/**
 * Build the Tools-tab display set for an agent (RFC §6.6 publish lifecycle).
 *
 * The published catalog (`usePlatformTools`, published-only) is the set of
 * tools an org user can attach. But the worker loads an agent's tools by
 * joining `agent_tools` -> `platform_tools` **without** filtering on
 * `is_published`, so an already-connected tool keeps working at runtime after
 * the platform admin unpublishes it — even though it vanishes from the catalog.
 *
 * This merge surfaces those connected-but-unpublished tools inline in the grid
 * (flagged via `unpublishedConnectedIds` so each card can render an amber
 * "Unpublished" pill + note). Unpublished AND not-mapped tools are never in
 * `agentTools`, so they don't appear — unchanged behavior.
 *
 * @param platformTools - Published catalog tools (published-only query).
 * @param agentTools - The agent's attached tools, each with a joined `tool`.
 * @returns `allTools` (catalog + connected-but-unpublished, deduped by id) and
 *   `unpublishedConnectedIds` (tool ids that are connected AND unpublished, for
 *   the card pill).
 */
export function buildAgentToolsDisplay(
  platformTools: PlatformTool[],
  agentTools: AgentTool[],
): {
  allTools: PlatformTool[];
  unpublishedConnectedIds: Set<string>;
  hiddenConnectedIds: Set<string>;
} {
  const unpublishedConnectedIds = new Set(
    agentTools
      .filter((at) => at.tool?.is_published === false)
      .map((at) => at.tool_id),
  );
  const hiddenConnectedIds = new Set(
    agentTools
      .filter((at) => at.tool?.is_visible === false)
      .map((at) => at.tool_id),
  );

  const catalogIds = new Set(platformTools.map((t) => t.id));
  const extras = agentTools
    .filter(
      (at) =>
        at.tool !== undefined &&
        (at.tool.is_published === false || at.tool.is_visible === false) &&
        !catalogIds.has(at.tool_id),
    )
    .map((at) => at.tool) as PlatformTool[];

  return {
    allTools: [...platformTools, ...extras],
    unpublishedConnectedIds,
    hiddenConnectedIds,
  };
}
