import { beforeEach, describe, expect, it, vi } from "vitest";

const { postMock, setSessionMock } = vi.hoisted(() => ({
  postMock: vi.fn(),
  setSessionMock: vi.fn(),
}));

vi.mock("@/lib/api/client", () => ({
  apiClient: {
    post: postMock,
  },
  ApiRequestError: class ApiRequestError extends Error {
    status: number;
    data?: unknown;
    constructor(message: string, status: number, data?: unknown) {
      super(message);
      this.status = status;
      this.data = data;
    }
  },
}));

vi.mock("@/lib/supabase", () => ({
  supabase: {
    auth: {
      setSession: setSessionMock,
    },
  },
}));

import { authService } from "@/services/auth-service";
import { ApiRequestError } from "@/lib/api/client";

describe("authService.signIn", () => {
  beforeEach(() => {
    postMock.mockReset();
    setSessionMock.mockReset();
  });

  it("sets Supabase session when backend sign-in succeeds", async () => {
    postMock.mockResolvedValue({
      success: true,
      data: {
        access_token: "access-token",
        refresh_token: "refresh-token",
      },
    });
    setSessionMock.mockResolvedValue({ error: null });

    const result = await authService.signIn({
      email: "user@example.com",
      password: "Password123!",
    });

    expect(result.success).toBe(true);
    expect(setSessionMock).toHaveBeenCalledWith({
      access_token: "access-token",
      refresh_token: "refresh-token",
    });
  });

  it("returns email_not_confirmed code from backend 403", async () => {
    postMock.mockRejectedValue(
      new ApiRequestError("Forbidden", 403, {
        detail: {
          message: "Please verify your email address before signing in.",
          code: "email_not_confirmed",
        },
      }),
    );

    const result = await authService.signIn({
      email: "user@example.com",
      password: "Password123!",
    });

    expect(result.success).toBe(false);
    expect(result.code).toBe("email_not_confirmed");
  });
});

describe("authService.verifyEmail", () => {
  beforeEach(() => {
    postMock.mockReset();
  });

  it("calls backend verify-email endpoint", async () => {
    postMock.mockResolvedValue({
      success: true,
      data: { success: true, message: "Email verified successfully." },
    });

    const result = await authService.verifyEmail("token-abc");

    expect(result.success).toBe(true);
    expect(postMock).toHaveBeenCalledWith("/api/v1/auth/verify-email", {
      token: "token-abc",
    });
  });
});

describe("authService.resendVerificationEmail", () => {
  beforeEach(() => {
    postMock.mockReset();
  });

  it("calls backend resend-verification endpoint", async () => {
    postMock.mockResolvedValue({
      success: true,
      data: { message: "Verification email sent." },
    });

    const result = await authService.resendVerificationEmail("user@example.com");

    expect(result.success).toBe(true);
    expect(postMock).toHaveBeenCalledWith("/api/v1/auth/resend-verification", {
      email: "user@example.com",
    });
  });
});
