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

  it("appends terms_accepted=true when signup consent is given", () => {
    expect(buildAuthorizeUrl("google", undefined, true)).toBe(
      "http://localhost:8000/api/v1/auth/google/authorize?terms_accepted=true",
    );
  });

  it("combines invitation tokens with terms acceptance", () => {
    expect(buildAuthorizeUrl("linkedin", "invite-123", true)).toBe(
      "http://localhost:8000/api/v1/auth/linkedin/authorize?invitation_token=invite-123&terms_accepted=true",
    );
  });

  it("omits terms_accepted when consent is missing", () => {
    expect(buildAuthorizeUrl("google", undefined, false)).toBe(
      "http://localhost:8000/api/v1/auth/google/authorize",
    );
    expect(buildAuthorizeUrl("google", undefined, undefined)).toBe(
      "http://localhost:8000/api/v1/auth/google/authorize",
    );
  });

  it("links to the terms-aware authorize URL when consent is passed", () => {
    render(
      <OAuthRedirectButton
        provider="google"
        text="signup_with"
        termsAccepted
      />,
    );

    const link = screen.getByTestId("google-oauth-redirect-button");
    expect(link.getAttribute("href")).toBe(
      "http://localhost:8000/api/v1/auth/google/authorize?terms_accepted=true",
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
      <OAuthRedirectButton provider="linkedin" text="signup_with" disabled />,
    );

    const link = screen.getByTestId("linkedin-oauth-redirect-button");
    expect(link).toHaveAttribute("aria-disabled", "true");
    expect(link).toHaveTextContent("Sign up with LinkedIn");
  });
});
