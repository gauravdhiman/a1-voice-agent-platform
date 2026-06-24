/**
 * Tests for the row-level action buttons rendered by <SkillEditor>.
 *
 * These tests pin down the bug the user reported: a deprecated platform
 * skill must show BOTH "reactivate" and "delete" actions, not just one.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import type { EditableSkill, SkillEditorAdapter } from "@/components/skills/skill-editor";
import { SkillEditor } from "@/components/skills/skill-editor";

function makeSkill(over: Partial<EditableSkill> = {}): EditableSkill {
  return {
    id: "skill-1",
    slug: "test-skill",
    name: "Test Skill",
    description: "A test skill",
    content: "# x",
    version: "2026.06.24_1",
    status: "active",
    created_at: "",
    updated_at: "",
    ...over,
  };
}

function makeAdapter(skills: EditableSkill[]): SkillEditorAdapter {
  return {
    loadSkills: vi.fn().mockResolvedValue(skills),
    loadFiles: vi.fn().mockResolvedValue([]),
    getFileContent: vi.fn(),
    createSkill: vi.fn(),
    updateSkill: vi.fn(),
    createFile: vi.fn(),
    updateFile: vi.fn(),
    deleteFile: vi.fn(),
    deleteSkill: vi.fn().mockResolvedValue(undefined),
    restoreSkill: vi.fn().mockResolvedValue(undefined),
    deprecateSkill: vi.fn().mockResolvedValue(undefined),
    reactivateSkill: vi.fn().mockResolvedValue(undefined),
  };
}

describe("SkillEditor row actions by skill status", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("active skill shows Deprecate and Delete actions", async () => {
    const skill = makeSkill({ status: "active" });
    render(
      <SkillEditor
        mode="platform"
        adapter={makeAdapter([skill])}
        canCreate
        canEdit
        canDelete
        deleteMode="soft"
        showDeletedFilter
      />,
    );
    const row = await screen.findByText("Test Skill");
    // Walk up to the row container (the flex group div)
    const rowContainer = row.closest(".group")!;
    expect(
      within(rowContainer).queryByTitle("Deprecate skill"),
    ).toBeInTheDocument();
    expect(
      within(rowContainer).queryByTitle("Delete skill"),
    ).toBeInTheDocument();
    expect(
      within(rowContainer).queryByTitle("Reactivate skill"),
    ).not.toBeInTheDocument();
    expect(
      within(rowContainer).queryByTitle("Restore skill"),
    ).not.toBeInTheDocument();
  });

  it("deprecated skill shows BOTH Reactivate AND Delete actions", async () => {
    // The reported bug: deprecated skills only showed Reactivate, missing Delete.
    const skill = makeSkill({ status: "deprecated" });
    render(
      <SkillEditor
        mode="platform"
        adapter={makeAdapter([skill])}
        canCreate
        canEdit
        canDelete
        deleteMode="soft"
        showDeletedFilter
      />,
    );
    const row = await screen.findByText("Test Skill");
    const rowContainer = row.closest(".group")!;
    expect(
      within(rowContainer).queryByTitle("Reactivate skill"),
    ).toBeInTheDocument();
    expect(
      within(rowContainer).queryByTitle("Delete skill"),
    ).toBeInTheDocument();
    expect(
      within(rowContainer).queryByTitle("Deprecate skill"),
    ).not.toBeInTheDocument();
    expect(
      within(rowContainer).queryByTitle("Restore skill"),
    ).not.toBeInTheDocument();
  });

  it("deleted skill shows only Restore action", async () => {
    const skill = makeSkill({ status: "deleted" });
    render(
      <SkillEditor
        mode="platform"
        adapter={makeAdapter([skill])}
        canCreate
        canEdit
        canDelete
        deleteMode="soft"
        showDeletedFilter
      />,
    );
    const row = await screen.findByText("Test Skill");
    const rowContainer = row.closest(".group")!;
    expect(
      within(rowContainer).queryByTitle("Restore skill"),
    ).toBeInTheDocument();
    expect(
      within(rowContainer).queryByTitle("Delete skill"),
    ).not.toBeInTheDocument();
    expect(
      within(rowContainer).queryByTitle("Deprecate skill"),
    ).not.toBeInTheDocument();
    expect(
      within(rowContainer).queryByTitle("Reactivate skill"),
    ).not.toBeInTheDocument();
  });

  it("clicking Deprecate on an active skill calls adapter.deprecateSkill", async () => {
    const skill = makeSkill({ status: "active" });
    const adapter = makeAdapter([skill]);
    render(
      <SkillEditor
        mode="platform"
        adapter={adapter}
        canCreate
        canEdit
        canDelete
        deleteMode="soft"
        showDeletedFilter
      />,
    );
    const row = await screen.findByText("Test Skill");
    const rowContainer = row.closest(".group")!;
    fireEvent.click(within(rowContainer).getByTitle("Deprecate skill"));
    expect(adapter.deprecateSkill).toHaveBeenCalledWith("skill-1");
  });

  it("clicking Delete on a deprecated skill opens the confirm dialog and then deletes", async () => {
    // Soft-delete (platform) goes through a confirm dialog, so clicking the
    // trash icon sets the delete target and renders the dialog; clicking
    // "Delete Skill" in the footer is what actually invokes deleteSkill.
    const skill = makeSkill({ status: "deprecated" });
    const adapter = makeAdapter([skill]);
    render(
      <SkillEditor
        mode="platform"
        adapter={adapter}
        canCreate
        canEdit
        canDelete
        deleteMode="soft"
        showDeletedFilter
      />,
    );
    const row = await screen.findByText("Test Skill");
    const rowContainer = row.closest(".group")!;
    fireEvent.click(within(rowContainer).getByTitle("Delete skill"));
    // Dialog appears; click the destructive confirm button.
    const dialog = await screen.findByRole("dialog");
    fireEvent.click(within(dialog).getByText("Delete Skill"));
    await vi.waitFor(() =>
      expect(adapter.deleteSkill).toHaveBeenCalledWith("skill-1"),
    );
  });
});
