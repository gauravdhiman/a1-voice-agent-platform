/**
 * Tests for the platform-admin voice preset create/edit drawer entry points.
 *
 * The catalog remains visible as the primary page surface; authoring and
 * editing are intentionally opened in the shared right-side Sheet pattern.
 */
import { act, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { PlatformPresetsManager } from "@/components/presets/platform-presets-manager";

const mockState = vi.hoisted(() => ({
  presets: [] as Array<Record<string, unknown>>,
  configFormInitialConfig: null as Record<string, unknown> | null,
  configFormOnChange: vi.fn(),
  configFormOnValidityChange: vi.fn(),
  createPreset: vi.fn(),
  updatePreset: vi.fn(),
  publishPreset: vi.fn(),
  updateDefaultPreset: vi.fn(),
}));

vi.mock("@/hooks/use-preset-queries", () => ({
  usePresets: () => ({ data: mockState.presets }),
  useCreatePreset: () => ({
    mutateAsync: mockState.createPreset,
    isPending: false,
  }),
  useUpdatePreset: () => ({
    mutateAsync: mockState.updatePreset,
    isPending: false,
  }),
  usePublishPreset: () => ({
    mutate: mockState.publishPreset,
    isPending: false,
  }),
  useUpdateDefaultPreset: () => ({
    mutateAsync: mockState.updateDefaultPreset,
    isPending: false,
  }),
}));

vi.mock("@/components/presets/preset-config-form", () => ({
  PresetConfigForm: ({
    initialConfig,
    onChange,
    onValidityChange,
  }: {
    initialConfig?: Record<string, unknown> | null;
    onChange: (config: Record<string, unknown>) => void;
    onValidityChange?: (valid: boolean) => void;
  }) => {
    mockState.configFormInitialConfig = initialConfig ?? null;
    mockState.configFormOnChange = onChange;
    mockState.configFormOnValidityChange = onValidityChange ?? vi.fn();
    return <div data-testid="preset-config-form" />;
  },
}));

vi.mock("@/components/presets/preset-delete-dialog", () => ({
  PresetDeleteDialog: ({
    onOpenChange,
    onDeleted,
    preset,
  }: {
    onOpenChange: (open: boolean) => void;
    onDeleted: () => void;
    preset: { name: string };
  }) => (
    <div data-testid="preset-delete-dialog">
      <span>{preset.name}</span>
      <button type="button" onClick={() => onOpenChange(false)}>
        Close delete dialog
      </button>
      <button type="button" onClick={onDeleted}>
        Confirm delete
      </button>
    </div>
  ),
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
    mockState.configFormInitialConfig = null;
    mockState.configFormOnChange = vi.fn();
    mockState.configFormOnValidityChange = vi.fn();
    mockState.createPreset.mockReset();
    mockState.createPreset.mockResolvedValue(authoredPreset);
    mockState.updatePreset.mockReset();
    mockState.updatePreset.mockResolvedValue(authoredPreset);
    mockState.publishPreset.mockReset();
    mockState.updateDefaultPreset.mockReset();
    mockState.updateDefaultPreset.mockResolvedValue(authoredPreset);
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

  it("copies an existing preset into a new draft with its editable fields", async () => {
    const { userEvent } = await import("@testing-library/user-event");
    const user = userEvent.setup();
    mockState.presets = [authoredPreset];
    render(<PlatformPresetsManager />);

    await user.click(
      screen.getByRole("button", { name: "Copy Support Voice" }),
    );

    expect(
      await screen.findByRole("heading", { name: /Create voice preset/i }),
    ).toBeInTheDocument();
    expect(screen.getByDisplayValue("Copy of Support Voice")).toBeInTheDocument();
    expect(
      screen.getByDisplayValue("A calm voice for support calls."),
    ).toBeInTheDocument();
    expect(mockState.configFormInitialConfig).toEqual(authoredPreset.config);

    await user.click(screen.getByRole("button", { name: "Save draft" }));

    expect(mockState.createPreset).toHaveBeenCalledWith({
      name: "Copy of Support Voice",
      description: "A calm voice for support calls.",
      config: authoredPreset.config,
      is_published: false,
    });
  });

  it("generates a numbered copy name when the default copy already exists", async () => {
    const { userEvent } = await import("@testing-library/user-event");
    const user = userEvent.setup();
    mockState.presets = [
      authoredPreset,
      { ...authoredPreset, id: "preset-2", name: "Copy of Support Voice" },
    ];
    render(<PlatformPresetsManager />);

    await user.click(
      screen.getByRole("button", { name: "Copy Support Voice" }),
    );

    expect(
      await screen.findByDisplayValue("Copy of Support Voice (2)"),
    ).toBeInTheDocument();
  });

  it("can copy the system default using the shared author drawer", async () => {
    const { userEvent } = await import("@testing-library/user-event");
    const user = userEvent.setup();
    const defaultPreset = {
      ...authoredPreset,
      id: "preset-default",
      name: "System Default",
      description: null,
      is_default: true,
    };
    mockState.presets = [defaultPreset];
    render(<PlatformPresetsManager />);

    await user.click(
      screen.getByRole("button", { name: "Copy System Default" }),
    );

    expect(
      await screen.findByDisplayValue("Copy of System Default"),
    ).toBeInTheDocument();
    expect(
      screen.getByDisplayValue(
        "Used when an agent has no voice profile selected. The voice profile will use your plan's call credits.",
      ),
      ).toBeInTheDocument();
  });

  it("shows the empty catalog state when no presets exist", () => {
    render(<PlatformPresetsManager />);

    expect(
      screen.getByText("No voice presets yet. Author a preset to get started."),
    ).toBeInTheDocument();
  });

  it("publishes, unpublishes, and opens the delete dialog for catalog rows", async () => {
    const { userEvent } = await import("@testing-library/user-event");
    const user = userEvent.setup();
    const publishedPreset = { ...authoredPreset, is_published: true };
    const draftPreset = {
      ...authoredPreset,
      id: "preset-draft",
      name: "Draft Voice",
      description: null,
      is_published: false,
      preset_type: "pipeline" as const,
    };
    mockState.presets = [publishedPreset, draftPreset];
    render(<PlatformPresetsManager />);

    await user.click(screen.getByRole("button", { name: "Unpublish" }));
    expect(mockState.publishPreset).toHaveBeenCalledWith({
      presetId: publishedPreset.id,
      published: false,
    });

    await user.click(screen.getByRole("button", { name: "Publish" }));
    expect(mockState.publishPreset).toHaveBeenCalledWith({
      presetId: draftPreset.id,
      published: true,
    });

    await user.click(screen.getAllByRole("button", { name: "Delete" })[0]);
    expect(screen.getByTestId("preset-delete-dialog")).toHaveTextContent(
      "Support Voice",
    );
    await user.click(
      screen.getByRole("button", { name: "Close delete dialog" }),
    );
    expect(screen.queryByTestId("preset-delete-dialog")).not.toBeInTheDocument();

    await user.click(screen.getAllByRole("button", { name: "Delete" })[0]);
    await user.click(screen.getByRole("button", { name: "Confirm delete" }));
    expect(screen.queryByTestId("preset-delete-dialog")).not.toBeInTheDocument();
  });

  it("saves a new preset as either a draft or a published preset", async () => {
    const { userEvent } = await import("@testing-library/user-event");
    const user = userEvent.setup();
    render(<PlatformPresetsManager />);

    await user.click(screen.getByRole("button", { name: /Create new preset/i }));
    await user.type(screen.getByLabelText(/Name/), "Draft Voice");
    await user.type(
      screen.getByLabelText(/Description/),
      "A draft voice profile.",
    );
    act(() => {
      mockState.configFormOnChange(authoredPreset.config);
      mockState.configFormOnValidityChange(true);
    });
    await user.click(screen.getByRole("button", { name: "Save draft" }));

    expect(mockState.createPreset).toHaveBeenNthCalledWith(1, {
      name: "Draft Voice",
      description: "A draft voice profile.",
      config: authoredPreset.config,
      is_published: false,
    });

    await user.click(screen.getByRole("button", { name: /Create new preset/i }));
    await user.type(screen.getByLabelText(/Name/), "Published Voice");
    act(() => {
      mockState.configFormOnChange(authoredPreset.config);
      mockState.configFormOnValidityChange(true);
    });
    await user.click(screen.getByRole("button", { name: "Publish" }));

    expect(mockState.createPreset).toHaveBeenNthCalledWith(2, {
      name: "Published Voice",
      description: null,
      config: authoredPreset.config,
      is_published: true,
    });
  });

  it("shows a validation error when a named preset has no config", async () => {
    const { userEvent } = await import("@testing-library/user-event");
    const user = userEvent.setup();
    render(<PlatformPresetsManager />);

    await user.click(screen.getByRole("button", { name: /Create new preset/i }));
    await user.type(screen.getByLabelText(/Name/), "Missing Config Voice");
    await user.click(screen.getByRole("button", { name: "Save draft" }));

    expect(
      await screen.findByText("Fix the invalid params JSON before saving."),
    ).toBeInTheDocument();
    expect(mockState.createPreset).not.toHaveBeenCalled();
  });

  it("updates an existing preset through the edit drawer", async () => {
    const { userEvent } = await import("@testing-library/user-event");
    const user = userEvent.setup();
    mockState.presets = [authoredPreset];
    render(<PlatformPresetsManager />);

    await user.click(screen.getByRole("button", { name: "Edit" }));
    await user.clear(screen.getByLabelText(/Name/));
    await user.type(screen.getByLabelText(/Name/), "Updated Support Voice");
    act(() => {
      mockState.configFormOnChange(authoredPreset.config);
      mockState.configFormOnValidityChange(true);
    });
    await user.click(screen.getByRole("button", { name: "Save draft" }));

    expect(mockState.updatePreset).toHaveBeenCalledWith({
      presetId: authoredPreset.id,
      payload: {
        name: "Updated Support Voice",
        description: authoredPreset.description,
        config: authoredPreset.config,
        is_published: false,
      },
    });
  });

  it("keeps the author drawer open and shows a save error", async () => {
    const { userEvent } = await import("@testing-library/user-event");
    const user = userEvent.setup();
    mockState.presets = [authoredPreset];
    mockState.createPreset.mockRejectedValue(new Error("Preset already exists."));
    render(<PlatformPresetsManager />);

    await user.click(
      screen.getByRole("button", { name: "Copy Support Voice" }),
    );
    await user.click(screen.getByRole("button", { name: "Save draft" }));

    expect(await screen.findByText("Preset already exists.")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /Create voice preset/i }),
    ).toBeInTheDocument();
  });

  it("saves the system default through its config-only path", async () => {
    const { userEvent } = await import("@testing-library/user-event");
    const user = userEvent.setup();
    const defaultPreset = {
      ...authoredPreset,
      id: "preset-default",
      name: "System Default",
      is_default: true,
    };
    mockState.presets = [defaultPreset];
    render(<PlatformPresetsManager />);

    await user.click(screen.getByRole("button", { name: "Edit config" }));
    await user.click(screen.getByRole("button", { name: "Save config" }));

    expect(mockState.updateDefaultPreset).toHaveBeenCalledWith(
      authoredPreset.config,
    );
    expect(screen.getByText("Voice preset catalog")).toBeInTheDocument();
  });

  it("shows a system-default save error without closing the drawer", async () => {
    const { userEvent } = await import("@testing-library/user-event");
    const user = userEvent.setup();
    const defaultPreset = {
      ...authoredPreset,
      id: "preset-default",
      name: "System Default",
      is_default: true,
    };
    mockState.presets = [defaultPreset];
    mockState.updateDefaultPreset.mockRejectedValue(
      new Error("Default update failed."),
    );
    render(<PlatformPresetsManager />);

    await user.click(screen.getByRole("button", { name: "Edit config" }));
    await user.click(screen.getByRole("button", { name: "Save config" }));

    expect(await screen.findByText("Default update failed.")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /Edit system default/i }),
    ).toBeInTheDocument();
  });

  it("returns to the catalog when the author drawer is closed", async () => {
    const { userEvent } = await import("@testing-library/user-event");
    const user = userEvent.setup();
    render(<PlatformPresetsManager initialView="author" />);

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Close" }));

    expect(screen.getByText("Voice preset catalog")).toBeInTheDocument();
  });
});
