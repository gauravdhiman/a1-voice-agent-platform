/**
 * Site-wide branding constants for the public-facing product.
 *
 * Single source of truth for the product name and tagline used across the
 * marketing pages (landing, sign-in, sign-up) and page metadata. Reads the
 * NEXT_PUBLIC_APP_NAME env var so deploy-time branding can override the
 * default without touching code.
 *
 * @example
 * ```ts
 * import { SITE_NAME, SITE_TAGLINE } from "@/lib/site-config";
 *
 * <header>{SITE_NAME}</header>
 * ```
 */
export const SITE_NAME = process.env.NEXT_PUBLIC_APP_NAME || "24x7 AI";

/** Short positioning tagline shown under the brand and in metadata. */
export const SITE_TAGLINE = "Your AI front desk. Always on.";

/** Long-form description used for SEO metadata and footer blurbs. */
export const SITE_DESCRIPTION =
  "24x7 AI answers every call, books every appointment, and follows up with your customers - 24 hours a day, 7 days a week. No coding required.";

/** Public marketing site URL (production). */
export const SITE_URL = "https://247ai.live";

/** Sales contact used by the "Talk to Sales" call-to-action. */
export const SITE_SALES_EMAIL = "sales@247ai.live";
