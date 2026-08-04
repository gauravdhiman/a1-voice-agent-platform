/**
 * Tests for the public sign-in page (/auth/signin).
 *
 * Contract: the sign-in page must present production-ready, business-oriented
 * messaging for the "24x7 AI" brand:
 *   - Brand is "24x7 AI" (never the "CogniNets" fallback or stale name).
 *   - The left panel communicates business value ("Every call answered. Every
 *     appointment booked.") instead of the old technical fake testimonial
 *     ("voice AI workflows... CTO at TechCorp").
 *   - The sign-in form still renders.
 */
import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

// The auth pages render the real form components + ProtectedRoute wrapper; for
// these page-level messaging tests we stub both so assertions stay on the copy.
vi.mock("@/components/auth/protected-route", () => ({
  ProtectedRoute: ({ children }: { children: React.ReactNode }) => children,
}));
vi.mock("@/components/auth/signin-form", () => ({
  SignInForm: () => <div data-testid="signin-form" />,
}));

import SignInPage from "../auth/signin/page";

describe("Sign-in page (public marketing messaging)", () => {
  it("renders the 24x7 AI brand", () => {
    render(<SignInPage />);
    expect(screen.getAllByText("24x7 AI").length).toBeGreaterThan(0);
    expect(screen.queryByText(/CogniNets/i)).not.toBeInTheDocument();
  });

  it("communicates business value instead of the old technical testimonial", () => {
    render(<SignInPage />);
    expect(screen.getByText(/every call answered/i)).toBeInTheDocument();
    // Removed fabricated/technical testimonial.
    expect(screen.queryByText(/techcorp/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/voice ai workflows/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/jane doe/i)).not.toBeInTheDocument();
  });

  it("keeps the sign-in entry point", () => {
    render(<SignInPage />);
    expect(screen.getByText(/welcome back/i)).toBeInTheDocument();
    expect(screen.getByTestId("signin-form")).toBeInTheDocument();
  });
});
