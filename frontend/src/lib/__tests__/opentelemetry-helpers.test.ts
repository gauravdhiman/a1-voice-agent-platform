import { describe, expect, it } from "vitest";
import { withTelemetrySignUp } from "@/lib/opentelemetry-helpers";
import type { SignUpData } from "@/types/auth";

describe("withTelemetrySignUp", () => {
  it("preserves the richer application signup result", async () => {
    const signup = async (_data: SignUpData) => ({
      user: undefined,
      emailVerificationRequired: true,
      error: null,
    });

    const result = await withTelemetrySignUp(signup)({
      email: "test@example.com",
      password: "Password123!",
      passwordConfirm: "Password123!",
      firstName: "Test",
      lastName: "User",
      terms_accepted: true,
    });

    expect(result.emailVerificationRequired).toBe(true);
    expect(result.error).toBeNull();
  });
});
