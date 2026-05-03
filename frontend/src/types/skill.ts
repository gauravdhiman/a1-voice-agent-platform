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
  category: "built_in" | "custom";
  is_active: boolean;
  version: string | null;
  author: string | null;
  content_hash: string | null;
  source_url: string | null;
  source_ref: string | null;
  created_at: string;
  updated_at: string;
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
