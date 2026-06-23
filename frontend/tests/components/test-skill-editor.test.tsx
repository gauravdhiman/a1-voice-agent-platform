/**
 * Component tests for the shared <SkillEditor>.
 *
 * Covers the regression where selecting a platform skill (whose list endpoint
 * returns summaries without content) left the SKILL.md body blank: content must
 * be lazily hydrated via the adapter's hydrateSkill() and then rendered.
 */
import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import type { SkillEditorAdapter, EditableSkill } from "@/components/skills/skill-editor";

// next/navigation is used by pages that host the editor, and the editor itself
// only uses syncUrl (a prop). Mock to be safe for any future internal usage.
vi.mock("next/navigation", () => ({
  useSearchParams: () => ({ get: () => null }),
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
}));

import { SkillEditor } from "@/components/skills/skill-editor";

function makeSkill(over: Partial<EditableSkill> = {}): EditableSkill {
  return {
    id: "skill-1",
    slug: "test-skill",
    name: "Test Skill",
    description: "A test skill",
    content: "",
    version: "2026.06.20_1",
    is_active: true,
    created_at: "",
    updated_at: "",
    ...over,
  };
}

describe("SkillEditor", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the skill list from the adapter", async () => {
    const adapter: SkillEditorAdapter = {
      loadSkills: vi.fn().mockResolvedValue([makeSkill()]),
      loadFiles: vi.fn().mockResolvedValue([]),
      getFileContent: vi.fn(),
      createSkill: vi.fn(),
      updateSkill: vi.fn(),
      createFile: vi.fn(),
      updateFile: vi.fn(),
      deleteFile: vi.fn(),
    };
    render(<SkillEditor mode="platform" adapter={adapter} canCreate canEdit />);
    expect(await screen.findByText("Test Skill")).toBeInTheDocument();
    expect(adapter.loadSkills).toHaveBeenCalled();
  });

  it("lazily hydrates and renders SKILL.md content when a skill is selected (platform summaries have no content)", async () => {
    const skill = makeSkill({ content: "" });
    const hydrated = makeSkill({ content: "# Rendered Skill Content" });
    const adapter: SkillEditorAdapter = {
      loadSkills: vi.fn().mockResolvedValue([skill]),
      loadFiles: vi.fn().mockResolvedValue([]),
      getFileContent: vi.fn(),
      createSkill: vi.fn(),
      updateSkill: vi.fn(),
      createFile: vi.fn(),
      updateFile: vi.fn(),
      deleteFile: vi.fn(),
      hydrateSkill: vi.fn().mockResolvedValue(hydrated),
    };
    render(<SkillEditor mode="platform" adapter={adapter} canCreate canEdit />);

    const row = await screen.findByText("Test Skill");
    fireEvent.click(row);

    // Content is hydrated asynchronously and rendered via ReactMarkdown.
    await waitFor(() => expect(adapter.hydrateSkill).toHaveBeenCalledWith(skill));
    expect(await screen.findByText("Rendered Skill Content")).toBeInTheDocument();
  });

  it("does not call hydrateSkill when skills already carry content (org-style list)", async () => {
    const skill = makeSkill({ content: "# Already Loaded" });
    const adapter: SkillEditorAdapter = {
      loadSkills: vi.fn().mockResolvedValue([skill]),
      loadFiles: vi.fn().mockResolvedValue([]),
      getFileContent: vi.fn(),
      createSkill: vi.fn(),
      updateSkill: vi.fn(),
      createFile: vi.fn(),
      updateFile: vi.fn(),
      deleteFile: vi.fn(),
      hydrateSkill: vi.fn(),
    };
    render(<SkillEditor mode="organization" adapter={adapter} canCreate canEdit canDelete showSourceBadge />);
    const row = await screen.findByText("Test Skill");
    fireEvent.click(row);
    expect(await screen.findByText("Already Loaded")).toBeInTheDocument();
    // No hydration needed when content is present.
    expect(adapter.hydrateSkill).not.toHaveBeenCalled();
  });
});
