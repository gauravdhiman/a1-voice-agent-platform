import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const getPublishedDocumentMock = vi.hoisted(() => vi.fn());

vi.mock("@/services/legal-doc-service", () => ({
  legalDocService: {
    getPublishedDocument: getPublishedDocumentMock,
  },
}));

import { LegalDocumentPage } from "../legal-document-page";
import type { LegalDocumentPublic } from "@/types/legal-docs";

const publishedTerms: LegalDocumentPublic = {
  document_key: "terms",
  title: "Terms & Conditions",
  version_number: 2,
  content_markdown: "# Heading\n\nBody text",
  published_at: "2026-10-01T00:00:00Z",
};

describe("LegalDocumentPage", () => {
  beforeEach(() => {
    getPublishedDocumentMock.mockReset();
    getPublishedDocumentMock.mockResolvedValue(publishedTerms);
  });

  it("renders the published markdown with version and published date", async () => {
    render(
      <LegalDocumentPage
        documentKey="terms"
        heading="Terms & Conditions"
        unavailableMessage="The Terms & Conditions are not available right now."
      />,
    );

    await waitFor(() => {
      expect(screen.getByText("Body text")).toBeTruthy();
    });

    expect(getPublishedDocumentMock).toHaveBeenCalledWith("terms");
    expect(screen.getByText("Heading")).toBeTruthy();
    expect(
      screen.getByRole("heading", { level: 1, name: "Terms & Conditions" }),
    ).toBeTruthy();
    expect(screen.getByText(/Version 2/)).toBeTruthy();
    // Mirror the component's date formatting so the assertion is
    // timezone-independent.
    const expectedDate = new Date("2026-10-01T00:00:00Z").toLocaleDateString(
      "en-US",
      { year: "numeric", month: "long", day: "numeric" },
    );
    expect(
      screen.getByText(new RegExp(`Published ${expectedDate}`)),
    ).toBeTruthy();
    expect(
      screen.queryByText("The Terms & Conditions are not available right now."),
    ).toBeNull();
  });

  it("shows the unavailable message when no published version exists", async () => {
    getPublishedDocumentMock.mockRejectedValue({ status: 404 });

    render(
      <LegalDocumentPage
        documentKey="privacy"
        heading="Privacy Policy"
        unavailableMessage="The Privacy Policy is not available right now."
      />,
    );

    await waitFor(() => {
      expect(
        screen.getByText("The Privacy Policy is not available right now."),
      ).toBeTruthy();
    });
    expect(screen.queryByText("Please try again later.")).toBeNull();
  });

  it("appends a retry hint when the load fails unexpectedly", async () => {
    getPublishedDocumentMock.mockRejectedValue({ status: 500 });

    render(
      <LegalDocumentPage
        documentKey="terms"
        heading="Terms & Conditions"
        unavailableMessage="The Terms & Conditions are not available right now."
      />,
    );

    await waitFor(() => {
      expect(
        screen.getByText(
          "The Terms & Conditions are not available right now. Please try again later.",
        ),
      ).toBeTruthy();
    });
  });

  it("scopes prose colors to the dark theme instead of forcing light text", async () => {
    render(
      <LegalDocumentPage
        documentKey="terms"
        heading="Terms & Conditions"
        unavailableMessage="The Terms & Conditions are not available right now."
      />,
    );

    await waitFor(() => {
      expect(screen.getByText("Body text")).toBeTruthy();
    });

    // The markdown wrapper must use the theme-scoped `dark:prose-invert`
    // variant; a bare `prose-invert` forces white text in day mode.
    const body = screen.getByText("Body text");
    const wrapper = body.closest("div");
    expect(wrapper).not.toBeNull();
    const classes = (wrapper as HTMLElement).className.split(" ");
    expect(classes).toContain("dark:prose-invert");
    expect(classes).not.toContain("prose-invert");
  });

  it("shows a loading state before the document arrives", () => {
    const { promise } = Promise.withResolvers<LegalDocumentPublic>();
    getPublishedDocumentMock.mockReturnValue(promise);

    render(
      <LegalDocumentPage
        documentKey="terms"
        heading="Terms & Conditions"
        unavailableMessage="The Terms & Conditions are not available right now."
      />,
    );

    expect(screen.getByText("Loading…")).toBeTruthy();
    expect(screen.queryByText("Body text")).toBeNull();
  });
});
