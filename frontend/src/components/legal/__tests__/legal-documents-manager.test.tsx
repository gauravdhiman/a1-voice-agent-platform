import React from "react";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { toast } from "sonner";

vi.mock("@/services/legal-doc-service", () => ({
  legalDocService: {
    listVersions: vi.fn(),
    getVersion: vi.fn(),
    createDraft: vi.fn(),
    updateDraft: vi.fn(),
    deleteDraft: vi.fn(),
    publishVersion: vi.fn(),
    getPublishedDocument: vi.fn(),
  },
}));

import { LegalDocumentsManager } from "../legal-documents-manager";
import { legalDocService } from "@/services/legal-doc-service";
import type {
  LegalDocumentVersionDetail,
  LegalDocumentVersionSummary,
} from "@/types/legal-docs";

const publishedVersion: LegalDocumentVersionSummary = {
  id: "22222222-2222-4222-8222-222222222222",
  document_key: "terms",
  version_number: 2,
  status: "published",
  is_current: true,
  summary_of_changes: "Clarify refund policy",
  published_at: "2026-10-01T00:00:00Z",
  published_by: null,
  created_at: "2026-09-30T00:00:00Z",
  updated_at: "2026-10-01T00:00:00Z",
};

const draftVersion: LegalDocumentVersionDetail = {
  id: "11111111-1111-4111-8111-111111111111",
  document_key: "terms",
  version_number: 3,
  status: "draft",
  is_current: false,
  summary_of_changes: "Clarify data retention windows",
  published_at: null,
  published_by: null,
  created_at: "2026-10-10T00:00:00Z",
  updated_at: "2026-10-11T00:00:00Z",
  content_markdown: "# Terms & Conditions\n\nUpdated body.",
};

const listVersionsMock = vi.mocked(legalDocService.listVersions);
const getVersionMock = vi.mocked(legalDocService.getVersion);
const updateDraftMock = vi.mocked(legalDocService.updateDraft);
const deleteDraftMock = vi.mocked(legalDocService.deleteDraft);

describe("LegalDocumentsManager", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listVersionsMock.mockResolvedValue([publishedVersion, draftVersion]);
  });

  it("opens a right drawer with version content from the View action", async () => {
    getVersionMock.mockResolvedValue({
      ...publishedVersion,
      content_markdown: "# Published body\n\nClause one.",
    });
    const user = userEvent.setup();
    render(<LegalDocumentsManager />);

    await waitFor(() => {
      expect(screen.getByText("v2")).toBeTruthy();
    });

    const viewButtons = screen.getAllByRole("button", { name: "View" });
    expect(viewButtons.length).toBe(2);
    await user.click(viewButtons[0]);

    await waitFor(() => {
      expect(getVersionMock).toHaveBeenCalledWith(publishedVersion.id);
    });
    await waitFor(() => {
      expect(screen.getByText("Clause one.")).toBeTruthy();
    });

    const drawer = screen.getByRole("dialog");
    expect(within(drawer).getByText("Published body")).toBeTruthy();
    expect(within(drawer).getByText("published")).toBeTruthy();
    expect(within(drawer).getByText("Clarify refund policy")).toBeTruthy();
    // Drawer markdown uses the public-page prose classes with the
    // theme-scoped dark variant (not a forced light-text `prose-invert`).
    const md = within(drawer).getByText("Clause one.").closest("div");
    expect(md).not.toBeNull();
    const classes = (md as HTMLElement).className.split(" ");
    expect(classes).toContain("dark:prose-invert");
    expect(classes).not.toContain("prose-invert");
  });

  it("previews unsaved editor content in a right drawer", async () => {
    getVersionMock.mockResolvedValue(draftVersion);
    const user = userEvent.setup();
    render(<LegalDocumentsManager />);

    await waitFor(() => {
      expect(screen.getByText("v3")).toBeTruthy();
    });

    // Open the draft editor from the draft row.
    await user.click(
      screen.getAllByRole("button", { name: "Continue draft" })[0],
    );
    await waitFor(() => {
      expect(screen.getByLabelText("Content (Markdown)")).toBeTruthy();
    });

    const textarea = screen.getByLabelText("Content (Markdown)");
    await user.clear(textarea);
    await user.type(textarea, "Unsaved preview body.");

    await user.click(screen.getAllByRole("button", { name: "Preview" })[0]);

    await waitFor(() => {
      const drawer = screen.getByRole("dialog");
      expect(within(drawer).getByText("Unsaved preview body.")).toBeTruthy();
    });
    // Preview renders the live editor state — nothing was saved to the API.
    expect(updateDraftMock).not.toHaveBeenCalled();
  });

  it("closes the delete dialog and removes the row after a successful delete", async () => {
    getVersionMock.mockResolvedValue(draftVersion);
    deleteDraftMock.mockResolvedValue(undefined);
    listVersionsMock
      .mockResolvedValueOnce([publishedVersion, draftVersion])
      .mockResolvedValueOnce([publishedVersion]);
    const user = userEvent.setup();
    render(<LegalDocumentsManager />);

    await waitFor(() => {
      expect(screen.getByText("v3")).toBeTruthy();
    });

    await user.click(
      screen.getAllByRole("button", { name: "Delete draft" })[0],
    );

    const dialog = await screen.findByRole("dialog");
    const confirmButton = within(dialog).getByRole("button", {
      name: "Delete draft",
    });
    expect((confirmButton as HTMLButtonElement).disabled).toBe(true);
    await user.type(within(dialog).getByPlaceholderText("Delete"), "Delete");
    expect((confirmButton as HTMLButtonElement).disabled).toBe(false);
    await user.click(confirmButton);

    await waitFor(() => {
      expect(deleteDraftMock).toHaveBeenCalledWith(draftVersion.id);
    });
    await waitFor(() => {
      expect(screen.queryByRole("dialog")).toBeNull();
    });
    expect(vi.mocked(toast.success)).toHaveBeenCalledWith("Draft deleted");
    await waitFor(() => {
      expect(screen.queryByText("v3")).toBeNull();
    });
  });
});
