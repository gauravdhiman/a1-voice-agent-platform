import { apiClient } from "@/lib/api/client";
import type { LinkedInSessionData } from "@/types/auth";

interface LinkedInAuthorizationApiResponse {
  authorization_url: string;
  state: string;
}

interface LinkedInSessionApiResponse {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  token_type: string;
  user: {
    id: string;
    email: string;
    first_name: string;
    last_name: string;
  };
}

/**
 * Service for the direct LinkedIn OAuth broker.
 *
 * The browser requests a provider authorization URL from the backend, opens
 * LinkedIn directly, and receives a Supabase session after the backend
 * completes the confidential token exchange.
 */
class LinkedInAuthService {
  /**
   * Requests a signed LinkedIn authorization URL for the popup flow.
   */
  async getAuthorizationUrl(): Promise<{
    success: boolean;
    error?: string;
    data?: { authorizationUrl: string; state: string };
  }> {
    try {
      const response = await apiClient.get<LinkedInAuthorizationApiResponse>(
        "/api/v1/auth/linkedin/authorize",
      );

      return {
        success: true,
        data: {
          authorizationUrl: response.data.authorization_url,
          state: response.data.state,
        },
      };
    } catch (error) {
      return {
        success: false,
        error:
          error instanceof Error ? error.message : "LinkedIn request failed",
      };
    }
  }

  /**
   * Exchanges a one-time LinkedIn callback code for a Supabase session.
   */
  async exchangeCode(
    code: string,
    state: string,
  ): Promise<{
    success: boolean;
    error?: string;
    data?: LinkedInSessionData;
  }> {
    try {
      const response = await apiClient.post<LinkedInSessionApiResponse>(
        "/api/v1/auth/linkedin/exchange",
        { code, state },
      );

      return {
        success: true,
        data: {
          accessToken: response.data.access_token,
          refreshToken: response.data.refresh_token,
          expiresIn: response.data.expires_in,
        },
      };
    } catch (error) {
      return {
        success: false,
        error:
          error instanceof Error ? error.message : "LinkedIn request failed",
      };
    }
  }
}

export const linkedinAuthService = new LinkedInAuthService();
