/**
 * Service for managing organization skills, platform skills, and agent skill assignments.
 *
 * Skills are reusable knowledge/procedure packages (markdown) that can be
 * assigned to agents via progressive disclosure.
 *
 * Platform skills are immutable templates that org admins can fork into their
 * own editable libraries. Forked skills can optionally be refreshed to receive
 * updates from the platform source.
 */

import { apiClient } from "@/lib/api/client";
import type {
  OrganizationSkill,
  OrganizationSkillCreate,
  OrganizationSkillUpdate,
  AgentSkill,
  SkillFile,
  SkillFileSummary,
  SkillImportResult,
  PlatformSkill,
  PlatformSkillCreate,
  PlatformSkillUpdate,
  PlatformSkillFile,
  PlatformSkillFileCreate,
  PlatformSkillImportResult,
  PlatformSkillFileSummary,
  PlatformSkillStatus,
  PlatformSkillSummary,
  SkillForkRequest,
  SkillRefreshRequest,
} from "@/types/skill";

class SkillService {
  // ═══════════════════════════════════════════════════════════════════════════════
  // Organization Skill Library
  // ═══════════════════════════════════════════════════════════════════════════════

  async getOrganizationSkills(orgId: string): Promise<OrganizationSkill[]> {
    const response = await apiClient.get<OrganizationSkill[]>(
      `/api/v1/organizations/${orgId}/skills`,
    );
    return response.data;
  }

  async createSkill(
    orgId: string,
    data: OrganizationSkillCreate,
  ): Promise<OrganizationSkill> {
    const response = await apiClient.post<OrganizationSkill>(
      `/api/v1/organizations/${orgId}/skills`,
      data,
    );
    return response.data;
  }

  async updateSkill(
    orgId: string,
    skillId: string,
    data: OrganizationSkillUpdate,
  ): Promise<OrganizationSkill> {
    const response = await apiClient.put<OrganizationSkill>(
      `/api/v1/organizations/${orgId}/skills/${skillId}`,
      data,
    );
    return response.data;
  }

  async deleteSkill(orgId: string, skillId: string): Promise<void> {
    await apiClient.delete(`/api/v1/organizations/${orgId}/skills/${skillId}`);
  }

  // ═══════════════════════════════════════════════════════════════════════════════
  // Platform Skills (Read-only for org users, CRUD for platform admins)
  // ═══════════════════════════════════════════════════════════════════════════════

  /**
   * List platform skill templates filtered by status.
   *
   * @param statuses - List of statuses to include. Defaults to `["active"]`
   *   so org admins browsing/forking only see forkable skills. Platform
   *   admins can pass e.g. `["active", "deprecated"]` to also see
   *   deprecated skills, or `["deleted"]` to view the trash bin.
   *
   *   The query is built with one `statuses=` param per value
   *   (`?statuses=active&statuses=deprecated`), which FastAPI parses into
   *   the corresponding `List[PlatformSkillStatus]` server-side.
   *
   *   Server-side enforces admin-only access for any non-active filter.
   */
  async listPlatformSkills(
    statuses: PlatformSkillStatus[] = ["active"],
  ): Promise<PlatformSkillSummary[]> {
    const params = new URLSearchParams();
    for (const s of statuses) {
      params.append("statuses", s);
    }
    const qs = params.toString();
    const response = await apiClient.get<PlatformSkillSummary[]>(
      `/api/v1/platform/skills${qs ? `?${qs}` : ""}`,
    );
    return response.data;
  }

  async getPlatformSkill(skillId: string): Promise<PlatformSkill> {
    const response = await apiClient.get<PlatformSkill>(
      `/api/v1/platform/skills/${skillId}`,
    );
    return response.data;
  }

  /** Create a new platform skill template (platform admin only). */
  async createPlatformSkill(
    data: PlatformSkillCreate,
  ): Promise<PlatformSkill> {
    const response = await apiClient.post<PlatformSkill>(
      `/api/v1/platform/skills`,
      data,
    );
    return response.data;
  }

