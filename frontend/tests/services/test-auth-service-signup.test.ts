import { beforeEach, describe, expect, it, vi } from "vitest";

const { postMock, setSessionMock } = vi.hoisted(() => ({
  postMock: vi.fn(),
  setSessionMock: vi.fn(),
}));

vi.mock("@/lib/api/client", () => ({
  apiClient: {
    post: postMock,
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

describe("authService.signUp", () => {
  beforeEach(() => {
    postMock.mockReset();
    setSessionMock.mockReset();
  });

  it("returns immediate session data when email verification is not required", async () => {
    postMock.mockResolvedValue({
      success: true,
      data: {
        user: {
          id: "user-1",
          email: "new@example.com",
          first_name: "New",
          last_name: "User",
          email_confirmed_at: "2026-01-01T00:00:00Z",
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
          roles: [],
        },
        email_verification_required: false,
        access_token: "access-token",
        refresh_token: "refresh-token",
        expires_in: 3600,
        token_type: "bearer",
      },
    });
    setSessionMock.mockResolvedValue({ error: null });

    const result = await authService.signUp({
      email: "new@example.com",
      password: "Password123!",
      passwordConfirm: "Password123!",
      firstName: "New",
      lastName: "User",
    });

    expect(postMock).toHaveBeenCalledWith("/api/v1/auth/signup", {
      email: "new@example.com",
      password: "Password123!",
      password_confirm: "Password123!",
      first_name: "New",
      last_name: "User",
      invitation_token: undefined,
    });
    expect(setSessionMock).toHaveBeenCalledWith({
      access_token: "access-token",
      refresh_token: "refresh-token",
    });
    expect(result).toEqual({
      success: true,
      emailVerificationRequired: false,
      user: expect.objectContaining({ id: "user-1", email: "new@example.com" }),
      joinedOrganizationId: null,
      joinedOrganizationName: null,
    });
  });

  it("does not set a session when email verification is required", async () => {
    postMock.mockResolvedValue({
      success: true,
      data: {
        user: {
          id: "user-1",
          email: "new@example.com",
          first_name: "New",
          last_name: "User",
          email_confirmed_at: null,
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
          roles: [],
        },
        email_verification_required: true,
        access_token: null,
        refresh_token: null,
        token_type: "bearer",
      },
    });

    const result = await authService.signUp({
      email: "new@example.com",
      password: "Password123!",
      passwordConfirm: "Password123!",
      firstName: "New",
      lastName: "User",
    });

    expect(setSessionMock).not.toHaveBeenCalled();
    expect(result).toEqual({
      success: true,
      emailVerificationRequired: true,
      user: expect.objectContaining({ id: "user-1" }),
      joinedOrganizationId: null,
      joinedOrganizationName: null,
    });
  });
});
