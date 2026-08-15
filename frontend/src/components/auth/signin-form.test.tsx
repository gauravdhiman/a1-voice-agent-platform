import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { checkEmailAvailabilityMock, signInMock } = vi.hoisted(() => ({
  checkEmailAvailabilityMock: vi.fn(),
  signInMock: vi.fn(),
}));

vi.mock("@/contexts/auth-context", () => ({
  useAuth: () => ({ signIn: signInMock }),
}));

vi.mock("@/services/auth-service", () => ({
  authService: {
    checkEmailAvailability: checkEmailAvailabilityMock,
  },
}));

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/components/auth/email-verification-banner", () => ({
  EmailVerificationBanner: () => null,
}));

vi.mock("@/components/auth/forgot-password-dialog", () => ({
  ForgotPasswordDialog: () => null,
}));

vi.mock("@/components/auth/oauth-redirect-button", () => ({
  OAuthRedirectButton: ({ text }: { text: string }) => <button>{text}</button>,
}));

import { SignInForm } from "./signin-form";

describe("SignInForm credential feedback", () => {
  beforeEach(() => {
    checkEmailAvailabilityMock.mockReset();
    signInMock.mockReset();
  });

  it("explains when no account exists for the submitted email", async () => {
    checkEmailAvailabilityMock.mockResolvedValue({
      success: true,
      data: { exists: false, signInMethods: [] },
    });

    render(<SignInForm />);
    fireEvent.change(screen.getByLabelText("Email Address"), {
      target: { value: "missing@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "Password123!" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Sign In" }));

    await waitFor(() =>
      expect(
        screen.getByText(
          "No account found for this email. Please check the address or sign up for a new account.",
        ),
      ).toBeInTheDocument(),
    );
    expect(signInMock).not.toHaveBeenCalled();
  });

  it("explains when the password does not match an existing account", async () => {
    checkEmailAvailabilityMock.mockResolvedValue({
      success: true,
      data: { exists: true, signInMethods: ["email"] },
    });
    signInMock.mockRejectedValue(new Error("Invalid email or password"));

    render(<SignInForm />);
    fireEvent.change(screen.getByLabelText("Email Address"), {
      target: { value: "existing@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "WrongPassword123!" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Sign In" }));

    await waitFor(() =>
      expect(
        screen.getByText(
          "The password you entered is incorrect. Please try again or reset your password.",
        ),
      ).toBeInTheDocument(),
    );
    expect(signInMock).toHaveBeenCalledWith({
      email: "existing@example.com",
      password: "WrongPassword123!",
    });
  });
});
