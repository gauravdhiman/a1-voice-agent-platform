import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
  OAuthRedirectButton,
  buildAuthorizeUrl,
} from "./oauth-redirect-button";

describe("OAuthRedirectButton", () => {
  it("builds Google authorize URLs without invitation tokens", () => {
    expect(buildAuthorizeUrl("google")).toBe(
      "http://localhost:8000/api/v1/auth/google/authorize",
    );
  });

  it("builds LinkedIn authorize URLs with invitation tokens", () => {
    expect(buildAuthorizeUrl("linkedin", "invite-123")).toBe(
      "http://localhost:8000/api/v1/auth/linkedin/authorize?invitation_token=invite-123",
    );
  });

  it("renders a Google sign-in link", () => {
    render(<OAuthRedirectButton provider="google" text="signin_with" />);

    const link = screen.getByTestId("google-oauth-redirect-button");
    expect(link).toHaveAttribute(
      "href",
      "http://localhost:8000/api/v1/auth/google/authorize",
    );
    expect(link).toHaveTextContent("Sign in with Google");
  });

  it("renders a disabled LinkedIn sign-up link", () => {
    render(
      <OAuthRedirectButton
        provider="linkedin"
        text="signup_with"
        disabled
      />,
    );

    const link = screen.getByTestId("linkedin-oauth-redirect-button");
    expect(link).toHaveAttribute("aria-disabled", "true");
    expect(link).toHaveTextContent("Sign up with LinkedIn");
  });
});
