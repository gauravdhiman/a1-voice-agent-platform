/** Tests for the shared visual treatment used by the voice preset form. */
import { fireEvent, render, screen } from "@testing-library/react";
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

describe("PresetConfigForm realtime provider controls", () => {
  it("shows only supported OpenAI models, voices, and controls", () => {
    const onChange = vi.fn();
    render(
      <PresetConfigForm
        initialConfig={{
          engine_mode: "realtime",
          provider: "openai",
          model: "gpt-live-1",
          voice: "marin",
          params: {},
        }}
        onChange={onChange}
      />,
    );

    expect(screen.getAllByRole("combobox")).toHaveLength(3);
    expect(screen.getByDisplayValue("gpt-live-1")).toBeTruthy();
    expect(screen.getByDisplayValue("marin")).toBeTruthy();
    expect(screen.queryByText("Temperature")).toBeNull();
    expect(screen.queryByText("Params")).toBeNull();
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({
        provider: "openai",
        model: "gpt-live-1",
        voice: "marin",
        params: {},
      }),
    );
  });

  it("keeps Gemini's editable model and tuning controls available", () => {
    render(
      <PresetConfigForm
        initialConfig={{
          engine_mode: "realtime",
          provider: "openai",
          model: "gpt-live-1",
          voice: "marin",
          params: {},
        }}
        onChange={vi.fn()}
      />,
    );

    const provider = screen.getAllByRole("combobox")[0];
    fireEvent.change(provider, { target: { value: "google" } });

    expect(screen.getByText("Temperature")).toBeTruthy();
    expect(screen.getByText("Params")).toBeTruthy();
    expect(
      screen.getByDisplayValue("gemini-3.8-live"),
    ).toBeTruthy();
    expect(screen.getByDisplayValue("Zephyr")).toBeTruthy();
  });
});
