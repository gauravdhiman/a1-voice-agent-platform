"use client";

/**
 * Organization-level skills tab.
 *
 * Thin wrapper around the shared `<SkillEditor>` (mode="organization") with an
 * adapter that maps the editor to the organization-skill service calls. This
 * replaces the skills UI that used to be embedded in the organization page, so
 * org and platform skills now share one editor implementation.
 *
 * Org-specific capabilities (kept via feature flags): Platform/Custom source
 * badge, library visibility (is_visible) toggle, fork-from-platform-library,
 * refresh forked skills, and hard delete with an agents-using pre-check.
 *
 * @example
 * ```tsx
 * <TabsContent value="skills">
 *   <OrganizationSkillsTab orgId={orgId} canCreate={isOrgAdmin || isPlatformAdmin} canEdit={isOrgAdmin || isPlatformAdmin} />
 * </TabsContent>
 * ```
 */

import { useCallback, useMemo } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import {
  SkillEditor,
  type EditableSkill,
  type SkillEditorAdapter,
} from "@/components/skills/skill-editor";
import { skillService } from "@/services/skill-service";
import type { OrganizationSkill } from "@/types/skill";

interface OrganizationSkillsTabProps {
  orgId: string;
  canCreate: boolean;
  canEdit: boolean;
}

/** Map an OrganizationSkill to the editor's normalized EditableSkill. */
function toEditable(s: OrganizationSkill): EditableSkill {
  return {
    id: s.id,
    slug: s.slug,
    name: s.name,
    description: s.description,
    content: s.content,
    version: s.version,
    author: s.author,
    is_visible: s.is_visible,
    source_skill_id: s.source_skill_id,
    source_version: s.source_version,
    created_at: s.created_at,
    updated_at: s.updated_at,
  };
}

export function OrganizationSkillsTab({ orgId, canCreate, canEdit }: OrganizationSkillsTabProps) {
  const router = useRouter();
  const searchParams = useSearchParams();

  // URL sync: /organization?org_id=…&tab=skills&skill=<slug>&file=<path>
  const syncUrl = useCallback(
    (state: { slug: string | null; filePath: string | null }) => {
      const params = new URLSearchParams();
      params.set("org_id", orgId);
      params.set("tab", "skills");
      if (state.slug) params.set("skill", state.slug);
      if (state.filePath) params.set("file", state.filePath);
      router.replace(`/organization?${params.toString()}`, { scroll: false });
    },
    [orgId, router],
  );

  const initialSelection = useMemo(
    () => ({
      slug: searchParams.get("skill") ?? undefined,
      filePath: searchParams.get("file"),
    }),
    [searchParams],
  );

  const adapter: SkillEditorAdapter = useMemo<SkillEditorAdapter>(() => ({
    loadSkills: async () => {
      const skills = await skillService.getOrganizationSkills(orgId);
      return skills.map(toEditable);
    },
    loadFiles: async (skillId) => {
      const files = await skillService.getSkillFiles(orgId, skillId);
      return files.map((f) => ({ id: f.id, file_path: f.file_path, file_kind: f.file_kind }));
    },
    getFileContent: async (skill, file) => {
      return await skillService.getSkillFileContent(orgId, skill.slug, file.file_path);
    },
    createSkill: async (input) => {
      const created = await skillService.createSkill(orgId, {
        organization_id: orgId,
        slug: input.slug,
        name: input.name,
        description: input.description ?? null,
        content: input.content,
      });
      return toEditable(created);
    },
    updateSkill: async (skillId, patch) => {
      const updated = await skillService.updateSkill(orgId, skillId, {
        name: patch.name,
        description: patch.description,
        content: patch.content,
        is_visible: patch.is_visible,
      });
      return toEditable(updated);
    },
    createFile: async (skillId, input) => {
      await skillService.createSkillFile(orgId, skillId, {
        file_path: input.file_path,
        content: input.content,
        file_kind: input.file_kind,
      });
    },
    updateFile: async (skillId, file, input) => {
      await skillService.updateSkillFile(orgId, skillId, file.id, {
        file_path: input.file_path,
        content: input.content,
      });
    },
    deleteFile: async (skillId, file) => {
      await skillService.deleteSkillFile(orgId, skillId, file.id);
    },
    deleteSkill: async (skillId) => {
      await skillService.deleteSkill(orgId, skillId);
    },
    getAgentsUsingSkill: async (skillId) => {
      return await skillService.getAgentsUsingSkill(orgId, skillId);
    },
    importFromUrl: async (url) => {
      const results = await skillService.importSkill(orgId, url);
      return results.map((r) => toEditable(r.skill));
    },
    checkUpdate: async (skillId) => {
      return await skillService.checkUpdateAvailable(orgId, skillId);
    },
    refresh: async (skillId) => {
      const refreshed = await skillService.refreshSkill(orgId, skillId, { confirm_overwrite: true });
      return toEditable(refreshed);
    },
    forkPlatformSkill: async (platformSkillId) => {
      const forked = await skillService.forkPlatformSkill(orgId, { platform_skill_id: platformSkillId });
      return toEditable(forked);
    },
    loadPlatformSkillsForFork: async () => {
      const list = await skillService.listPlatformSkills();
      return list.map((s) => ({ id: s.id, name: s.name, slug: s.slug, description: s.description }));
    },
  }), [orgId]);

  return (
    <div className="h-[calc(100vh-180px)] overflow-hidden">
      <SkillEditor
        mode="organization"
        adapter={adapter}
        canCreate={canCreate}
        canEdit={canEdit}
        canDelete={canCreate}
        showSourceBadge
        showVisibilityToggle
        showRefresh
        showImportFromPlatformLibrary
        syncUrl={syncUrl}
        initialSelection={initialSelection}
        emptyHint="Select a skill to view its content"
      />
    </div>
  );
}
