import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SkipOnboardingButton } from "@/components/onboarding/skip-onboarding-button";

describe("SkipOnboardingButton", () => {
  it("calls onSkip when clicked", () => {
    const onSkip = vi.fn();
    render(<SkipOnboardingButton onSkip={onSkip} />);

    fireEvent.click(screen.getByTestId("skip-onboarding"));
    expect(onSkip).toHaveBeenCalledTimes(1);
  });

  it("disables the control while loading", () => {
    render(<SkipOnboardingButton onSkip={vi.fn()} loading />);

    const button = screen.getByTestId("skip-onboarding");
    expect(button).toBeDisabled();
    expect(button.textContent).toMatch(/Skipping/i);
  });
});
