import { describe, expect, it } from "vitest";
import {
  buildStarterSkillMarkdown,
  suggestSkillSlugFromName,
} from "@/lib/skill-create";

describe("skill-create helpers", () => {
  it("suggests a kebab-case slug from the skill name", () => {
    expect(suggestSkillSlugFromName("Appointment Booking")).toBe(
      "appointment-booking",
    );
    expect(suggestSkillSlugFromName("  Call  Screening!  ")).toBe(
      "call-screening",
    );
  });

  it("builds a starter SKILL.md with title and empty sections", () => {
    expect(buildStarterSkillMarkdown("Appointment Booking")).toBe(
      "# Appointment Booking\n\n## When to use\n\n\n## Instructions\n\n",
    );
  });

  it("falls back to Untitled Skill when name is blank", () => {
    expect(buildStarterSkillMarkdown("   ")).toContain("# Untitled Skill");
  });
});
