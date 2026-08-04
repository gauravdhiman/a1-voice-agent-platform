/**
 * Tests for the public sign-up page (/auth/signup).
 *
 * Contract: the sign-up page must present production-ready, business-oriented
 * messaging for the "24x7 AI" brand:
 *   - Brand is "24x7 AI" (never the "CogniNets" fallback or stale name).
 *   - The left panel speaks to business owners ("Set up your AI front desk in
 *     minutes", "No code. No IT...") — not developers.
 *   - Fabricated stats ("10k+ Active Users", "99.9% Uptime") are removed and
 *     replaced with truthful value bullets.
 *   - The sign-up form still renders.
 */
import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/components/auth/protected-route", () => ({
  ProtectedRoute: ({ children }: { children: React.ReactNode }) => children,
}));
vi.mock("@/components/auth/signup-form", () => ({
  SignUpForm: () => <div data-testid="signup-form" />,
}));

import SignUpPage from "../auth/signup/page";

describe("Sign-up page (public marketing messaging)", () => {
  it("renders the 24x7 AI brand", () => {
    render(<SignUpPage />);
    expect(screen.getAllByText("24x7 AI").length).toBeGreaterThan(0);
    expect(screen.queryByText(/CogniNets/i)).not.toBeInTheDocument();
  });

  it("speaks to business owners, not developers", () => {
    render(<SignUpPage />);
    expect(
      screen.getByText(/set up your ai front desk in minutes/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/no code\./i)).toBeInTheDocument();
    // Removed developer-oriented copy and fabricated stats.
    expect(screen.queryByText(/developers/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/10k/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/99\.9/i)).not.toBeInTheDocument();
    expect(
      screen.queryByText(/next-generation voice applications/i),
    ).not.toBeInTheDocument();
  });

  it("keeps the sign-up entry point", () => {
    render(<SignUpPage />);
    expect(screen.getByText(/create your free account/i)).toBeInTheDocument();
    expect(screen.getByTestId("signup-form")).toBeInTheDocument();
  });
});
