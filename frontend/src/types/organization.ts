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
  created_at: string;
  updated_at: string;
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
