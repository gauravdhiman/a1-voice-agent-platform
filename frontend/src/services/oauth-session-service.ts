import { apiClient } from "@/lib/api/client";

interface SessionHandoffApiResponse {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  token_type: string;
}

function extractSessionPayload(
  response: Awaited<ReturnType<typeof apiClient.post<SessionHandoffApiResponse>>>,
): SessionHandoffApiResponse | null {
  const payload = response.data ?? (response as unknown as SessionHandoffApiResponse);
  if (
    payload &&
    typeof payload.access_token === "string" &&
    typeof payload.refresh_token === "string"
  ) {
    return payload;
  }
  return null;
}

/**
 * Exchanges a one-time OAuth session handoff token for Supabase credentials.
 */
export async function exchangeOAuthSessionHandoff(handoff: string): Promise<{
  success: boolean;
  error?: string;
  data?: SessionHandoffApiResponse;
}> {
  try {
    const response = await apiClient.post<SessionHandoffApiResponse>(
      "/api/v1/auth/session/handoff",
      { handoff },
    );
    const payload = extractSessionPayload(response);
    if (!payload) {
      return {
        success: false,
        error: "Authentication could not be completed.",
      };
    }
    return { success: true, data: payload };
  } catch (error) {
    return {
      success: false,
      error:
        error instanceof Error
          ? error.message
          : "Authentication could not be completed.",
    };
  }
}