  /** Update a platform skill (platform admin only). Bumps version automatically. */
  async updatePlatformSkill(
    skillId: string,
    data: PlatformSkillUpdate,
  ): Promise<PlatformSkill> {
    const response = await apiClient.put<PlatformSkill>(
      `/api/v1/platform/skills/${skillId}`,
      data,
    );
    return response.data;
  }

  /**
   * Soft-delete a platform skill (status → DELETED). Hidden from
   * forking/browsing; restorable via restorePlatformSkill().
   * Existing org forks keep working. (Platform admin only.)
   *
   * Throws if the skill is already deleted (no-op double-delete).
   */
  async deletePlatformSkill(skillId: string): Promise<void> {
    await apiClient.delete(`/api/v1/platform/skills/${skillId}`);
  }

  /** Restore a soft-deleted platform skill (status: DELETED → ACTIVE). */
  async restorePlatformSkill(skillId: string): Promise<PlatformSkill> {
    const response = await apiClient.post<PlatformSkill>(
      `/api/v1/platform/skills/${skillId}/restore`,
    );
    return response.data;
  }

  /** Deprecate a platform skill (status: ACTIVE → DEPRECATED). */
  async deprecatePlatformSkill(skillId: string): Promise<PlatformSkill> {
    const response = await apiClient.post<PlatformSkill>(
      `/api/v1/platform/skills/${skillId}/deprecate`,
    );
    return response.data;
  }

  /** Reactivate a deprecated platform skill (status: DEPRECATED → ACTIVE). */
  async reactivatePlatformSkill(skillId: string): Promise<PlatformSkill> {
    const response = await apiClient.post<PlatformSkill>(
      `/api/v1/platform/skills/${skillId}/reactivate`,
    );
    return response.data;
  }

  /**
   * Import skill(s) from a GitHub / skills.sh URL as platform skill templates.
   * Platform admin only. Imported skills become platform-level templates.
   */
  async importPlatformSkill(url: string): Promise<PlatformSkillImportResult[]> {
    const response = await apiClient.post<PlatformSkillImportResult[]>(
      `/api/v1/platform/skills/import`,
      { url },
    );
    return response.data;
  }

  // ─── Platform skill reference files (platform admin only) ───

  async listPlatformSkillFiles(
    skillId: string,
  ): Promise<PlatformSkillFileSummary[]> {
    const response = await apiClient.get<PlatformSkillFileSummary[]>(
      `/api/v1/platform/skills/${skillId}/files`,
    );
    return response.data;
  }

  async getPlatformSkillFile(
    skillId: string,
    fileId: string,
  ): Promise<PlatformSkillFile> {
    const response = await apiClient.get<PlatformSkillFile>(
      `/api/v1/platform/skills/${skillId}/files/${fileId}`,
    );
    return response.data;
  }

  async createPlatformSkillFile(
    skillId: string,
    data: PlatformSkillFileCreate,
  ): Promise<PlatformSkillFile> {
    const response = await apiClient.post<PlatformSkillFile>(
      `/api/v1/platform/skills/${skillId}/files`,
      data,
    );
    return response.data;
  }

  async updatePlatformSkillFile(
    skillId: string,
    fileId: string,
    data: PlatformSkillFileCreate,
  ): Promise<PlatformSkillFile> {
    const response = await apiClient.put<PlatformSkillFile>(
      `/api/v1/platform/skills/${skillId}/files/${fileId}`,
      data,
    );
    return response.data;
  }

  async deletePlatformSkillFile(
    skillId: string,
    fileId: string,
  ): Promise<void> {
    await apiClient.delete(`/api/v1/platform/skills/${skillId}/files/${fileId}`);
  }

  // ═══════════════════════════════════════════════════════════════════════════════
  // Fork / Refresh (Org-level)
  // ═══════════════════════════════════════════════════════════════════════════════

  async forkPlatformSkill(
    orgId: string,
    request: SkillForkRequest,
  ): Promise<OrganizationSkill> {
    const response = await apiClient.post<OrganizationSkill>(
      `/api/v1/organizations/${orgId}/skills/fork`,
      request,
    );
    return response.data;
  }

