/**
 * Organization-related type definitions
 */

// Base Organization interface with all possible fields
export interface Organization {
  id: string;
  name: string;
  description: string | null;
  slug: string;
  website: string | null;
  is_active: boolean;
  industry?: string | null;
  location?: string | null;
  /** IANA timezone used to anchor voice agent date/time context. */
  timezone?: string | null;
  onboarding_completed: boolean;
  created_at: string;
  updated_at: string;
  google_api_key?: string | null;
  /**
   * Per-provider "is a key configured?" map (booleans only — never the decrypted
   * values), derived from the encrypted `provider_credentials` blob on read
   * (Phase 4). Keys: google, deepgram, openai, cartesia, cerebras, openrouter,
   * fish, resend.
   * Drives the Configured/Not-configured pills on the org-settings page.
   */
  provider_credentials_status?: Record<string, boolean>;
  /** Optional non-secret reference notes keyed by provider name. */
  provider_credentials_descriptions?: Record<string, string>;
  /** When true, `/o/{slug}` is available to visitors. */
  public_page_enabled?: boolean;
  /** When true, visitors must enter a passphrase before listing agents. */
  public_page_passphrase_enabled?: boolean;
}

// Enhanced Organization interface with business details field
export interface OrganizationEnhanced extends Organization {
  business_details?: string | null;
}

// Invitation type for organization membership invitations
export type InvitationRole = "regular_user" | "org_admin";

export interface Invitation {
  id: string;
  email: string;
  organization_id: string;
  invited_by: string;
  token: string;
  status: "pending" | "accepted" | "expired" | "cancelled";
  expires_at: string;
  created_at: string;
  accepted_at?: string;
  role_id?: string | null;
  /** Populated when an invitation is accepted successfully. */
  organization_name?: string | null;
}

// For organization creation (subset of Organization)
export interface OrganizationCreate {
  name: string;
  description?: string;
  slug: string;
  website?: string;
  is_active?: boolean;
}

/** Organization creation payload used by platform-admin provisioning. */
export interface PlatformOrganizationCreate extends OrganizationCreate {
  plan_version_id: string;
}

// For organization updates (partial Organization)
export interface OrganizationUpdate {
  name?: string;
  description?: string | null;
  slug?: string;
  website?: string | null;
  is_active?: boolean;
  industry?: string | null;
  location?: string | null;
  /** IANA timezone; empty string clears the org default on save. */
  timezone?: string | null;
  business_details?: string | null;
  google_api_key?: string | null;
  /**
   * Per-provider credentials supplied from the UI (Phase 4). Send ONLY touched
   * fields: a non-empty string to set, `null` to explicitly clear, and OMIT a
   * provider to leave it unchanged (the backend preserves omitted keys and
   * drops `None`). The backend merges this with the existing decrypted blob and
   * re-encrypts; this field is never persisted directly. Keys: google, deepgram,
   * openai, cartesia, cerebras, openrouter, fish, resend.
   */
  provider_credentials_input?: Record<string, string | null>;
  /** Non-secret per-provider reference notes; omitted providers are preserved. */
  provider_credentials_descriptions_input?: Record<string, string | null>;
  public_page_enabled?: boolean;
  public_page_passphrase_enabled?: boolean;
  /** Write-only: set or rotate the public page passphrase (never returned). */
  public_page_passphrase?: string;
}

// Organization with member count (for listings)
export interface OrganizationWithStats extends Organization {
  memberCount?: number;
  activeProjects?: number;
}

// Combined organization data structure
export interface OrganizationCompleteData {
  organization: OrganizationEnhanced;
}
