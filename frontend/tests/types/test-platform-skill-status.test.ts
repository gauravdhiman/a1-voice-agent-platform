/**
 * Tests for PlatformSkillStatus type and the new statuses query param.
 *
 * These tests should fail until the type and service are refactored to use
 * a single `status` enum instead of `is_active`/`is_deleted` booleans.
 */

import type { PlatformSkillSummary, PlatformSkill, PlatformSkillUpdate } from "@/types/skill";
import type { PlatformSkillStatus } from "@/types/skill";

describe("PlatformSkillStatus type", () => {
  it("exposes draft/active/deprecated/deleted values", () => {
    const statuses: PlatformSkillStatus[] = ["draft", "active", "deprecated", "deleted"];
    expect(statuses).toHaveLength(4);
  });

  it("PlatformSkillSummary carries status (not is_active/is_deleted)", () => {
    const summary: PlatformSkillSummary = {
      id: "s1",
      slug: "appointment-booking",
      name: "Appointment Booking",
      description: null,
      version: "2026.06.24_1",
      status: "active",
    };
    expect(summary.status).toBe("active");
    // @ts-expect-error - is_active should be gone from the type
    expect(summary.is_active).toBeUndefined();
  });

  it("PlatformSkill carries status", () => {
    const skill: PlatformSkill = {
      id: "s1",
      slug: "appointment-booking",
      name: "Appointment Booking",
      description: null,
      content: "# X",
      version: "2026.06.24_1",
      author: null,
      content_hash: "h",
      status: "deprecated",
      files: [],
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    };
    expect(skill.status).toBe("deprecated");
  });

  it("PlatformSkillUpdate no longer carries status", () => {
    const update: PlatformSkillUpdate = {
      name: "Renamed",
    };
    // status must not be settable via update — transitions are dedicated endpoints
    expect("status" in update).toBe(false);
  });
});
