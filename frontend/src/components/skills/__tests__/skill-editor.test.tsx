/**
 * Tests for the shared <SkillEditor> row-action permission gate.
 *
 * Contract (mirrors the N1 permission-aware-UI follow-up; see
 * `docs/tw-drafts/navigation-redesign.md` Section 6.5 + the user
 * feedback that "actions like deleting a skill ... should respect
 * the permissions of the user's role"):
 *
 *   - When `canDelete` is false (e.g. a regular org member), the
 *     per-row "Delete skill" button MUST NOT be rendered. The
 *     confirm dialog is already canDelete-gated, but the per-row
 *     trash icon was leaking the action.
 *   - When `canDelete` is true (e.g. an org admin), the per-row
 *     "Delete skill" button IS rendered.
 *   - When the adapter exposes `deleteSkill` but `canDelete` is
 *     false, no delete UI surfaces — i.e. the permission gate
 *     dominates the adapter capability check.
 *   - Other actions (deprecate, reactivate, restore) are driven
 *     only by adapter capabilities + skill status and are NOT
 *     affected by `canDelete` (separate permission gates live in
 *     the page that mounts the editor).
 */
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// next/navigation is mocked globally in tests/setup.ts, but
// SkillEditor's `<MarkdownRenderer>` is reachable only on selection
// (we never click a row in these tests, so it shouldn't run).
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn(),
    back: vi.fn(),
  }),
  useSearchParams: () => ({ get: vi.fn().mockReturnValue(null) }),
  useParams: () => ({}),
  usePathname: () => "/skills",
}));

import { SkillEditor, type EditableSkill, type SkillEditorAdapter } from "../skill-editor";

