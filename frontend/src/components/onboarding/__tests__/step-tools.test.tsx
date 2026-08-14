import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StepTools } from "@/components/onboarding/step-tools";

describe("StepTools", () => {
  it("describes business connections without exposing implementation terms", () => {
    render(<StepTools onNext={() => {}} onBack={() => {}} />);

    expect(
      screen.getByText(/Other business services your team uses/i),
    ).toBeInTheDocument();
    expect(screen.queryByText(/MCP|platform tools/i)).not.toBeInTheDocument();
  });
});
