"use client";

/**
 * Platform Skills management page (platform admin only).
 *
 * Thin wrapper around the shared `<SkillEditor>` (mode="platform"). Platform
 * skills are built-in templates available to all organizations via forking.
 * The editor delegates to the platform-skill service via an adapter; the
 * backend independently enforces platform_admin on every write endpoint.
 *
 * Out of scope here (separate upcoming item): soft-delete (`is_deleted`),
 * show-deleted filter, and restore. The page therefore ships without a
 * delete/hide control — see TODO below.
 *
 * @example
 * ```tsx
 * <PlatformSkillsPage />
 * ```
 */

import { useCallback, useMemo } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { useAuth } from "@/contexts/auth-context";
import { AccessDenied } from "@/components/ui/access-denied";
import { SkillEditor, type SkillEditorAdapter } from "@/components/skills/skill-editor";
import { skillService } from "@/services/skill-service";
import type {
  EditableSkill, // re-exported via component? no — defined in component
} from "@/components/skills/skill-editor";
import type { PlatformSkillFile } from "@/types/skill";

export default function PlatformSkillsPage() {
  const { user } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();

  // Frontend authz gate. Backend enforces the same independently.
  if (!user?.hasRole("platform_admin")) {
    return (
      <AccessDenied
        title="Access Denied"
        description="You do not have permission to access this page. Only platform administrators can manage platform skills."
        redirectPath="/dashboard"
      />
    );
  }

  // URL sync for platform skills: /platform/skills?skill=<slug>&file=<path>
  const syncUrl = useCallback(
    (state: { slug: string | null; filePath: string | null }) => {
      const params = new URLSearchParams();
      if (state.slug) params.set("skill", state.slug);
      if (state.filePath) params.set("file", state.filePath);
      const qs = params.toString();
      router.replace(`/platform/skills${qs ? `?${qs}` : ""}`, { scroll: false });
    },
    [router],
  );

  const initialSelection = useMemo(
    () => ({
      slug: searchParams.get("skill") ?? undefined,
      filePath: searchParams.get("file"),
    }),
    [searchParams],
  );

  // Adapter: maps the shared editor to platform-skill service calls.
  // TODO: [Platform Skills] Add soft-delete (is_deleted) + show-deleted filter +
  //   restore as a separate item. Until then, no delete/hide control is exposed
  //   here (the existing backend deprecate endpoint remains available via API).
  const adapter: SkillEditorAdapter = useMemo<SkillEditorAdapter>(() => ({
    loadSkills: async () => {
      // Platform admins see all skills incl. deprecated (is_active=false).
      const list = await skillService.listPlatformSkills(true);
      return list.map((s) => ({
        id: s.id,
        slug: s.slug,
        name: s.name,
        description: s.description,
        content: "", // loaded on demand via getPlatformSkill when editing
        version: s.version,
        is_active: s.is_active,
        created_at: "",
        updated_at: "",
      }));
    },
    loadFiles: async (skillId) => {
      const files = await skillService.listPlatformSkillFiles(skillId);
      return files.map((f) => ({ id: f.id, file_path: f.file_path, file_kind: f.file_kind }));
    },
    getFileContent: async (skill, file) => {
      const full: PlatformSkillFile = await skillService.getPlatformSkillFile(skill.id, file.id);
      return full.content;
    },
    // Platform list returns summaries without content; hydrate on selection.
    hydrateSkill: async (skill) => {
      const full = await skillService.getPlatformSkill(skill.id);
      return toEditable(full);
    },
    createSkill: async (input) => {
      const created = await skillService.createPlatformSkill({
        slug: input.slug,
        name: input.name,
        description: input.description ?? null,
        content: input.content,
      });
      return toEditable(created);
    },
    updateSkill: async (skillId, patch) => {
      // Fetch current content if not editing content (the editor always sends content
      // when editing; for visibility/other patches we'd need current content, but
      // platform mode has no visibility toggle, so patch always carries content here).
      const full = await skillService.getPlatformSkill(skillId);
      const updated = await skillService.updatePlatformSkill(skillId, {
        name: patch.name ?? full.name,
        description: patch.description ?? full.description,
        content: patch.content ?? full.content,
      });
      return toEditable(updated);
    },
    createFile: async (skillId, input) => {
      await skillService.createPlatformSkillFile(skillId, {
        file_path: input.file_path,
        content: input.content,
        file_kind: input.file_kind as "reference" | "script" | "asset" | "other",
      });
    },
    updateFile: async (skillId, file, input) => {
      await skillService.updatePlatformSkillFile(skillId, file.id, {
        file_path: input.file_path,
        content: input.content,
        file_kind: input.file_kind as "reference" | "script" | "asset" | "other",
      });
    },
    deleteFile: async () => {
      // Not exposed in the platform UI yet; kept for adapter completeness.
    },
    importFromUrl: async (url) => {
      const results = await skillService.importPlatformSkill(url);
      return results.map((r) => toEditable(r.skill));
    },
  }), []);

  return (
    <div className="space-y-6 h-[calc(100vh-12rem)]">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">Platform Skills</h1>
        <p className="text-muted-foreground mt-1">
          Manage built-in skill templates available to all organizations. Edit a skill in the right
          pane, add reference files, or import from a URL.
        </p>
      </div>
      <SkillEditor
        mode="platform"
        adapter={adapter}
        canCreate
        canEdit
        syncUrl={syncUrl}
        initialSelection={initialSelection}
        emptyHint="Select a skill to view its content"
      />
    </div>
  );
}

/** Map a full PlatformSkill to the editor's normalized EditableSkill. */
function toEditable(s: {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  content: string;
  version: string;
  author?: string | null;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
}): EditableSkill {
  return {
    id: s.id,
    slug: s.slug,
    name: s.name,
    description: s.description,
    content: s.content,
    version: s.version,
    author: s.author ?? null,
    is_active: s.is_active ?? true,
    created_at: s.created_at ?? "",
    updated_at: s.updated_at ?? "",
  };
}
