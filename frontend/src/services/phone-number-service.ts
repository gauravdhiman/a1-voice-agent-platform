/**
 * Service for phone number API operations
 */

import { apiClient } from "@/lib/api/client";
import type {
  PhoneNumber,
  PhoneNumberWithAgent,
  PhoneNumberAssignRequest,
  PhoneNumberListResponse,
  PhoneNumberImportRequest,
  PhoneNumberImportResponse,
  PhoneNumberPurchaseRequest,
  PhoneNumberPurchaseResponse,
  PhoneNumberSearchRequest,
  PhoneNumberSearchResponse,
  PhoneNumberWebhookDetailsResponse,
} from "@/types/phone-number";

class PhoneNumberService {
  private baseUrl = "/api/v1/phone-numbers";

  async searchAvailable(
    searchRequest: PhoneNumberSearchRequest,
  ): Promise<PhoneNumberSearchResponse> {
    const params = new URLSearchParams();

    params.append("organization_id", searchRequest.organization_id);
    if (searchRequest.country_code) {
      params.append("country_code", searchRequest.country_code);
    }
    if (searchRequest.phone_number_type) {
      params.append("phone_number_type", searchRequest.phone_number_type);
    }
    if (searchRequest.area_code) {
      params.append("area_code", searchRequest.area_code);
    }
    if (searchRequest.contains) {
      params.append("contains", searchRequest.contains);
    }
    if (searchRequest.search_mode) {
      params.append("search_mode", searchRequest.search_mode);
    }
    if (searchRequest.page) {
      params.append("page", searchRequest.page.toString());
    }
    if (searchRequest.page_size) {
      params.append("page_size", searchRequest.page_size.toString());
    }

    const response = await apiClient.get<PhoneNumberSearchResponse>(
      `${this.baseUrl}/available?${params}`,
    );
    return response.data;
  }

  async purchaseNumber(
    organizationId: string,
    purchaseRequest: PhoneNumberPurchaseRequest,
    idempotencyKey = globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`,
  ): Promise<PhoneNumberPurchaseResponse> {
    const response = await apiClient.post<PhoneNumberPurchaseResponse>(
      `${this.baseUrl}/purchase?organization_id=${encodeURIComponent(organizationId)}`,
      purchaseRequest,
      { headers: { "Idempotency-Key": idempotencyKey } },
    );
    return response.data;
  }

  async importNumber(
    organizationId: string,
    importRequest: PhoneNumberImportRequest,
  ): Promise<PhoneNumberImportResponse> {
    const response = await apiClient.post<PhoneNumberImportResponse>(
      `${this.baseUrl}/import?organization_id=${encodeURIComponent(organizationId)}`,
      importRequest,
    );
    return response.data;
  }

  async getOrganizationNumbers(
    organizationId: string,
  ): Promise<PhoneNumberListResponse> {
    const response = await apiClient.get<PhoneNumberListResponse>(
      `${this.baseUrl}?organization_id=${organizationId}`,
    );
    return response.data;
  }

  /**
   * Loads the active number assigned to one agent without listing the whole
   * organization inventory.
   *
   * @param organizationId - Organization that owns the agent
   * @param agentId - Agent whose assignment should be loaded
   * @returns The assigned number, or null when the agent has no assignment
   */
  async getAgentNumber(
    organizationId: string,
    agentId: string,
  ): Promise<PhoneNumberWithAgent | null> {
    const response = await apiClient.get<PhoneNumberWithAgent | null>(
      `${this.baseUrl}/agent/${agentId}?organization_id=${encodeURIComponent(organizationId)}`,
    );
    return response.data;
  }

  /**
   * Loads the tokenized webhook URLs for a customer-owned number awaiting verification.
   *
   * @param organizationId - Organization that owns the number
   * @param phoneNumberId - Phone-number record awaiting verification
   * @returns Pending webhook URLs and setup instructions
   */
  async getVerificationDetails(
    organizationId: string,
    phoneNumberId: string,
  ): Promise<PhoneNumberWebhookDetailsResponse> {
    const response = await apiClient.get<PhoneNumberWebhookDetailsResponse>(
      `${this.baseUrl}/${phoneNumberId}/verification-details?organization_id=${encodeURIComponent(organizationId)}`,
    );
    return response.data;
  }

  async assignToAgent(
    phoneNumberId: string,
    assignRequest: PhoneNumberAssignRequest,
    organizationId: string,
  ): Promise<{ success: boolean; phone_number: PhoneNumber }> {
    const response = await apiClient.post<{
      success: boolean;
      phone_number: PhoneNumber;
    }>(
      `${this.baseUrl}/${phoneNumberId}/assign?organization_id=${encodeURIComponent(organizationId)}`,
      assignRequest,
    );
    return response.data;
  }

  /**
   * Removes an agent mapping without releasing the organization-owned number.
   *
   * @param phoneNumberId - Phone-number record to unassign
   * @param organizationId - Organization scope for the request
   * @returns Updated phone-number record
   */
  async unassignFromAgent(
    phoneNumberId: string,
    organizationId: string,
  ): Promise<{ success: boolean; phone_number: PhoneNumber }> {
    const response = await apiClient.delete<{
      success: boolean;
      phone_number: PhoneNumber;
    }>(
      `${this.baseUrl}/${phoneNumberId}/assignment?organization_id=${encodeURIComponent(organizationId)}`,
    );
    return response.data;
  }

  async cancelNumber(
    phoneNumberId: string,
    organizationId: string,
  ): Promise<{ success: boolean; message: string }> {
    const response = await apiClient.delete<{
      success: boolean;
      message: string;
    }>(
      `${this.baseUrl}/${phoneNumberId}?organization_id=${encodeURIComponent(organizationId)}`,
    );
    return response.data;
  }

  formatPhoneNumber(phoneNumber: string): string {
    const cleaned = phoneNumber.replace(/\D/g, "");
    if (cleaned.length === 11 && cleaned.startsWith("1")) {
      return `+1 (${cleaned.slice(1, 4)}) ${cleaned.slice(4, 7)}-${cleaned.slice(7)}`;
    }
    if (cleaned.length === 10) {
      return `+1 (${cleaned.slice(0, 3)}) ${cleaned.slice(3, 6)}-${cleaned.slice(6)}`;
    }
    return phoneNumber;
  }

  formatCredits(credits: number): string {
    return new Intl.NumberFormat("en-US").format(credits);
  }
}

export const phoneNumberService = new PhoneNumberService();
