import { describe, expect, it } from "vitest";

import { signUpSchema } from "@/lib/auth/signup-schema";

const validPayload = {
  firstName: "Jane",
  lastName: "Doe",
  email: "jane@example.com",
  password: "Password123!",
  passwordConfirm: "Password123!",
  terms_accepted: true,
};

describe("signUpSchema", () => {
  it("accepts a fully valid signup payload", () => {
    expect(signUpSchema.safeParse(validPayload).success).toBe(true);
  });

  it("rejects empty confirm password", () => {
    const result = signUpSchema.safeParse({
      ...validPayload,
      passwordConfirm: "",
    });

    expect(result.success).toBe(false);
    if (!result.success) {
      expect(
        result.error.issues.some(
          (issue) => issue.path[0] === "passwordConfirm",
        ),
      ).toBe(true);
    }
  });

  it("rejects mismatched passwords", () => {
    const result = signUpSchema.safeParse({
      ...validPayload,
      passwordConfirm: "Different123!",
    });

    expect(result.success).toBe(false);
    if (!result.success) {
      expect(
        result.error.issues.some(
          (issue) => issue.message === "Passwords don't match",
        ),
      ).toBe(true);
    }
  });

  it("rejects a signup without terms acceptance", () => {
    const result = signUpSchema.safeParse({
      ...validPayload,
      terms_accepted: false,
    });

    expect(result.success).toBe(false);
    if (!result.success) {
      expect(
        result.error.issues.some((issue) => issue.path[0] === "terms_accepted"),
      ).toBe(true);
    }
  });

  it("rejects missing required identity fields", () => {
    expect(
      signUpSchema.safeParse({ ...validPayload, firstName: "" }).success,
    ).toBe(false);
    expect(
      signUpSchema.safeParse({ ...validPayload, lastName: "" }).success,
    ).toBe(false);
    expect(
      signUpSchema.safeParse({ ...validPayload, email: "not-an-email" })
        .success,
    ).toBe(false);
  });
});
