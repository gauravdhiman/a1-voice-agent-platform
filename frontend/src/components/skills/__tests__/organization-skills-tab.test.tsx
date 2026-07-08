/**
 * Tests for <OrganizationSkillsTab>'s `basePath` contract.
 *
 * Background — bug #35: clicking a skill in the left panel of the top-level
 * /skills page caused a page flash because the editor's `syncUrl` callback
 * always navigated to `/organization?...`, even when the editor was rendered
 * from the `/skills` route. This is the regression test for that fix.
 *
 * Contract:
 *   - When `basePath` is not provided, the `syncUrl` callback must write to
 *     `/organization?...` (the legacy default — used when the tab is rendered
 *     inside the org page).
 *   - When `basePath` is provided (e.g. `/skills`), the `syncUrl` callback
 *     must write to that base path instead, so the editor stays on whichever
 *     page is rendering it.
 *   - In both cases, the URL written must include the org_id, the skill slug,
 *     and (when present) the file path.
 */
import React from "react";
import { render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mockReplace = vi.fn();
const mockPush = vi.fn();
const mockSearchParamsGet = vi.fn();
let mockSearchParams: URLSearchParams = new URLSearchParams();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
    replace: mockReplace,
    prefetch: vi.fn(),
    back: vi.fn(),
  }),
  useSearchParams: () => {
    // The component calls `.get(key)` on this. We back it with our
    // own URLSearchParams so we can seed initial-selection params.
    return {
      get: (key: string) => mockSearchParamsGet(key) ?? null,
    };
  },
  usePathname: () => "/skills",
}));

// Capture the `syncUrl` prop the parent passes to <SkillEditor> so the test
// can invoke it directly. We render a marker in place of the real editor.
let capturedSyncUrl:
  | ((state: { slug: string | null; filePath: string | null }) => void)
  | null
  = null;

vi.mock("@/components/skills/skill-editor", () => ({
  SkillEditor: ({
    syncUrl,
  }: {
    syncUrl?: (state: { slug: string | null; filePath: string | null }) => void;
  }) => {
    capturedSyncUrl = syncUrl ?? null;
    return <div data-testid="skill-editor-stub" />;
  },
}));

// Stub the skill service so the adapter can be created without a real network.
vi.mock("@/services/skill-service", () => ({
  skillService: {
    getOrganizationSkills: vi.fn().mockResolvedValue([]),
    getSkillFiles: vi.fn().mockResolvedValue([]),
    getSkillFileContent: vi.fn().mockResolvedValue(""),
    createSkill: vi.fn(),
    updateSkill: vi.fn(),
    createSkillFile: vi.fn(),
    updateSkillFile: vi.fn(),
    deleteSkillFile: vi.fn(),
    deleteSkill: vi.fn(),
    getAgentsUsingSkill: vi.fn().mockResolvedValue([]),
    importSkill: vi.fn().mockResolvedValue([]),
    checkUpdateAvailable: vi.fn(),
    refreshSkill: vi.fn(),
    forkPlatformSkill: vi.fn(),
    listPlatformSkills: vi.fn().mockResolvedValue([]),
  },
}));

import { OrganizationSkillsTab } from "../organization-skills-tab";

describe("<OrganizationSkillsTab> basePath contract (bug #35)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    capturedSyncUrl = null;
    mockSearchParams = new URLSearchParams();
    mockSearchParamsGet.mockImplementation(
      (key: string) => mockSearchParams.get(key) ?? null,
    );
  });

  afterEach(() => {
    mockSearchParams = new URLSearchParams();
  });

  it("defaults syncUrl to /organization?... when basePath is not provided", () => {
    render(
      <OrganizationSkillsTab
        orgId="org-1"
        canCreate={true}
        canEdit={true}
      />,
    );

    expect(capturedSyncUrl).not.toBeNull();
    capturedSyncUrl!({ slug: "foo", filePath: null });

    expect(mockReplace).toHaveBeenCalledTimes(1);
    const url = mockReplace.mock.calls[0][0] as string;
    expect(url.startsWith("/organization?")).toBe(true);
    expect(url).toContain("org_id=org-1");
    expect(url).toContain("tab=skills");
    expect(url).toContain("skill=foo");
  });

  it("writes to the provided basePath instead of /organization (regression for #35)", () => {
    render(
      <OrganizationSkillsTab
        orgId="org-1"
        canCreate={true}
        canEdit={true}
        basePath="/skills"
      />,
    );

    expect(capturedSyncUrl).not.toBeNull();
    capturedSyncUrl!({ slug: "foo", filePath: null });

    expect(mockReplace).toHaveBeenCalledTimes(1);
    const url = mockReplace.mock.calls[0][0] as string;
    // The whole point of the fix: when the editor is on /skills, it must
    // stay on /skills. It must NOT navigate to /organization.
    expect(url.startsWith("/skills?")).toBe(true);
    expect(url.startsWith("/organization?")).toBe(false);
    expect(url).toContain("org_id=org-1");
    expect(url).toContain("skill=foo");
  });

  it("includes file path in the URL when filePath is set", () => {
    render(
      <OrganizationSkillsTab
        orgId="org-1"
        canCreate={true}
        canEdit={true}
        basePath="/skills"
      />,
    );

    capturedSyncUrl!({ slug: "foo", filePath: "reference/menu.md" });

    const url = mockReplace.mock.calls[0][0] as string;
    expect(url).toContain("skill=foo");
    expect(url).toContain("file=");
  });

  it("omits the skill param when slug is null (e.g. selection cleared)", () => {
    render(
      <OrganizationSkillsTab
        orgId="org-1"
        canCreate={true}
        canEdit={true}
        basePath="/skills"
      />,
    );

    capturedSyncUrl!({ slug: null, filePath: null });

    const url = mockReplace.mock.calls[0][0] as string;
    expect(url.startsWith("/skills?")).toBe(true);
    expect(url).not.toContain("skill=");
  });
});
