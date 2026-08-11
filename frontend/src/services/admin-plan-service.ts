/**
 * Service for platform-admin plan catalog and entitlement APIs.
 */

import { apiClient } from "@/lib/api/client";
import type {
  EntitlementDefinition,
  EntitlementDefinitionUpdate,
  PlanProduct,
  PlanProductCreate,
  PlanProductCreateResult,
  PlanProductWithVersions,
  PlanVersionCloneRequest,
  PlanVersionDetail,
  PlanVersionDraftCreate,
  PlanVersionDraftUpdate,
  PlanVersionPublishRequest,
  PlanVersionPublishResult,
} from "@/types/admin-plans";

class AdminPlanService {
  private baseUrl = "/api/v1/admin";

  async listEntitlementDefinitions(
    activeOnly = false,
  ): Promise<EntitlementDefinition[]> {
    const params = new URLSearchParams();
    if (activeOnly) params.append("active_only", "true");
    const query = params.toString();
    const response = await apiClient.get<EntitlementDefinition[]>(
      `${this.baseUrl}/entitlement-definitions${query ? `?${query}` : ""}`,
    );
    return response.data;
  }

  async updateEntitlementDefinition(
    key: string,
    body: EntitlementDefinitionUpdate,
  ): Promise<EntitlementDefinition> {
    const response = await apiClient.patch<EntitlementDefinition>(
      `${this.baseUrl}/entitlement-definitions/${encodeURIComponent(key)}`,
      body,
    );
    return response.data;
  }

  async listPlanProducts(): Promise<PlanProductWithVersions[]> {
    const response = await apiClient.get<PlanProductWithVersions[]>(
      `${this.baseUrl}/plan-products`,
    );
    return response.data;
  }

  async createPlanProduct(body: PlanProductCreate): Promise<PlanProductCreateResult> {
    const response = await apiClient.post<PlanProductCreateResult>(
      `${this.baseUrl}/plan-products`,
      body,
    );
    return response.data;
  }

  async updatePlanProductStripe(
    productId: string,
    stripeProductId: string,
  ): Promise<PlanProduct> {
    const response = await apiClient.patch<PlanProduct>(
      `${this.baseUrl}/plan-products/${productId}/stripe`,
      { stripe_product_id: stripeProductId },
    );
    return response.data;
  }

  async createDraftVersion(
    productId: string,
    body: PlanVersionDraftCreate,
  ): Promise<PlanVersionDetail> {
    const response = await apiClient.post<PlanVersionDetail>(
      `${this.baseUrl}/plan-products/${productId}/versions`,
      body,
    );
    return response.data;
  }

  async getPlanVersion(versionId: string): Promise<PlanVersionDetail> {
    const response = await apiClient.get<PlanVersionDetail>(
      `${this.baseUrl}/plan-versions/${versionId}`,
    );
    return response.data;
  }

  async updateDraftVersion(
    versionId: string,
    body: PlanVersionDraftUpdate,
  ): Promise<PlanVersionDetail> {
    const response = await apiClient.put<PlanVersionDetail>(
      `${this.baseUrl}/plan-versions/${versionId}`,
      body,
    );
    return response.data;
  }

  /**
   * Updates only the entitlement presentation order for a plan version.
   *
   * @param versionId - Plan version whose card order should change
   * @param entitlementKeys - All assigned keys in their desired display order
   * @returns The updated plan version detail
   */
  async reorderPlanVersionEntitlements(
    versionId: string,
    entitlementKeys: string[],
  ): Promise<PlanVersionDetail> {
    const response = await apiClient.patch<PlanVersionDetail>(
      `${this.baseUrl}/plan-versions/${versionId}/entitlements/order`,
      { entitlement_keys: entitlementKeys },
    );
    return response.data;
  }

  async deleteDraftVersion(versionId: string): Promise<void> {
    await apiClient.delete(`${this.baseUrl}/plan-versions/${versionId}`);
  }

  async clonePlanVersion(
    versionId: string,
    body: PlanVersionCloneRequest = {},
  ): Promise<PlanVersionDetail> {
    const response = await apiClient.post<PlanVersionDetail>(
      `${this.baseUrl}/plan-versions/${versionId}/clone`,
      body,
    );
    return response.data;
  }

  async publishPlanVersion(
    versionId: string,
    body: PlanVersionPublishRequest,
  ): Promise<PlanVersionPublishResult> {
    const response = await apiClient.post<PlanVersionPublishResult>(
      `${this.baseUrl}/plan-versions/${versionId}/publish`,
      body,
    );
    return response.data;
  }
}

export const adminPlanService = new AdminPlanService();
