import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/contexts/auth-context", () => ({
  useAuth: vi.fn(),
}));

vi.mock("@/components/auth/google-sign-in-button", () => ({
  GoogleSignInButton: ({
    onCredential,
    disabled,
    text,
  }: {
    onCredential: (credential: string, nonce: string) => void;
    disabled?: boolean;
    text: "signin_with" | "signup_with";
  }) => (
    <button
      type="button"
      disabled={disabled}
      onClick={() => onCredential("google-id-token", "google-raw-nonce")}
    >
      {text === "signin_with" ? "Sign in with Google" : "Sign up with Google"}
    </button>
  ),
}));

import { useAuth } from "@/contexts/auth-context";
import { SignInForm } from "./signin-form";
import { SignUpForm } from "./signup-form";

describe("Google authentication forms", () => {
  const signIn = vi.fn();
  const signUp = vi.fn();
  const signInWithOAuth = vi.fn();
  const signInWithGoogleIdToken = vi.fn();

  beforeEach(() => {
    signIn.mockReset();
    signUp.mockReset();
    signInWithOAuth.mockReset();
    signInWithGoogleIdToken.mockReset();
    signInWithGoogleIdToken.mockResolvedValue({ error: null });

    vi.mocked(useAuth).mockReturnValue({
      signIn,
      signUp,
      signInWithOAuth,
      signInWithGoogleIdToken,
    } as never);
  });

  it("exchanges the Google ID token during sign-in", async () => {
    const user = userEvent.setup();

    render(<SignInForm />);
    await user.click(
      screen.getByRole("button", { name: "Sign in with Google" }),
    );

    await waitFor(() => {
      expect(signInWithGoogleIdToken).toHaveBeenCalledWith({
        token: "google-id-token",
        nonce: "google-raw-nonce",
      });
    });
    expect(signInWithOAuth).not.toHaveBeenCalled();
  });

  it("exchanges the Google ID token during sign-up", async () => {
    const user = userEvent.setup();

    render(<SignUpForm />);
    await user.click(
      screen.getByRole("button", { name: "Sign up with Google" }),
    );

    await waitFor(() => {
      expect(signInWithGoogleIdToken).toHaveBeenCalledWith({
        token: "google-id-token",
        nonce: "google-raw-nonce",
        invitationToken: undefined,
      });
    });
    expect(signInWithOAuth).not.toHaveBeenCalled();
  });

  it("shows the ID-token exchange error on sign-in", async () => {
    const user = userEvent.setup();
    signInWithGoogleIdToken.mockResolvedValueOnce({
      error: { message: "Google authentication failed" },
    });

    render(<SignInForm />);
    await user.click(
      screen.getByRole("button", { name: "Sign in with Google" }),
    );

    expect(
      await screen.findByText("Google authentication failed"),
    ).toBeTruthy();
  });
});
