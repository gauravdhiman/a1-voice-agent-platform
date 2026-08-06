import { describe, expect, it } from "vitest";

import { getSafeApiErrorMessage } from "@/lib/api/error-message";

describe("getSafeApiErrorMessage", () => {
  it("extracts validation messages without echoing request input", () => {
    const message = getSafeApiErrorMessage({
      detail: [
        {
          type: "value_error",
          loc: ["body"],
          msg: "Value error, Passwords do not match",
          input: {
            email: "user@example.com",
            password: "Secret123!",
            password_confirm: "",
          },
        },
      ],
    });

    expect(message).toBe("Passwords do not match");
    expect(message).not.toContain("Secret123!");
  });

  it("returns structured conflict messages", () => {
    const message = getSafeApiErrorMessage({
      detail: {
        message: "An account with this email already exists.",
        sign_in_methods: ["google"],
      },
    });

    expect(message).toBe("An account with this email already exists.");
  });

  it("falls back when payload appears to contain sensitive fields", () => {
    const message = getSafeApiErrorMessage({
      detail: '{"password":"Secret123!"}',
    });

    expect(message).toBe("Something went wrong. Please try again.");
  });
});
