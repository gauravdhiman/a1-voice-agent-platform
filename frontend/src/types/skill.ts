/**
 * Skill type definitions for the skills system.
 *
 * Skills are reusable knowledge/procedure packages (markdown) that can be
 * assigned to agents. They use progressive disclosure — only metadata is
 * in the system prompt; full content loads on-demand via tool call.
 */

export interface OrganizationSkill {
  id: string;
  organization_id: string;
  slug: string;
  name: string;
  description: string | null;
  content: string;
  category: "custom";
  is_active: boolean;
  version: string | null;
  author: string | null;
  content_hash: string | null;
  is_visible: boolean;
  source_skill_id: string | null;
  source_version: string | null;
  created_at: string;
  updated_at: string;
}

export interface PlatformSkillSummary {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  version: string;
  /** Active (visible/forkable) vs deprecated (hidden). Always true for non-admin lists. */
  is_active: boolean;
}

/** Payload for creating a new platform skill template (platform admin only). */
export interface PlatformSkillCreate {
  slug: string;
  name: string;
  description?: string | null;
  content: string;
  author?: string | null;
}

/** Payload for updating a platform skill (platform admin only). Bumps version. */
export interface PlatformSkillUpdate {
  name?: string;
  description?: string | null;
  content?: string;
  is_active?: boolean;
}

/** Full platform skill reference file (with content). */
export interface PlatformSkillFile {
  id: string;
  skill_id: string;
  file_path: string;
  content: string;
  file_kind: "reference" | "script" | "asset" | "other";
  content_hash: string | null;
  created_at: string;
  updated_at: string;
}

/** Payload for creating/updating a platform skill reference file. */
export interface PlatformSkillFileCreate {
  file_path: string;
  content: string;
  file_kind?: "reference" | "script" | "asset" | "other";
}

export interface PlatformSkill {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  content: string;
  version: string;
  author: string | null;
  content_hash: string;
  is_active: boolean;
  files?: PlatformSkillFileSummary[];
  created_at: string;
  updated_at: string;
}

export interface PlatformSkillFileSummary {
  id: string;
  skill_id: string;
  file_path: string;
  file_kind: string;
  content_hash: string | null;
}

export interface SkillForkRequest {
  platform_skill_id: string;
  custom_name?: string;
  custom_slug?: string;
}

export interface SkillRefreshRequest {
  confirm_overwrite: boolean;
}

export interface OrganizationSkillCreate {
  organization_id: string;
  slug: string;
  name: string;
  description?: string | null;
  content: string;
  category?: string;
}

export interface OrganizationSkillUpdate {
  name?: string;
  description?: string | null;
  content?: string;
  is_active?: boolean;
  is_visible?: boolean;
}

export interface AgentSkill {
  id: string;
  agent_id: string;
  skill_id: string;
  skill: OrganizationSkill;
  is_active: boolean;
  created_at: string;
}

export interface SkillFile {
  id: string;
  skill_id: string;
  file_path: string;
  content: string;
  file_kind: "reference" | "script" | "asset" | "other";
  content_hash: string | null;
  created_at: string;
  updated_at: string;
}

export interface SkillFileSummary {
  id: string;
  file_path: string;
  file_kind: string;
  content_hash: string | null;
}

export interface SkillImportResult {
  skill: OrganizationSkill;
  files_imported: number;
  source_url: string;
}

/** Result of importing an external skill as a platform skill template. */
export interface PlatformSkillImportResult {
  skill: PlatformSkill;
  files_imported: number;
  source_url: string;
}
