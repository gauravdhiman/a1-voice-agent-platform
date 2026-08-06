/**
 * Tests for the direct LinkedIn authentication service.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

import { apiClient } from "@/lib/api/client";
import { linkedinAuthService } from "@/services/linkedin-auth-service";

describe("LinkedInAuthService", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("maps the backend authorization response", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: {
        authorization_url:
          "https://www.linkedin.com/oauth/v2/authorization?state=signed",
        state: "signed-state",
      },
      success: true,
    });

    const result = await linkedinAuthService.getAuthorizationUrl();

    expect(result).toEqual({
      success: true,
      data: {
        authorizationUrl:
          "https://www.linkedin.com/oauth/v2/authorization?state=signed",
        state: "signed-state",
      },
    });
    expect(apiClient.get).toHaveBeenCalledWith(
      "/api/v1/auth/linkedin/authorize",
    );
  });

  it("maps the backend session response", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      data: {
        access_token: "access-token",
        refresh_token: "refresh-token",
        expires_in: 3600,
        token_type: "bearer",
        user: {
          id: "user-id",
          email: "user@example.com",
          first_name: "Jane",
          last_name: "Doe",
        },
      },
      success: true,
    });

    const result = await linkedinAuthService.exchangeCode(
      "authorization-code",
      "signed-state",
    );

    expect(result).toEqual({
      success: true,
      data: {
        accessToken: "access-token",
        refreshToken: "refresh-token",
        expiresIn: 3600,
      },
    });
    expect(apiClient.post).toHaveBeenCalledWith(
      "/api/v1/auth/linkedin/exchange",
      { code: "authorization-code", state: "signed-state" },
    );
  });

  it("returns a structured error when the backend request fails", async () => {
    vi.mocked(apiClient.get).mockRejectedValue(
      new Error("Backend unavailable"),
    );

    const result = await linkedinAuthService.getAuthorizationUrl();

    expect(result).toEqual({
      success: false,
      error: "Backend unavailable",
    });
  });
});
