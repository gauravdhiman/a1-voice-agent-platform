/**
 * Service for public legal documents and platform-admin versioning APIs.
 */

import { apiClient } from "@/lib/api/client";
import type {
  LegalDocumentKey,
  LegalDocumentPublic,
  LegalDocumentVersionDetail,
  LegalDocumentVersionSummary,
  LegalDraftCreate,
  LegalDraftUpdate,
  LegalPublishRequest,
  LegalPublishResult,
} from "@/types/legal-docs";

class LegalDocService {
  /** Public (unauthenticated) legal document reads. */
  private publicBaseUrl = "/api/v1/legal";
  /** Platform-admin version management. */
  private adminBaseUrl = "/api/v1/admin/legal";

  async getPublishedDocument(
    key: LegalDocumentKey,
  ): Promise<LegalDocumentPublic> {
    const response = await apiClient.get<LegalDocumentPublic>(
      `${this.publicBaseUrl}/${encodeURIComponent(key)}`,
    );
    return response.data;
  }

  async listVersions(
    key: LegalDocumentKey,
  ): Promise<LegalDocumentVersionSummary[]> {
    const response = await apiClient.get<LegalDocumentVersionSummary[]>(
      `${this.adminBaseUrl}/${encodeURIComponent(key)}/versions`,
    );
    return response.data;
  }

  async getVersion(versionId: string): Promise<LegalDocumentVersionDetail> {
    const response = await apiClient.get<LegalDocumentVersionDetail>(
      `${this.adminBaseUrl}/versions/${encodeURIComponent(versionId)}`,
    );
    return response.data;
  }

  async createDraft(
    key: LegalDocumentKey,
    body: LegalDraftCreate,
  ): Promise<LegalDocumentVersionDetail> {
    const response = await apiClient.post<LegalDocumentVersionDetail>(
      `${this.adminBaseUrl}/${encodeURIComponent(key)}/draft`,
      body,
    );
    return response.data;
  }

  async updateDraft(
    versionId: string,
    body: LegalDraftUpdate,
  ): Promise<LegalDocumentVersionDetail> {
    const response = await apiClient.put<LegalDocumentVersionDetail>(
      `${this.adminBaseUrl}/versions/${encodeURIComponent(versionId)}`,
      body,
    );
    return response.data;
  }

  async deleteDraft(versionId: string): Promise<void> {
    await apiClient.delete(
      `${this.adminBaseUrl}/versions/${encodeURIComponent(versionId)}`,
    );
  }

  async publishVersion(
    versionId: string,
    body: LegalPublishRequest,
  ): Promise<LegalPublishResult> {
    const response = await apiClient.post<LegalPublishResult>(
      `${this.adminBaseUrl}/versions/${encodeURIComponent(versionId)}/publish`,
      body,
    );
    return response.data;
  }
}

export const legalDocService = new LegalDocService();
