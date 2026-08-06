import { beforeEach, describe, expect, it, vi } from "vitest";

const { postMock } = vi.hoisted(() => ({
  postMock: vi.fn(),
}));

vi.mock("@/lib/api/client", () => ({
  apiClient: {
    post: postMock,
  },
}));

import { exchangeOAuthSessionHandoff } from "@/services/oauth-session-service";

describe("exchangeOAuthSessionHandoff", () => {
  beforeEach(() => {
    postMock.mockReset();
  });

  it("returns tokens from a wrapped API response", async () => {
    postMock.mockResolvedValue({
      success: true,
      data: {
        access_token: "access-token",
        refresh_token: "refresh-token",
        expires_in: 3600,
        token_type: "bearer",
      },
    });

    const result = await exchangeOAuthSessionHandoff("handoff-token");

    expect(postMock).toHaveBeenCalledWith("/api/v1/auth/session/handoff", {
      handoff: "handoff-token",
    });
    expect(result).toEqual({
      success: true,
      data: {
        access_token: "access-token",
        refresh_token: "refresh-token",
        expires_in: 3600,
        token_type: "bearer",
      },
    });
  });

  it("returns tokens from a direct API response body", async () => {
    postMock.mockResolvedValue({
      access_token: "access-token",
      refresh_token: "refresh-token",
      expires_in: 3600,
      token_type: "bearer",
    });

    const result = await exchangeOAuthSessionHandoff("handoff-token");

    expect(result.success).toBe(true);
    expect(result.data?.access_token).toBe("access-token");
  });

  it("returns an error when tokens are missing", async () => {
    postMock.mockResolvedValue({ success: true, data: { expires_in: 3600 } });

    const result = await exchangeOAuthSessionHandoff("handoff-token");

    expect(result).toEqual({
      success: false,
      error: "Authentication could not be completed.",
    });
  });

  it("returns an error when the API call throws", async () => {
    postMock.mockRejectedValue(new Error("Network error"));

    const result = await exchangeOAuthSessionHandoff("handoff-token");

    expect(result).toEqual({
      success: false,
      error: "Network error",
    });
  });
});
