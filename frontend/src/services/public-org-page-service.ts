/**
 * Client for unauthenticated public organization page APIs.
 */

import type {
  PublicCallTokenResponse,
  PublicOrgAgentsResponse,
  PublicOrgSummary,
} from "@/types/public-org-page";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function accessHeaders(accessToken?: string | null): HeadersInit {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (accessToken) {
    headers["X-Public-Access-Token"] = accessToken;
  }
  return headers;
}

class PublicOrgPageService {
  async getOrgSummary(slug: string): Promise<PublicOrgSummary> {
    const response = await fetch(`${API_BASE_URL}/api/v1/public/orgs/${slug}`);
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || "Public page not found");
    }
    return response.json();
  }

  async verifyPassphrase(
    slug: string,
    passphrase: string,
  ): Promise<{ access_token: string }> {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/public/orgs/${slug}/access`,
      {
        method: "POST",
        headers: accessHeaders(),
        body: JSON.stringify({ passphrase }),
      },
    );
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || "Incorrect passphrase");
    }
    return response.json();
  }

  async listAgents(
    slug: string,
    accessToken?: string | null,
  ): Promise<PublicOrgAgentsResponse> {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/public/orgs/${slug}/agents`,
      { headers: accessHeaders(accessToken) },
    );
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || "Failed to load agents");
    }
    return response.json();
  }

  async getCallToken(
    slug: string,
    agentId: string,
    accessToken?: string | null,
  ): Promise<PublicCallTokenResponse> {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/public/orgs/${slug}/agents/${agentId}/token`,
      {
        method: "POST",
        headers: accessHeaders(accessToken),
      },
    );
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || "Failed to start call");
    }
    return response.json();
  }
}

export const publicOrgPageService = new PublicOrgPageService();

export function getPublicAccessTokenKey(slug: string): string {
  return `public-org-access:${slug}`;
}

export function readStoredAccessToken(slug: string): string | null {
  if (typeof window === "undefined") return null;
  try {
    return sessionStorage.getItem(getPublicAccessTokenKey(slug));
  } catch {
    return null;
  }
}

export function storeAccessToken(slug: string, token: string): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.setItem(getPublicAccessTokenKey(slug), token);
  } catch {
    // ignore quota / private mode
  }
}

export function clearAccessToken(slug: string): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.removeItem(getPublicAccessTokenKey(slug));
  } catch {
    // ignore
  }
}
