import { describe, expect, it, vi, beforeEach } from "vitest";
import { ApiRequestError } from "@/lib/api/client";

const { mockGet, mockPost } = vi.hoisted(() => ({
  mockGet: vi.fn(),
  mockPost: vi.fn(),
}));

vi.mock("@/lib/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/client")>();
  return {
    ...actual,
    apiClient: {
      get: mockGet,
      post: mockPost,
    },
  };
});

describe("authService email availability", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns existing account methods from check-email", async () => {
    mockGet.mockResolvedValue({
      data: {
        exists: true,
        sign_in_methods: ["google", "email"],
        message: "An account with this email already exists. Sign in with Google or Email and password.",
      },
    });

    const { authService } = await import("@/services/auth-service");
    const result = await authService.checkEmailAvailability("existing@example.com");

    expect(result.success).toBe(true);
    expect(result.data?.exists).toBe(true);
    expect(result.data?.signInMethods).toEqual(["google", "email"]);
    expect(mockGet).toHaveBeenCalledWith(
      "/api/v1/auth/check-email?email=existing%40example.com",
    );
  });

  it("returns structured conflict details on duplicate signup", async () => {
    mockPost.mockRejectedValue(
      new ApiRequestError("Conflict", 409, {
        detail: {
          message: "An account with this email already exists.",
          sign_in_methods: ["linkedin"],
        },
      }),
    );

    const { authService } = await import("@/services/auth-service");
    const result = await authService.signUp({
      email: "existing@example.com",
      password: "Password123!",
      passwordConfirm: "Password123!",
      firstName: "Existing",
      lastName: "User",
    });

    expect(result.success).toBe(false);
    expect(result.errorDetails?.signInMethods).toEqual(["linkedin"]);
    expect(result.error).toContain("already exists");
  });
});