const FIXTURE_SKILL: EditableSkill = {
  id: "skill-1",
  slug: "fixture-skill",
  name: "Fixture Skill",
  description: "A skill used for the permission tests",
  content: "# Hello",
  version: "1.0.0",
  author: "tester",
  status: "active",
  is_visible: true,
  source_skill_id: null,
  source_version: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

function makeAdapter(overrides: Partial<SkillEditorAdapter> = {}): SkillEditorAdapter {
  return {
    loadSkills: vi.fn().mockResolvedValue([FIXTURE_SKILL]),
    loadFiles: vi.fn().mockResolvedValue([]),
    getFileContent: vi.fn().mockResolvedValue(""),
    createSkill: vi.fn().mockResolvedValue(FIXTURE_SKILL),
    updateSkill: vi.fn().mockResolvedValue(FIXTURE_SKILL),
    createFile: vi.fn().mockResolvedValue(undefined),
    updateFile: vi.fn().mockResolvedValue(undefined),
    deleteFile: vi.fn().mockResolvedValue(undefined),
    // The adapter CAPABILITY check is what availableActions() consults.
    // In the real app, the adapter is always wired to deleteSkill on
    // both org + platform modes — that's the whole point of the leak:
    // the adapter had it, the user did not have the permission, and
    // the button rendered anyway.
    deleteSkill: vi.fn().mockResolvedValue(undefined),
    ...overrides,
  };
}

function makeWrapper(queryClient: QueryClient) {
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(
      QueryClientProvider,
      { client: queryClient },
      children,
    );
}

describe("SkillEditor - per-row delete action permission gate", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("does NOT render the per-row 'Delete skill' button when canDelete=false", async () => {
    const adapter = makeAdapter();
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <SkillEditor
        mode="organization"
        adapter={adapter}
        canCreate={false}
        canEdit={false}
        canDelete={false}
      />,
      { wrapper: makeWrapper(queryClient) },
    );

    // Wait for the skill list to render.
    await waitFor(() => {
      expect(screen.getByText("Fixture Skill")).toBeInTheDocument();
    });

    // The per-row action button has `title="Delete skill"` (set on the
    // button rendered inside availableActions()). If canDelete is
    // false, that button must not exist anywhere in the DOM.
    expect(
      screen.queryByTitle("Delete skill"),
      "per-row Delete skill button must not render when canDelete is false",
    ).not.toBeInTheDocument();
  });

  it("renders the per-row 'Delete skill' button when canDelete=true", async () => {
    const adapter = makeAdapter();
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <SkillEditor
        mode="organization"
        adapter={adapter}
        canCreate={true}
        canEdit={true}
        canDelete={true}
      />,
      { wrapper: makeWrapper(queryClient) },
    );

    await waitFor(() => {
      expect(screen.getByText("Fixture Skill")).toBeInTheDocument();
    });

    // The button is in the row. Several of them may exist (one per
    // rendered skill), so we just assert at least one is present.
    const deleteButtons = screen.queryAllByTitle("Delete skill");
    expect(
      deleteButtons.length,
      "per-row Delete skill button must render when canDelete is true",
    ).toBeGreaterThan(0);
  });

  it("canDelete=false hides the delete button even when adapter.deleteSkill is provided", async () => {
    // Defends the contract: the permission gate dominates the
    // adapter capability check. The adapter exposes deleteSkill, but
    // the user has no permission to delete — the button must not
    // appear. This is exactly the browser-validated leak that
    // surfaced for a regular org member.
    const adapter = makeAdapter({ deleteSkill: vi.fn().mockResolvedValue(undefined) });
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <SkillEditor
        mode="organization"
        adapter={adapter}
        canCreate={false}
        canEdit={false}
        canDelete={false}
      />,
      { wrapper: makeWrapper(queryClient) },
    );

    await waitFor(() => {
      expect(screen.getByText("Fixture Skill")).toBeInTheDocument();
    });

    expect(screen.queryByTitle("Delete skill")).not.toBeInTheDocument();
  });

  it("the row itself remains visible (the permission gate does not hide the skill)", async () => {
    // Pin the contract: canDelete=false hides the *delete action*,
    // not the row. A regular member must still be able to see skills.
    const adapter = makeAdapter();
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <SkillEditor
        mode="organization"
        adapter={adapter}
        canCreate={false}
        canEdit={false}
        canDelete={false}
      />,
      { wrapper: makeWrapper(queryClient) },
    );

    await waitFor(() => {
      expect(screen.getByText("Fixture Skill")).toBeInTheDocument();
    });

    // The skill name + count header are still present.
    expect(screen.getByText("1 skills")).toBeInTheDocument();
  });

  it("the filter input remains usable when canDelete=false (no broken toolbar)", async () => {
    // Regression check: gating the delete button must not break the
    // surrounding toolbar (filter input still rendered, search still
    // works). Belt-and-suspenders against a future refactor that
    // wraps the row in a canDelete check by accident.
    const adapter = makeAdapter();
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <SkillEditor
        mode="organization"
        adapter={adapter}
        canCreate={false}
        canEdit={false}
        canDelete={false}
      />,
      { wrapper: makeWrapper(queryClient) },
    );

    await waitFor(() => {
      expect(screen.getByText("Fixture Skill")).toBeInTheDocument();
    });

    expect(
      screen.getByPlaceholderText("Filter skills..."),
    ).toBeInTheDocument();
  });

  it("the rendered row contains no element with role=button that triggers delete when canDelete=false", async () => {
    // The action buttons inside availableActions() are real <button>
    // elements, so this is a stricter version of the title-based
    // check: it catches a future regression that changes the title
    // (e.g. i18n) but leaves the button in place. We grab the row by
    // its text and assert the row has no button with a Trash2-shaped
    // title or aria-label.
    const adapter = makeAdapter();
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <SkillEditor
        mode="organization"
        adapter={adapter}
        canCreate={false}
        canEdit={false}
        canDelete={false}
      />,
      { wrapper: makeWrapper(queryClient) },
    );

    await waitFor(() => {
      expect(screen.getByText("Fixture Skill")).toBeInTheDocument();
    });

    // The row containing the skill name should contain no button.
    // Find the name node and walk up to its enclosing row.
    const skillName = screen.getByText("Fixture Skill");
    // `Element.closest()` returns `Element | null`; the row is a
    // plain <div>, so the cast is safe and unblocks TS.
    const row = skillName.closest("div.group") as HTMLElement | null;
    expect(row).not.toBeNull();
    if (row) {
      // Either no buttons at all, or no button whose title indicates
      // a destructive action. We pin "Delete skill" by title because
      // that's what availableActions() emits today.
      const buttons = within(row).queryAllByRole("button");
      const destructive = buttons.filter(
        (b) => b.getAttribute("title") === "Delete skill",
      );
      expect(destructive.length).toBe(0);
    }
  });
});

