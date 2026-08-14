/**
 * Shared navigation contract for the agent detail page.
 *
 * Keeping the tab values in one place lets old `properties` links continue to
 * work while new links use the more meaningful `persona` label.
 */

export const AGENT_DETAIL_TABS = [
  "persona",
  "skills",
  "tools",
  "settings",
  "recordings",
] as const;

const STANDARD_AGENT_DETAIL_TABS = AGENT_DETAIL_TABS.filter(
  (tab) => tab !== "recordings",
) as readonly Exclude<AgentDetailTab, "recordings">[];

export type AgentDetailTab = (typeof AGENT_DETAIL_TABS)[number];

/**
 * Returns the tabs available for an agent based on its recording setting.
 *
 * @param callRecordingEnabled - Whether this agent has call recording enabled.
 * @returns Standard tabs plus Call Recordings when recording is enabled.
 */
export function getAgentDetailTabs(
  callRecordingEnabled: boolean,
): readonly AgentDetailTab[] {
  return callRecordingEnabled ? AGENT_DETAIL_TABS : STANDARD_AGENT_DETAIL_TABS;
}

/**
 * Determines whether an authorized user should see the recordings tab.
 *
 * Historical recordings remain discoverable when an older environment does
 * not yet return the agent-level setting, or when recording is later disabled.
 *
 * @param callRecordingEnabled - Whether recording is enabled for the agent.
 * @param hasRecordedCalls - Whether completed recordings exist for the agent.
 * @param canViewRecordings - Whether the current user may view recordings.
 * @returns True when the recordings tab should be rendered.
 */
export function shouldShowAgentRecordingsTab(
  callRecordingEnabled: boolean,
  hasRecordedCalls: boolean,
  canViewRecordings: boolean,
): boolean {
  return canViewRecordings && (callRecordingEnabled || hasRecordedCalls);
}

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
