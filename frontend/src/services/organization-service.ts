// services/organization-service.ts
import { apiClient } from "@/lib/api/client";

// Import types from centralized location
import type {
  Organization,
  OrganizationCreate,
  PlatformOrganizationCreate,
  OrganizationUpdate,
  Invitation,
  InvitationRole,
  WebsiteBusinessContextDraft,
} from "@/types/organization";
import type { Member } from "@/types/user";

// Organization Service class
class OrganizationService {
  private baseUrl = "/api/v1/organizations";

  // Create organization for current user using the self endpoint
  async createSelfOrganization(
    orgData: OrganizationCreate,
  ): Promise<Organization> {
    const response = await apiClient.post<Organization>(
      `${this.baseUrl}/self`,
      orgData,
    );
    return response.data;
  }

  // Get organizations for current user.
  // Trailing slash matches the FastAPI route (`GET /api/v1/organizations/`)
  // and avoids a 307 redirect that can emit http:// Location behind Cloud Run
  // if proxy headers are not trusted (Mixed Content in the browser).
  async getUserOrganizations(): Promise<Organization[]> {
    const response = await apiClient.get<Organization[]>(`${this.baseUrl}/`);
    return response.data;
  }

  // Alias for getUserOrganizations for consistency
  async getOrganizations(): Promise<Organization[]> {
    return this.getUserOrganizations();
  }

  // Create organization (platform admin only)
  async createOrganization(
    orgData: PlatformOrganizationCreate,
  ): Promise<Organization> {
    const response = await apiClient.post<Organization>(this.baseUrl, orgData);
    return response.data;
  }

  // Update organization
  async updateOrganization(
    orgId: string,
    orgData: OrganizationUpdate,
  ): Promise<Organization> {
    const response = await apiClient.patch<Organization>(
      `${this.baseUrl}/${orgId}`,
      orgData,
    );
    return response.data;
  }

  /**
   * Generate an unsaved business-context draft from a public website.
   *
   * @param orgId - Organization whose administrators initiated the request
   * @param website - Public HTTP(S) website URL to analyze
   * @returns Editable draft and the number of pages analyzed
   */
  async generateWebsiteBusinessContext(
    orgId: string,
    website: string,
  ): Promise<WebsiteBusinessContextDraft> {
    const response = await apiClient.post<WebsiteBusinessContextDraft>(
      `${this.baseUrl}/${orgId}/business-context-from-website`,
      { website },
    );
    return response.data;
  }

  // Delete organization
  async deleteOrganization(orgId: string): Promise<void> {
    await apiClient.delete(`${this.baseUrl}/${orgId}`);
  }

  // Get organization by ID
  async getOrganizationById(orgId: string): Promise<Organization> {
    const response = await apiClient.get<Organization>(
      `${this.baseUrl}/${orgId}`,
    );
    return response.data;
  }

  // Get organization members
  async getOrganizationMembers(orgId: string): Promise<Member[]> {
    const response = await apiClient.get<Member[]>(
      `${this.baseUrl}/${orgId}/members`,
    );
    return response.data;
  }

  // Mark onboarding as completed for an organization (org_admin only, one-way)
  async completeOnboarding(orgId: string): Promise<Organization> {
    const response = await apiClient.post<Organization>(
      `${this.baseUrl}/${orgId}/complete-onboarding`,
    );
    return response.data;
  }

  // Invite a member to the organization
  async inviteMember(
    orgId: string,
    email: string,
    role: InvitationRole = "regular_user",
  ): Promise<Invitation> {
    const response = await apiClient.post<Invitation>(
      `${this.baseUrl}/${orgId}/invite`,
      {
        email,
        role,
        organization_id: orgId,
      },
    );
    return response.data;
  }
}

// Export a singleton instance of the Organization service
export const organizationService = new OrganizationService();
