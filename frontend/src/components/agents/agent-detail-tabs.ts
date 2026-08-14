/**
 * Shared navigation contract for the agent detail page.
 *
 * Keeping the tab values in one place lets old `properties` links continue to
 * work while new links use the more meaningful `persona` label.
 */

export const AGENT_DETAIL_TABS = ["persona", "skills", "tools", "settings"] as const;

export type AgentDetailTab = (typeof AGENT_DETAIL_TABS)[number];

/**
 * Converts an agent detail URL value into a supported tab.
 *
 * @param value - Raw tab query-string value.
 * @returns A supported tab, defaulting to `persona` for missing or unknown values.
 */
export function normalizeAgentDetailTab(value: string | null): AgentDetailTab {
  if (value === "properties") return "persona";
  if (AGENT_DETAIL_TABS.includes(value as AgentDetailTab)) {
    return value as AgentDetailTab;
  }
  return "persona";
}
