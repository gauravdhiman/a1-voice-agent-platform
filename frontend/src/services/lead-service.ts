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

/** Standard service result envelope. */
export interface LeadServiceResult {
  success: boolean;
  error?: string;
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

export const leadService = {
  submitInterestLead,
  isPublicSignupEnabled,
};
