/**
 * Render tests for `PresetPicker` (white-label catalog + readiness).
 *
 * Contract: org admins see name + description + Ready/Setup required badges only
 * (no Realtime/Pipeline or provider names). Selecting a not-ready profile shows
 * generic setup guidance without naming underlying providers.
 */
import * as React from "react";
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

import { PresetPicker } from "@/components/agents/preset-picker";
import { DEFAULT_PRESET_DISPLAY } from "@/types/preset";
import type { PresetCatalogResponse } from "@/types/preset";

const mockUsePresetCatalog = vi.fn();

vi.mock("@/hooks/use-preset-queries", () => ({
  usePresetCatalog: (...args: unknown[]) => mockUsePresetCatalog(...args),
}));

const ORG_ID = "org-1";

function makeCatalog(
  over: Partial<PresetCatalogResponse> = {},
): PresetCatalogResponse {
  return {
    presets: [],
    default_is_ready: true,
    credentials_self_service: true,
    ...over,
  };
}

describe("PresetPicker", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the system-default option with shared display name and readiness badge", () => {
    mockUsePresetCatalog.mockReturnValue({
      data: makeCatalog({ default_is_ready: true }),
      isLoading: false,
    });

    render(
      <PresetPicker organizationId={ORG_ID} value={null} onChange={() => {}} />,
    );

    expect(screen.getByText(DEFAULT_PRESET_DISPLAY.name)).toBeInTheDocument();
    expect(
      screen.getByText(DEFAULT_PRESET_DISPLAY.description),
    ).toBeInTheDocument();
    expect(screen.queryByText("Realtime")).not.toBeInTheDocument();
    expect(screen.queryByText("Pipeline")).not.toBeInTheDocument();
    expect(screen.getAllByText("Ready").length).toBeGreaterThanOrEqual(1);
  });

  it("renders published profiles with Ready or Setup required badges (no engine badges)", () => {
    mockUsePresetCatalog.mockReturnValue({
      data: makeCatalog({
        presets: [
          {
            id: "p-ready",
            name: "Professional Voice",
            description: "Warm tone for support.",
            is_ready: true,
          },
          {
            id: "p-setup",
            name: "Enterprise Voice",
            description: "Low latency.",
            is_ready: false,
          },
        ],
      }),
      isLoading: false,
    });

    render(
      <PresetPicker organizationId={ORG_ID} value={null} onChange={() => {}} />,
    );

    expect(screen.getByText("Professional Voice")).toBeInTheDocument();
    expect(screen.getByText("Enterprise Voice")).toBeInTheDocument();
    expect(screen.getByText("Setup required")).toBeInTheDocument();
    expect(screen.queryByText("Pipeline")).not.toBeInTheDocument();
    expect(screen.queryByText("Realtime")).not.toBeInTheDocument();
  });

  it("shows generic setup callout when a not-ready profile is selected", () => {
    mockUsePresetCatalog.mockReturnValue({
      data: makeCatalog({
        presets: [
          {
            id: "p-setup",
            name: "Enterprise Voice",
            description: null,
            is_ready: false,
          },
        ],
        credentials_self_service: true,
      }),
      isLoading: false,
    });

    render(
      <PresetPicker
        organizationId={ORG_ID}
        value="p-setup"
        onChange={() => {}}
      />,
    );

    expect(
      screen.getByText(/needs a little more setup before your agent can use it/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/Open voice setup/i)).toBeInTheDocument();
    expect(screen.queryByText(/API credentials/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Deepgram/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/OpenAI/i)).not.toBeInTheDocument();
  });

  it("does not show setup callout for system default even when API reports not ready", () => {
    mockUsePresetCatalog.mockReturnValue({
      data: makeCatalog({
        default_is_ready: false,
        credentials_self_service: true,
      }),
      isLoading: false,
    });

    render(
      <PresetPicker organizationId={ORG_ID} value={null} onChange={() => {}} />,
    );

    expect(
      screen.queryByText(/needs a little more setup before your agent can use it/i),
    ).not.toBeInTheDocument();
    expect(screen.getByText("Ready")).toBeInTheDocument();
  });

  it("shows contact-admin copy when credentials are not self-service", () => {
    mockUsePresetCatalog.mockReturnValue({
      data: makeCatalog({
        presets: [
          {
            id: "p-managed",
            name: "Managed Profile",
            description: null,
            is_ready: false,
          },
        ],
        default_is_ready: true,
        credentials_self_service: false,
      }),
      isLoading: false,
    });

    render(
      <PresetPicker
        organizationId={ORG_ID}
        value="p-managed"
        onChange={() => {}}
      />,
    );

    expect(
      screen.getByText(/contact your account administrator/i),
    ).toBeInTheDocument();
    expect(screen.queryByText(/Open voice setup/i)).not.toBeInTheDocument();
  });

  it("fires onChange(null) when the system-default option is selected", () => {
    mockUsePresetCatalog.mockReturnValue({
      data: makeCatalog(),
      isLoading: false,
    });
    const onChange = vi.fn();

    render(
      <PresetPicker organizationId={ORG_ID} value="p-1" onChange={onChange} />,
    );

    const defaultOption = screen
      .getByText(DEFAULT_PRESET_DISPLAY.name)
      .closest("[role='radio']");
    expect(defaultOption).not.toBeNull();
    (defaultOption as HTMLElement).click();
    expect(onChange).toHaveBeenCalledWith(null);
  });
});
