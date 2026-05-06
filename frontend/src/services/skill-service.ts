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

  async listPlatformSkills(): Promise<PlatformSkillSummary[]> {
    const response = await apiClient.get<PlatformSkillSummary[]>(
      `/api/v1/platform/skills`,
    );
    return response.data;
  }

  async getPlatformSkill(skillId: string): Promise<PlatformSkill> {
    const response = await apiClient.get<PlatformSkill>(
      `/api/v1/platform/skills/${skillId}`,
    );
    return response.data;
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
