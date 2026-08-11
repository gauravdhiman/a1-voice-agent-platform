/** Tests for the shared visual treatment used by the voice preset form. */
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { PresetConfigForm } from "@/components/presets/preset-config-form";

describe("PresetConfigForm visual theme", () => {
  it("uses a layered surface and filled controls for field contrast", () => {
    render(<PresetConfigForm onChange={vi.fn()} onValidityChange={vi.fn()} />);

    expect(
      screen.getByText("Engine mode").closest(".form-surface"),
    ).not.toBeNull();
    expect(
      screen
        .getAllByRole("textbox")
        .some((field) => field.classList.contains("form-control")),
    ).toBe(true);
    expect(
      screen
        .getByText("Params")
        .closest(".form-field")
        ?.querySelector("textarea"),
    ).toHaveClass("form-control");
  });
});
