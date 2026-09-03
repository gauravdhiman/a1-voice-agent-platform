import React from "react";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const useSearchParamsMock = vi.fn(() => new URLSearchParams());

vi.mock("next/navigation", () => ({
  useSearchParams: () => useSearchParamsMock(),
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
}));

vi.mock("@/contexts/auth-context", () => ({
  useAuth: vi.fn(),
}));

vi.mock("@/components/auth/oauth-redirect-button", () => ({
  OAuthRedirectButton: ({
    provider,
    text,
    invitationToken,
  }: {
    provider: "google" | "linkedin";
    text: "signin_with" | "signup_with";
    invitationToken?: string;
  }) => (
    <a
      href={`http://localhost:8000/api/v1/auth/${provider}/authorize${
        invitationToken ? `?invitation_token=${invitationToken}` : ""
      }`}
    >
      {text === "signin_with"
        ? `Sign in with ${provider === "google" ? "Google" : "LinkedIn"}`
        : `Sign up with ${provider === "google" ? "Google" : "LinkedIn"}`}
    </a>
  ),
}));

import { useAuth } from "@/contexts/auth-context";
import { SignInForm } from "./signin-form";
import { SignUpForm } from "./signup-form";

describe("OAuth redirect authentication forms", () => {
  const signIn = vi.fn();
  const signUp = vi.fn();

  beforeEach(() => {
    signIn.mockReset();
    signUp.mockReset();
    useSearchParamsMock.mockReturnValue(new URLSearchParams());

    vi.mocked(useAuth).mockReturnValue({
      signIn,
      signUp,
    } as never);
  });

  it("renders backend Google redirect links during sign-in", () => {
    render(<SignInForm />);

    expect(
      screen.getByRole("link", { name: "Sign in with Google" }),
    ).toHaveAttribute(
      "href",
      "http://localhost:8000/api/v1/auth/google/authorize",
    );
  });

  it("renders backend LinkedIn redirect links during sign-in", () => {
    render(<SignInForm />);

    expect(
      screen.getByRole("link", { name: "Sign in with LinkedIn" }),
    ).toHaveAttribute(
      "href",
      "http://localhost:8000/api/v1/auth/linkedin/authorize",
    );
  });

  it("includes invitation tokens in sign-up OAuth redirect links", () => {
    useSearchParamsMock.mockReturnValue(new URLSearchParams("token=invite-token"));

    render(<SignUpForm />);

    expect(
      screen.getByRole("link", { name: "Sign up with Google" }),
    ).toHaveAttribute(
      "href",
      "http://localhost:8000/api/v1/auth/google/authorize?invitation_token=invite-token",
    );
  });
});