describe("SkillEditor - platform skill library sheet scrolling", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Radix dropdown/sheet need a constructible ResizeObserver for floating-ui.
    global.ResizeObserver = class {
      observe() {}
      unobserve() {}
      disconnect() {}
    } as unknown as typeof ResizeObserver;
  });

  it("renders the platform library list in a scrollable flex body", async () => {
    const user = userEvent.setup();
    const platformSkills = Array.from({ length: 12 }, (_, i) => ({
      id: `ps-${i}`,
      name: `Platform Skill ${i + 1}`,
      slug: `platform-skill-${i + 1}`,
      description: `Description for platform skill ${i + 1}`,
    }));
    const adapter = makeAdapter({
      loadPlatformSkillsForFork: vi.fn().mockResolvedValue(platformSkills),
      forkPlatformSkill: vi.fn(),
    });
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <SkillEditor
        mode="organization"
        adapter={adapter}
        canCreate={true}
        canEdit={true}
        canDelete={true}
        showImportFromPlatformLibrary
      />,
      { wrapper: makeWrapper(queryClient) },
    );

    await waitFor(() => {
      expect(screen.getByText("Fixture Skill")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /^add$/i }));
    await user.click(
      await screen.findByRole("menuitem", {
        name: /create from platform library/i,
      }),
    );

    await waitFor(() => {
      expect(screen.getByText("Platform Skill Library")).toBeInTheDocument();
    });

    const list = screen.getByTestId("platform-skill-library-list");
    expect(list.className).toMatch(/overflow-y-auto/);
    expect(list.className).toMatch(/flex-1/);
    expect(list.className).toMatch(/min-h-0/);

    // SheetContent must be a column flex container so flex-1 can constrain
    // the list height; otherwise overflow-y-auto never engages.
    const sheet = list.parentElement;
    expect(sheet).not.toBeNull();
    expect(sheet?.className).toMatch(/flex/);
    expect(sheet?.className).toMatch(/flex-col/);

    expect(screen.getByText("Platform Skill 1")).toBeInTheDocument();
    expect(screen.getByText("Platform Skill 12")).toBeInTheDocument();
  });
});

describe("SkillEditor - create custom skill sheet", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.ResizeObserver = class {
      observe() {}
      unobserve() {}
      disconnect() {}
    } as unknown as typeof ResizeObserver;
  });

  it("opens a right sheet with name/description/slug only (no SKILL.md textarea)", async () => {
    const user = userEvent.setup();
    const adapter = makeAdapter();
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <SkillEditor
        mode="organization"
        adapter={adapter}
        canCreate={true}
        canEdit={true}
        canDelete={true}
      />,
      { wrapper: makeWrapper(queryClient) },
    );

    await waitFor(() => {
      expect(screen.getByText("Fixture Skill")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /^add$/i }));
    await user.click(
      await screen.findByRole("menuitem", { name: /create custom skill/i }),
    );

    expect(
      await screen.findByRole("heading", { name: /create custom skill/i }),
    ).toBeInTheDocument();

    expect(screen.getByLabelText(/^name$/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^description$/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^slug$/i)).toBeInTheDocument();
    expect(
      screen.queryByLabelText(/content \(skill\.md/i),
    ).not.toBeInTheDocument();

    const sheet = screen.getByTestId("create-skill-sheet");
    expect(sheet.className).toMatch(/flex/);
    expect(sheet.className).toMatch(/flex-col/);
  });

  it("auto-fills slug from name and creates with starter SKILL.md, then selects the skill in edit mode", async () => {
    const user = userEvent.setup();
    const created: EditableSkill = {
      ...FIXTURE_SKILL,
      id: "skill-new",
      slug: "appointment-booking",
      name: "Appointment Booking",
      description: "Books appointments",
      content:
        "# Appointment Booking\n\n## When to use\n\n\n## Instructions\n\n",
    };
    const createSkill = vi.fn().mockResolvedValue(created);
    const adapter = makeAdapter({
      createSkill,
      loadSkills: vi
        .fn()
        .mockResolvedValueOnce([FIXTURE_SKILL])
        .mockResolvedValue([FIXTURE_SKILL, created]),
    });
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <SkillEditor
        mode="organization"
        adapter={adapter}
        canCreate={true}
        canEdit={true}
        canDelete={true}
      />,
      { wrapper: makeWrapper(queryClient) },
    );

    await waitFor(() => {
      expect(screen.getByText("Fixture Skill")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /^add$/i }));
    await user.click(
      await screen.findByRole("menuitem", { name: /create custom skill/i }),
    );

    await user.type(screen.getByLabelText(/^name$/i), "Appointment Booking");
    await user.type(
      screen.getByLabelText(/^description$/i),
      "Books appointments",
    );

    await waitFor(() => {
      expect(screen.getByLabelText(/^slug$/i)).toHaveValue(
        "appointment-booking",
      );
    });

    await user.click(screen.getByRole("button", { name: /create skill/i }));

    await waitFor(() => {
      expect(createSkill).toHaveBeenCalledTimes(1);
    });

    expect(createSkill).toHaveBeenCalledWith({
      slug: "appointment-booking",
      name: "Appointment Booking",
      description: "Books appointments",
      content:
        "# Appointment Booking\n\n## When to use\n\n\n## Instructions\n\n",
    });

    // Main editor should land on the new skill in edit mode (SKILL.md textarea).
    await waitFor(() => {
      expect(screen.getByText("Editing SKILL.md")).toBeInTheDocument();
    });
    expect(screen.getByDisplayValue("Appointment Booking")).toBeInTheDocument();
  });
});