  async checkUpdateAvailable(
    orgId: string,
    skillId: string,
  ): Promise<{
    update_available: boolean;
    latest_version: string;
    current_version: string | null;
  }> {
    const response = await apiClient.get<{
      update_available: boolean;
      latest_version: string;
      current_version: string | null;
    }>(
      `/api/v1/organizations/${orgId}/skills/${skillId}/update-check`,
    );
    return response.data;
  }

  async refreshSkill(
    orgId: string,
    skillId: string,
    request: SkillRefreshRequest,
  ): Promise<OrganizationSkill> {
    const response = await apiClient.post<OrganizationSkill>(
      `/api/v1/organizations/${orgId}/skills/${skillId}/refresh`,
      request,
    );
    return response.data;
  }

  // ═══════════════════════════════════════════════════════════════════════════════
  // Agent Skill Assignments
  // ═══════════════════════════════════════════════════════════════════════════════

  async getAgentSkills(agentId: string): Promise<AgentSkill[]> {
    const response = await apiClient.get<AgentSkill[]>(
      `/api/v1/agents/${agentId}/skills`,
    );
    return response.data;
  }

  async assignSkill(agentId: string, skillId: string): Promise<void> {
    await apiClient.post(`/api/v1/agents/${agentId}/skills`, {
      skill_id: skillId,
    });
  }

  async unassignSkill(agentId: string, skillId: string): Promise<void> {
    await apiClient.delete(`/api/v1/agents/${agentId}/skills/${skillId}`);
  }

  // ═══════════════════════════════════════════════════════════════════════════════
  // Skill Reference Files
  // ═══════════════════════════════════════════════════════════════════════════════

  async getSkillFiles(
    orgId: string,
    skillId: string,
  ): Promise<SkillFileSummary[]> {
    const response = await apiClient.get<SkillFileSummary[]>(
      `/api/v1/organizations/${orgId}/skills/${skillId}/files`,
    );
    return response.data;
  }

  async createSkillFile(
    orgId: string,
    skillId: string,
    data: { file_path: string; content: string; file_kind?: string },
  ): Promise<SkillFile> {
    const response = await apiClient.post<SkillFile>(
      `/api/v1/organizations/${orgId}/skills/${skillId}/files`,
      data,
    );
    return response.data;
  }

  async updateSkillFile(
    orgId: string,
    skillId: string,
    fileId: string,
    data: { file_path?: string; content?: string },
  ): Promise<SkillFile> {
    const response = await apiClient.put<SkillFile>(
      `/api/v1/organizations/${orgId}/skills/${skillId}/files/${fileId}`,
      data,
    );
    return response.data;
  }

  async deleteSkillFile(
    orgId: string,
    skillId: string,
    fileId: string,
  ): Promise<void> {
    await apiClient.delete(
      `/api/v1/organizations/${orgId}/skills/${skillId}/files/${fileId}`,
    );
  }

  async getAgentsUsingSkill(
    orgId: string,
    skillId: string,
  ): Promise<Array<{ id: string; name: string; is_active: boolean }>> {
    const response = await apiClient.get<
      Array<{ id: string; name: string; is_active: boolean }>
    >(`/api/v1/organizations/${orgId}/skills/${skillId}/agents`);
    return response.data;
  }

  async getSkillFileContent(
    orgId: string,
    slug: string,
    filePath: string,
  ): Promise<string> {
    const response = await apiClient.get<string>(
      `/api/v1/skills/${orgId}/${slug}/files/${filePath}`,
    );
    return response.data;
  }

  // ═══════════════════════════════════════════════════════════════════════════════
  // Import
  // ═══════════════════════════════════════════════════════════════════════════════

  async importSkill(
    orgId: string,
    url: string,
  ): Promise<SkillImportResult[]> {
    const response = await apiClient.post<SkillImportResult[]>(
      `/api/v1/organizations/${orgId}/skills/import`,
      { url },
    );
    return response.data;
  }
}

export const skillService = new SkillService();
