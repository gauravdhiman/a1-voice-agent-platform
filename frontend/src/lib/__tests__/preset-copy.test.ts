import { describe, expect, it } from "vitest";
import { getClonePresetName } from "@/lib/preset-copy";

describe("getClonePresetName", () => {
  it("prefixes an available source name", () => {
    expect(getClonePresetName("Support Voice", ["Support Voice"])).toBe(
      "Copy of Support Voice",
    );
  });

  it("increments the copy suffix when generated names already exist", () => {
    expect(
      getClonePresetName("Support Voice", [
        "Copy of Support Voice",
        "copy of support voice (2)",
      ]),
    ).toBe("Copy of Support Voice (3)");
  });

  it("ignores surrounding whitespace and case when checking collisions", () => {
    expect(
      getClonePresetName("  Support Voice  ", [" copy of support voice "]),
    ).toBe("Copy of Support Voice (2)");
  });

  it("keeps long generated names within the backend limit", () => {
    const sourceName = "A".repeat(100);
    const copyName = getClonePresetName(sourceName, []);

    expect(copyName).toBe(`Copy of ${"A".repeat(92)}`);
    expect(copyName).toHaveLength(100);
  });

  it("reserves room for a numeric suffix after a long-name collision", () => {
    const sourceName = "B".repeat(100);
    const firstCopy = `Copy of ${"B".repeat(92)}`;

    const copyName = getClonePresetName(sourceName, [firstCopy]);

    expect(copyName).toBe(`Copy of ${"B".repeat(88)} (2)`);
    expect(copyName).toHaveLength(100);
  });
});
