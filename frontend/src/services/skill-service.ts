/**
 * Service for managing organization skills and agent skill assignments.
 *
 * Skills are reusable knowledge/procedure packages (markdown) that can be
 * assigned to agents via progressive disclosure.
 */

import { apiClient } from "@/lib/api/client";
import type {
  OrganizationSkill,
  OrganizationSkillCreate,
  OrganizationSkillUpdate,
  AgentSkill,
} from "@/types/skill";

class SkillService {
  // --- Organization skill library ---

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

  async seedSkills(orgId: string): Promise<{ seeded: number }> {
    const response = await apiClient.post<{ seeded: number }>(
      `/api/v1/organizations/${orgId}/skills/seed`,
    );
    return response.data;
  }

  // --- Agent skill assignments ---

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
}

export const skillService = new SkillService();
