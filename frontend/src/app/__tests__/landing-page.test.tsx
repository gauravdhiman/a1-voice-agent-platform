/**
 * Tests for the public landing page (/).
 *
 * Contract: the landing page must present production-ready, business-oriented
 * messaging for the "24x7 AI" brand:
 *   - Brand is "24x7 AI" (never the stale "VoiceAI" name).
 *   - Hero headline sells the business outcome ("Never miss a call...").
 *   - An industries section ("Built for businesses that live on the phone")
 *     replaces the fabricated customer logos and testimonials.
 *   - Pricing is outcome-focused ("Start free") with no hardcoded dollar
 *     figures (removed $0 / $99 / Custom that could drift from Stripe).
 *   - Removed fabricated social proof (Acme Corp, TechStart, fake names).
 */
import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import LandingPage from "../page";

describe("Landing page (public marketing messaging)", () => {
  it("renders the 24x7 AI brand in the header and footer", () => {
    render(<LandingPage />);
    // Brand appears in the header nav and the footer.
    expect(screen.getAllByText("24x7 AI").length).toBeGreaterThan(0);
    // The stale hardcoded name must be gone.
    expect(screen.queryByText(/VoiceAI/i)).not.toBeInTheDocument();
  });

  it("leads with a business-outcome hero headline", () => {
    render(<LandingPage />);
    expect(
      screen.getByRole("heading", {
        level: 1,
        name: /never miss a call/i,
      }),
    ).toBeInTheDocument();
    // The "no coding required" differentiator is present in the hero.
    expect(screen.getAllByText(/no coding required/i).length).toBeGreaterThan(
      0,
    );
  });

  it("shows an industries section instead of fabricated logos/testimonials", () => {
    render(<LandingPage />);
    expect(
      screen.getByText(/built for businesses that live on the phone/i),
    ).toBeInTheDocument();
    // Fabricated social proof removed.
    expect(screen.queryByText(/acme corp/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/techstart/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/sarah chen/i)).not.toBeInTheDocument();
  });

  it("features outcome-driven value props", () => {
    render(<LandingPage />);
    expect(screen.getByText(/answer every call, 24x7/i)).toBeInTheDocument();
    expect(screen.getByText(/book & manage appointments/i)).toBeInTheDocument();
    expect(
      screen.getByText(/follow up & win customers back/i),
    ).toBeInTheDocument();
  });

  it("keeps pricing outcome-focused with no hardcoded dollar figures", () => {
    render(<LandingPage />);
    expect(screen.getAllByText(/start free/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/cancel anytime/i).length).toBeGreaterThan(0);
    expect(screen.queryByText(/\$99/)).not.toBeInTheDocument();
    expect(screen.queryByText(/\$0/)).not.toBeInTheDocument();
  });
});
