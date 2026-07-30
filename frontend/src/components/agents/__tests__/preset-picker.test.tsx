/**
 * Render tests for `PresetPicker` (Phase 4 follow-up).
 *
 * Contract (owner requirement): the `preset_id = null` fallback option must
 * show the **same name + description** as the platform-admin Voice Presets page
 * (`DEFAULT_PRESET_DISPLAY` — "System Default" / "Used when an agent has no
 * voice profile selected."), with NO type badge (don't leak the underlying
 * engine). Published presets render below it, each with a Realtime/Pipeline
 * badge. Selecting the default fires `onChange(null)`.
 */
import * as React from "react";
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

import { PresetPicker } from "@/components/agents/preset-picker";
import { DEFAULT_PRESET_DISPLAY } from "@/types/preset";
import type { Preset } from "@/types/preset";

const mockUsePresets = vi.fn();

vi.mock("@/hooks/use-preset-queries", () => ({
  usePresets: (...args: unknown[]) => mockUsePresets(...args),
}));

function makePreset(over: Partial<Preset> = {}): Preset {
  return {
    id: "p-1",
    name: "Pipeline (Deepgram+OpenAI+Cartesia)",
    description: "Modular STT/LLM/TTS cascade preset.",
    config: {},
    is_published: true,
    preset_type: "pipeline",
    is_default: false,
    created_at: "2026-07-29T00:00:00Z",
    updated_at: "2026-07-29T00:00:00Z",
    ...over,
  };
}

describe("PresetPicker", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the system-default fallback option with the platform-page name + description and no type badge", () => {
    mockUsePresets.mockReturnValue({ data: [], isLoading: false });

    render(<PresetPicker value={null} onChange={() => {}} />);

    // Name + description match the platform page (shared constant).
    expect(screen.getByText(DEFAULT_PRESET_DISPLAY.name)).toBeInTheDocument();
    expect(
      screen.getByText(DEFAULT_PRESET_DISPLAY.description),
    ).toBeInTheDocument();

    // The default option carries no Realtime/Pipeline badge — the underlying
    // engine is a platform-admin concern, not shown to org users.
    expect(screen.queryByText("Realtime")).not.toBeInTheDocument();
    expect(screen.queryByText("Pipeline")).not.toBeInTheDocument();
  });

  it("renders published presets below the default, each with a type badge", () => {
    mockUsePresets.mockReturnValue({
      data: [
        makePreset({
          id: "p-pipe",
          name: "Pipeline (Deepgram+OpenAI+Cartesia)",
          preset_type: "pipeline",
        }),
        makePreset({
          id: "p-rt",
          name: "Realtime (Gemini) default",
          preset_type: "realtime",
        }),
      ],
      isLoading: false,
    });

    render(<PresetPicker value={null} onChange={() => {}} />);

    expect(screen.getByText("Pipeline (Deepgram+OpenAI+Cartesia)")).toBeInTheDocument();
    expect(screen.getByText("Realtime (Gemini) default")).toBeInTheDocument();
    // Both published presets carry their type badge.
    const badges = screen.getAllByText("Pipeline");
    expect(badges.length).toBe(1); // the preset's badge
    expect(screen.getByText("Realtime")).toBeInTheDocument();
  });

  it("fires onChange(null) when the system-default option is selected", () => {
    mockUsePresets.mockReturnValue({ data: [], isLoading: false });
    const onChange = vi.fn();

    render(<PresetPicker value={null} onChange={onChange} />);

    // The default option row is a radio labeled with its name.
    const defaultOption = screen.getByText(DEFAULT_PRESET_DISPLAY.name).closest(
      "[role='radio']",
    );
    expect(defaultOption).not.toBeNull();
    (defaultOption as HTMLElement).click();
    expect(onChange).toHaveBeenCalledWith(null);
  });
});