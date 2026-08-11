/**
 * Tests for the platform-admin voice preset create/edit drawer entry points.
 *
 * The catalog remains visible as the primary page surface; authoring and
 * editing are intentionally opened in the shared right-side Sheet pattern.
 */
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { PlatformPresetsManager } from "@/components/presets/platform-presets-manager";

const mockState = vi.hoisted(() => ({
  presets: [] as Array<Record<string, unknown>>,
}));

vi.mock("@/hooks/use-preset-queries", () => ({
  usePresets: () => ({ data: mockState.presets }),
  useCreatePreset: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useUpdatePreset: () => ({ mutateAsync: vi.fn(), isPending: false }),
  usePublishPreset: () => ({ mutate: vi.fn(), isPending: false }),
  useUpdateDefaultPreset: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

vi.mock("@/components/presets/preset-config-form", () => ({
  PresetConfigForm: () => <div data-testid="preset-config-form" />,
}));

vi.mock("@/components/presets/preset-delete-dialog", () => ({
  PresetDeleteDialog: () => null,
}));

const authoredPreset = {
  id: "preset-1",
  name: "Support Voice",
  description: "A calm voice for support calls.",
  config: { engine_mode: "realtime" },
  is_published: false,
  preset_type: "realtime" as const,
  is_default: false,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

describe("PlatformPresetsManager drawer entry points", () => {
  beforeEach(() => {
    mockState.presets = [];
  });

  it("opens a right-side drawer from Create new preset", async () => {
    const { userEvent } = await import("@testing-library/user-event");
    const user = userEvent.setup();
    render(<PlatformPresetsManager />);

    expect(
      screen.getByRole("button", { name: /Create new preset/i }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /Author preset/i }),
    ).not.toBeInTheDocument();

    await user.click(
      screen.getByRole("button", { name: /Create new preset/i }),
    );

    expect(
      await screen.findByRole("heading", { name: /Create voice preset/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("opens the same drawer for editing an existing preset", async () => {
    const { userEvent } = await import("@testing-library/user-event");
    const user = userEvent.setup();
    mockState.presets = [authoredPreset];
    render(<PlatformPresetsManager />);

    await user.click(screen.getByRole("button", { name: "Edit" }));

    expect(
      await screen.findByRole("heading", { name: /Edit voice preset/i }),
    ).toBeInTheDocument();
    expect(screen.getByDisplayValue("Support Voice")).toBeInTheDocument();
  });
});
