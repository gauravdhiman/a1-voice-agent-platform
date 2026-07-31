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
  onboarding_completed: boolean;
  created_at: string;
  updated_at: string;
  google_api_key?: string | null;
  /**
   * Per-provider "is a key configured?" map (booleans only — never the decrypted
   * values), derived from the encrypted `provider_credentials` blob on read
   * (Phase 4). Keys: google, deepgram, openai, cartesia, cerebras, livekit.
   * Drives the Configured/Not-configured pills on the org-settings page. The
   * `livekit` boolean is true when the livekit blob has an `api_key`.
   */
  provider_credentials_status?: Record<string, boolean>;
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
}

// For organization creation (subset of Organization)
export interface OrganizationCreate {
  name: string;
  description?: string;
  slug: string;
  website?: string;
  is_active?: boolean;
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
  business_details?: string | null;
  google_api_key?: string | null;
  /**
   * Per-provider credentials supplied from the UI (Phase 4). Send ONLY touched
   * fields: a non-empty string to set, `null` to explicitly clear, and OMIT a
   * provider to leave it unchanged (the backend preserves omitted keys and
   * drops `None`). LiveKit is `{api_key, api_secret}`. The backend merges this
   * with the existing decrypted blob and re-encrypts; this field is never
   * persisted directly. Keys: google, deepgram, openai, cartesia, cerebras,
   * livekit.
   */
  provider_credentials_input?: Record<
    string,
    string | { api_key: string; api_secret: string } | null
  >;
  public_page_enabled?: boolean;
  public_page_passphrase_enabled?: boolean;
  /** Write-only: set or rotate the public page passphrase (never returned). */
  public_page_passphrase?: string;
}

// Minimal organization interface for utility functions
export interface OrganizationForDetection {
  name: string;
  slug: string;
  description?: string | null;
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
