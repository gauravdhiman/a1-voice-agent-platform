import { describe, expect, it } from "vitest";

import {
  AGENT_DETAIL_TABS,
  getAgentDetailTabs,
  normalizeAgentDetailTab,
  shouldShowAgentRecordingsTab,
} from "../agent-detail-tabs";

describe("agent detail tabs", () => {
  it("organizes the detail page around persona, skills, tools, and settings", () => {
    expect(AGENT_DETAIL_TABS).toEqual([
      "persona",
      "skills",
      "tools",
      "settings",
      "recordings",
    ]);
  });

  it("shows Call Recordings only when recording is enabled", () => {
    expect(getAgentDetailTabs(false)).toEqual([
      "persona",
      "skills",
      "tools",
      "settings",
    ]);
    expect(getAgentDetailTabs(true)).toContain("recordings");
  });

  it("shows recordings when historical recordings exist even without the setting", () => {
    expect(shouldShowAgentRecordingsTab(false, true, true)).toBe(true);
    expect(shouldShowAgentRecordingsTab(false, false, true)).toBe(false);
    expect(shouldShowAgentRecordingsTab(true, false, false)).toBe(false);
  });

  it("keeps old properties links pointed at the Persona tab", () => {
    expect(normalizeAgentDetailTab("properties")).toBe("persona");
  });

  it("falls back to Persona for missing or unknown tab values", () => {
    expect(normalizeAgentDetailTab(null)).toBe("persona");
    expect(normalizeAgentDetailTab("unknown")).toBe("persona");
  });
});
