import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AgentDetailSaveBar } from "../agent-detail-save-bar";

describe("AgentDetailSaveBar", () => {
  it("keeps the save action available outside the tab content for editors", () => {
    const onSave = vi.fn();

    render(
      <AgentDetailSaveBar
        canEdit
        saving={false}
        onSave={onSave}
      />,
    );

    const saveButton = screen.getByRole("button", { name: /save changes/i });
    expect(saveButton).toBeInTheDocument();

    fireEvent.click(saveButton);
    expect(onSave).toHaveBeenCalledTimes(1);
  });

  it("does not expose a save action to read-only users", () => {
    render(
      <AgentDetailSaveBar
        canEdit={false}
        saving={false}
        onSave={vi.fn()}
      />,
    );

    expect(
      screen.queryByRole("button", { name: /save changes/i }),
    ).not.toBeInTheDocument();
  });

  it("disables the action and communicates saving state", () => {
    render(
      <AgentDetailSaveBar
        canEdit
        saving
        onSave={vi.fn()}
      />,
    );

    expect(
      screen.getByRole("button", { name: /saving/i }),
    ).toBeDisabled();
  });
});
