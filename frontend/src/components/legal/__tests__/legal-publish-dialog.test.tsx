import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { toast } from "sonner";

vi.mock("@/services/legal-doc-service", () => ({
  legalDocService: {
    publishVersion: vi.fn(),
  },
}));

import { legalDocService } from "@/services/legal-doc-service";
import { LegalPublishDialog } from "../legal-publish-dialog";
import type {
  LegalDocumentVersionDetail,
  LegalPublishResult,
} from "@/types/legal-docs";

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

const publishResult: LegalPublishResult = {
  version: {
    ...draftVersion,
    status: "published",
    is_current: true,
    published_at: "2026-10-12T00:00:00Z",
    published_by: "22222222-2222-4222-8222-222222222222",
  },
  publish_event_id: "33333333-3333-4333-8333-333333333333",
  notified_count: 42,
  dispatch_id: "44444444-4444-4444-8444-444444444444",
};

describe("LegalPublishDialog", () => {
  const publishVersionMock = vi.mocked(legalDocService.publishVersion);

  beforeEach(() => {
    publishVersionMock.mockReset();
    publishVersionMock.mockResolvedValue(publishResult);
  });

  it("checks the notify-users checkbox by default", () => {
    render(
      <LegalPublishDialog
        version={draftVersion}
        open
        onOpenChange={vi.fn()}
        onPublished={vi.fn()}
      />,
    );

    const notifyCheckbox = screen.getByLabelText(
      "Notify all signed-up users by email",
    ) as HTMLInputElement;

    expect(notifyCheckbox.checked).toBe(true);
  });

  it("sends notify_users=true and reports the notified count on publish", async () => {
    const user = userEvent.setup();
    const onOpenChange = vi.fn();
    const onPublished = vi.fn();

    render(
      <LegalPublishDialog
        version={draftVersion}
        open
        onOpenChange={onOpenChange}
        onPublished={onPublished}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Publish" }));

    await waitFor(() => {
      expect(publishVersionMock).toHaveBeenCalledWith(draftVersion.id, {
        notify_users: true,
      });
    });
    await waitFor(() => {
      expect(onPublished).toHaveBeenCalledWith(publishResult);
    });
    expect(onOpenChange).toHaveBeenCalledWith(false);
    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith(
        "Published version 3",
        expect.objectContaining({
          description: "Notified 42 users by email.",
        }),
      );
    });
  });

  it("sends notify_users=false when the checkbox is unchecked", async () => {
    const user = userEvent.setup();

    render(
      <LegalPublishDialog
        version={draftVersion}
        open
        onOpenChange={vi.fn()}
        onPublished={vi.fn()}
      />,
    );

    const notifyCheckbox = screen.getByLabelText(
      "Notify all signed-up users by email",
    ) as HTMLInputElement;
    await user.click(notifyCheckbox);
    expect(notifyCheckbox.checked).toBe(false);

    await user.click(screen.getByRole("button", { name: "Publish" }));

    await waitFor(() => {
      expect(publishVersionMock).toHaveBeenCalledWith(draftVersion.id, {
        notify_users: false,
      });
    });
  });

  it("shows the no-users-notified message when nobody was notified", async () => {
    const user = userEvent.setup();
    publishVersionMock.mockResolvedValue({
      ...publishResult,
      notified_count: 0,
      dispatch_id: null,
    });

    render(
      <LegalPublishDialog
        version={draftVersion}
        open
        onOpenChange={vi.fn()}
        onPublished={vi.fn()}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Publish" }));

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith(
        "Published version 3",
        expect.objectContaining({
          description: "No users were notified.",
        }),
      );
    });
  });

  it("resets the notify checkbox to checked each time the dialog opens", async () => {
    const user = userEvent.setup();
    const { rerender } = render(
      <LegalPublishDialog
        version={draftVersion}
        open
        onOpenChange={vi.fn()}
        onPublished={vi.fn()}
      />,
    );

    const notifyCheckbox = screen.getByLabelText(
      "Notify all signed-up users by email",
    ) as HTMLInputElement;
    await user.click(notifyCheckbox);
    expect(notifyCheckbox.checked).toBe(false);

    rerender(
      <LegalPublishDialog
        version={draftVersion}
        open={false}
        onOpenChange={vi.fn()}
        onPublished={vi.fn()}
      />,
    );
    rerender(
      <LegalPublishDialog
        version={draftVersion}
        open
        onOpenChange={vi.fn()}
        onPublished={vi.fn()}
      />,
    );

    // Radix unmounts the dialog content while closed, so re-query the
    // checkbox rendered by the reopened dialog.
    const reopenedCheckbox = screen.getByLabelText(
      "Notify all signed-up users by email",
    ) as HTMLInputElement;
    await waitFor(() => {
      expect(reopenedCheckbox.checked).toBe(true);
    });
  });

  it("surfaces publish failures without calling onPublished", async () => {
    const user = userEvent.setup();
    publishVersionMock.mockRejectedValue(new Error("Network down"));
    const onPublished = vi.fn();

    render(
      <LegalPublishDialog
        version={draftVersion}
        open
        onOpenChange={vi.fn()}
        onPublished={onPublished}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Publish" }));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith(
        "Failed to publish version",
        expect.objectContaining({ description: "Network down" }),
      );
    });
    expect(onPublished).not.toHaveBeenCalled();
  });
});
