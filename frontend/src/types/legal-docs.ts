/**
 * Types for the public legal documents and platform-admin versioning APIs.
 */

export type LegalDocumentKey = "terms" | "privacy";

export type LegalVersionStatus =
  | "draft"
  | "published"
  | "deprecated"
  | "retired";

export interface LegalDocumentPublic {
  document_key: LegalDocumentKey;
  title: string;
  version_number: number;
  content_markdown: string;
  published_at: string | null;
}

export interface LegalDocumentVersionSummary {
  id: string;
  document_key: LegalDocumentKey;
  version_number: number;
  status: LegalVersionStatus;
  is_current: boolean;
  summary_of_changes: string | null;
  published_at: string | null;
  published_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface LegalDocumentVersionDetail
  extends LegalDocumentVersionSummary {
  content_markdown: string;
}

export interface LegalDraftCreate {
  content_markdown?: string | null;
  summary_of_changes?: string | null;
}

export interface LegalDraftUpdate {
  content_markdown: string;
  summary_of_changes?: string | null;
}

export interface LegalPublishRequest {
  notify_users: boolean;
}

export interface LegalPublishResult {
  version: LegalDocumentVersionDetail;
  publish_event_id: string;
  notified_count: number;
  dispatch_id: string | null;
}
