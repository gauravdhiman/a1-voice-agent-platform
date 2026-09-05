import { describe, expect, it } from "vitest";

import {
  DEFAULT_TOOL_FILTER_TYPE,
  shouldShowSeeAllToolsPrompt,
} from "@/components/tools/tool-filters";

describe("agent tool filter defaults", () => {
  it("starts on Connected regardless of whether the agent has connections", () => {
    expect(DEFAULT_TOOL_FILTER_TYPE).toBe("connected");
  });

  it("prompts an empty Connected view to show all tools", () => {
    expect(
      shouldShowSeeAllToolsPrompt({
        filterType: "connected",
        connectedToolCount: 0,
        searchQuery: "",
      }),
    ).toBe(true);
  });

  it("keeps search-empty states separate from the See all tools prompt", () => {
    expect(
      shouldShowSeeAllToolsPrompt({
        filterType: "connected",
        connectedToolCount: 0,
        searchQuery: "calendar",
      }),
    ).toBe(false);
  });
});
