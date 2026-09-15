/**
 * Client for interest-lead capture and the public signup gate.
 *
 * @module services/lead-service
 */

import { apiClient, ApiRequestError } from "@/lib/api/client";

/** Visitor-submitted interest payload. */
export interface InterestLeadData {
  /** Contact name. */
  name: string;
  /** Business name. */
  businessName?: string;
  /** Contact email address. */
  email: string;
  /** Callback number. */
  phone?: string;
  /** Business vertical (dental, hvac, restaurant). */
  vertical?: string;
  /** What the business needs. */
  message?: string;
  /** Capture channel; defaults to the request-demo form. */
  source?: "request-demo" | "outcome-form" | "demo-call" | "manual";
  /** Demo agent slug when captured post-demo. */
  demoSlug?: string;
  /** Cloudflare Turnstile token (sent when the widget is enabled). */
  captchaToken?: string;
}

/** Follow-up status of an interest lead. */
export type InterestLeadStatus =
  "new" | "contacted" | "invited" | "converted" | "dropped";

/** One stored interest lead (platform-admin view). */
export interface InterestLead {
  /** Row identifier. */
  id: string;
  /** Contact name. */
  name: string;
  /** Business name. */
  business_name: string | null;
  /** Contact email. */
  email: string;
  /** Callback number. */
  phone: string | null;
  /** Business vertical. */
  vertical: string | null;
  /** What the business needs. */
  message: string | null;
  /** Capture channel. */
  source: string;
  /** Demo slug when captured post-demo. */
  demo_slug: string | null;
  /** Follow-up status. */
  status: InterestLeadStatus;
  /** Submission timestamp. */
  created_at: string;
  /** First outreach timestamp. */
  contacted_at: string | null;
}

/** Standard service result envelope. */
export interface LeadServiceResult {
  success: boolean;
  error?: string;
}

/** Aggregate visitor ratings for one demo slug (platform admins). */
export interface DemoFeedbackSummary {
  demo_slug: string;
  count: number;
  average_rating: number | null;
}

/** One stored visitor rating (platform admins). */
export interface DemoFeedbackRecord {
  id: string;
  session_id: string;
  agent_id: string;
  organization_id: string;
  demo_slug: string;
  rating: number;
  created_at: string;
}

/** Ratings overview: per-demo aggregates plus the newest rows. */
export interface DemoFeedbackOverview {
  summary: DemoFeedbackSummary[];
  recent: DemoFeedbackRecord[];
}

/**
 * Submits visitor interest to the private lead funnel.
 *
 * The backend always returns the same ack envelope, so a success here
 * only means "received" — never whether the email already exists.
 *
 * @param data - Validated interest form values.
 * @returns `{ success: true }` on accept, or `{ success: false, error }`.
 */
async function submitInterestLead(
  data: InterestLeadData,
): Promise<LeadServiceResult> {
  try {
    await apiClient.post<{ received: boolean }>("/api/v1/public/leads", {
      name: data.name,
      business_name: data.businessName || undefined,
      email: data.email,
      phone: data.phone || undefined,
      vertical: data.vertical || undefined,
      message: data.message || undefined,
      source: data.source ?? "request-demo",
      demo_slug: data.demoSlug || undefined,
      captcha_token: data.captchaToken || undefined,
    });
    return { success: true };
  } catch (error) {
    return {
      success: false,
      error:
        error instanceof Error
          ? error.message
          : "Could not send your request. Please try again.",
    };
  }
}

/**
 * Reports whether open public signup is enabled.
 *
 * Used by the signup page to redirect visitors to `/request-demo`
 * while the controlled-SaaS gate is closed. The backend gate remains
 * authoritative; this is UX-only.
 *
 * @returns `true` when open signup is enabled, `false` otherwise
 * (including on lookup failure — closed is the safe default).
 */
async function isPublicSignupEnabled(): Promise<boolean> {
  try {
    const response = await apiClient.get<{ public_signup_enabled: boolean }>(
      "/api/v1/auth/signup-status",
    );
    return response.data?.public_signup_enabled === true;
  } catch (error) {
    if (error instanceof ApiRequestError) {
      return false;
    }
    return false;
  }
}

/**
 * Lists interest leads newest-first (platform admins).
 *
 * @param status - Optional follow-up status filter.
 * @returns Envelope with the lead list.
 */
async function listInterestLeads(
  status?: InterestLeadStatus,
): Promise<LeadServiceResult & { data?: InterestLead[] }> {
  try {
    const query = status ? `?status=${encodeURIComponent(status)}` : "";
    const response = await apiClient.get<InterestLead[]>(
      `/api/v1/leads${query}`,
    );
    return { success: true, data: response.data ?? [] };
  } catch (error) {
    return {
      success: false,
      error:
        error instanceof Error ? error.message : "Could not load interest.",
    };
  }
}

/**
 * Advances one lead's follow-up status (platform admins).
 *
 * @param leadId - Lead row identifier.
 * @param status - Target follow-up status.
 * @returns Envelope with the updated row.
 */
async function updateInterestLeadStatus(
  leadId: string,
  status: InterestLeadStatus,
): Promise<LeadServiceResult & { data?: InterestLead }> {
  try {
    const response = await apiClient.patch<InterestLead>(
      `/api/v1/leads/${encodeURIComponent(leadId)}`,
      { status },
    );
    if (!response.data) return { success: false, error: "No lead returned." };
    return { success: true, data: response.data };
  } catch (error) {
    return {
      success: false,
      error:
        error instanceof Error ? error.message : "Could not update the lead.",
    };
  }
}

export const leadService = {
  submitInterestLead,
  isPublicSignupEnabled,
  listInterestLeads,
  updateInterestLeadStatus,
  listDemoFeedback,
};

/**
 * Lists stored demo ratings with per-demo aggregates (platform admins).
 *
 * @returns Envelope with the ratings overview.
 */
async function listDemoFeedback(): Promise<
  LeadServiceResult & { data?: DemoFeedbackOverview }
> {
  try {
    const response = await apiClient.get<DemoFeedbackOverview>(
      "/api/v1/leads/demo-feedback",
    );
    return {
      success: true,
      data: response.data ?? { summary: [], recent: [] },
    };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : "Could not load ratings.",
    };
  }
}
