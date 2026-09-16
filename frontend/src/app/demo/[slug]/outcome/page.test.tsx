import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { getDemoOutcomeMock, useParamsMock, useSearchParamsMock } = vi.hoisted(
  () => ({
    getDemoOutcomeMock: vi.fn(),
    useParamsMock: vi.fn(() => ({ slug: "copper-ridge-service-request" })),
    useSearchParamsMock: vi.fn(
      () => new URLSearchParams("token=receipt-token"),
    ),
  }),
);

vi.mock("next/navigation", () => ({
  useParams: useParamsMock,
  useSearchParams: useSearchParamsMock,
}));

vi.mock("@/services/demo-public-service", () => ({
  demoPublicService: {
    getDemoOutcome: getDemoOutcomeMock,
  },
}));

import DemoOutcomePage from "./page";

describe("DemoOutcomePage", () => {
  beforeEach(() => {
    getDemoOutcomeMock.mockReset();
    useParamsMock.mockReturnValue({ slug: "copper-ridge-service-request" });
    useSearchParamsMock.mockReturnValue(
      new URLSearchParams("token=receipt-token"),
    );
  });

  it("shows the captured fields and provider destination", async () => {
    getDemoOutcomeMock.mockResolvedValue({
      demo_slug: "copper-ridge-service-request",
      agent_name: "Jordan",
      organization_name: "Copper Ridge Heating & Air",
      status: "completed",
      actions: [
        {
          id: "receipt-1",
          action_type: "lead_capture",
          provider: "google_sheets",
          status: "succeeded",
          error_code: null,
          captured_fields: {
            caller_name: "Maria Garcia",
            service_needed: "AC repair",
            issue_summary: "Warm air upstairs",
          },
          provider_result: {
            record_type: "lead_row",
            record_id: "submission-123",
            message: "Service inquiry captured in Google Sheets.",
          },
          public_result_url:
            "https://docs.google.com/spreadsheets/d/demo-sheet/edit?gid=0#gid=0",
          created_at: "2026-08-30T10:00:00Z",
          expires_at: "2026-08-31T10:00:00Z",
        },
        {
          id: "receipt-email-1",
          action_type: "email_delivery",
          provider: "gmail",
          status: "succeeded",
          error_code: null,
          captured_fields: {},
          provider_result: {
            record_type: "email",
            record_id: "gmail-message-123",
            message: "Gmail confirmed the email was sent.",
          },
          public_result_url: null,
          created_at: "2026-08-30T10:00:01Z",
          expires_at: "2026-08-31T10:00:01Z",
        },
      ],
      expires_at: "2026-08-31T10:00:00Z",
    });

    render(<DemoOutcomePage />);

    expect(
      await screen.findByRole("heading", {
        name: /that call just did real work/i,
      }),
    ).toBeTruthy();
    expect(screen.getByText("What Jordan")).toBeTruthy();
    expect(screen.getByText("saved for you")).toBeTruthy();
    expect(screen.getByText("Maria Garcia")).toBeTruthy();
    expect(screen.getByText("AC repair")).toBeTruthy();
    expect(screen.getByText("via Google Sheets")).toBeTruthy();
    expect(screen.getByText("Email confirmation sent")).toBeTruthy();
    expect(
      screen.getByText("Gmail confirmed the email was sent."),
    ).toBeTruthy();
    expect(screen.getByText("via Gmail")).toBeTruthy();
    const detailsLink = screen.getByRole("link", {
      name: "See what was saved",
    });
    expect(detailsLink.getAttribute("href")).toBe("#call-results");
    const turn = screen.getByText("YOUR TURN · 30 SECONDS");
    const results = screen.getByText("saved for you");
    expect(
      turn.compareDocumentPosition(results) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    const resultLink = screen.getByRole("link", {
      name: "Open Google Sheets result",
    });
    expect(resultLink.getAttribute("href")).toBe(
      "https://docs.google.com/spreadsheets/d/demo-sheet/edit?gid=0#gid=0",
    );
    await waitFor(() => {
      expect(getDemoOutcomeMock).toHaveBeenCalledWith(
        "copper-ridge-service-request",
        "receipt-token",
      );
    });
  });

  it("explains when a call ended before a provider mutation", async () => {
    getDemoOutcomeMock.mockResolvedValue({
      demo_slug: "copper-ridge-service-request",
      agent_name: "Jordan",
      organization_name: "Copper Ridge Heating & Air",
      status: "no_action",
      actions: [],
      expires_at: "2026-08-31T10:00:00Z",
    });

    render(<DemoOutcomePage />);

    expect(
      await screen.findByText("Nothing got saved on this call"),
    ).toBeTruthy();
    expect(
      screen.getByText(/This page only shows results that tools confirmed\./),
    ).toBeTruthy();
  });

  it("uses the configured result URL for a Calendar booking", async () => {
    getDemoOutcomeMock.mockResolvedValue({
      demo_slug: "pleasant-pediatric-appointments",
      agent_name: "Alex",
      organization_name: "Pleasant Pediatric",
      status: "completed",
      actions: [
        {
          id: "receipt-calendar-1",
          action_type: "appointment_booking",
          provider: "google_calendar",
          status: "succeeded",
          error_code: null,
          captured_fields: {
            caller_name: "Maria Garcia",
            purpose: "New patient visit",
            start_time: "2026-09-01T14:00:00-07:00",
          },
          provider_result: {
            record_type: "calendar_event",
            record_id: "event-1",
            record_url:
              "https://calendar.google.com/calendar/event?eid=event-1",
            message: "Appointment booked.",
          },
          public_result_url:
            "https://calendar.google.com/calendar/r/eventedit/event-1",
          created_at: "2026-08-30T10:00:00Z",
          expires_at: "2026-08-31T10:00:00Z",
        },
      ],
      expires_at: "2026-08-31T10:00:00Z",
    });

    render(<DemoOutcomePage />);

    const link = await screen.findByRole("link", {
      name: "Open Google Calendar result",
    });
    expect(link.getAttribute("href")).toBe(
      "https://calendar.google.com/calendar/r/eventedit/event-1",
    );
    expect(link.getAttribute("target")).toBe("_blank");
  });

  it("does not show an external CTA when no result URL is configured", async () => {
    getDemoOutcomeMock.mockResolvedValue({
      demo_slug: "pleasant-pediatric-appointments",
      agent_name: "Alex",
      organization_name: "Pleasant Pediatric",
      status: "completed",
      actions: [
        {
          id: "receipt-calendar-2",
          action_type: "appointment_booking",
          provider: "google_calendar",
          status: "succeeded",
          error_code: null,
          captured_fields: {
            caller_name: "Maria Garcia",
            purpose: "New patient visit",
          },
          provider_result: {
            record_type: "calendar_event",
            record_id: "event-2",
            record_url:
              "https://calendar.google.com/calendar/event?eid=event-2",
            message: "Appointment booked.",
          },
          public_result_url: null,
          created_at: "2026-08-30T10:00:00Z",
          expires_at: "2026-08-31T10:00:00Z",
        },
      ],
      expires_at: "2026-08-31T10:00:00Z",
    });

    render(<DemoOutcomePage />);

    expect(
      await screen.findByRole("heading", {
        name: /that call just did real work/i,
      }),
    ).toBeTruthy();
    expect(screen.getByText("What Alex")).toBeTruthy();
    expect(screen.getByText("saved for you")).toBeTruthy();
    expect(
      screen.queryByRole("link", { name: "Open Google Calendar result" }),
    ).toBeNull();
  });

  it("distinguishes captured details from an unsuccessful provider save", async () => {
    getDemoOutcomeMock.mockResolvedValue({
      demo_slug: "copper-ridge-service-request",
      agent_name: "Jordan",
      organization_name: "Copper Ridge Heating & Air",
      status: "needs_attention",
      actions: [
        {
          id: "receipt-2",
          action_type: "lead_capture",
          provider: "google_sheets",
          status: "failed",
          error_code: "invalid_configuration",
          captured_fields: {
            caller_name: "Maria Garcia",
            caller_email: "maria@example.com",
            service_needed: "AC repair",
          },
          provider_result: {
            message:
              "The Google Sheets destination is not configured for this demo.",
          },
          public_result_url:
            "https://docs.google.com/spreadsheets/d/demo-sheet/edit?gid=0#gid=0",
          created_at: "2026-08-30T10:00:00Z",
          expires_at: "2026-08-31T10:00:00Z",
        },
      ],
      expires_at: "2026-08-31T10:00:00Z",
    });

    render(<DemoOutcomePage />);

    expect(
      await screen.findByRole("heading", { name: /almost done/i }),
    ).toBeTruthy();
    expect(screen.getByText("Service request not saved")).toBeTruthy();
    expect(screen.getByText("Didn't go through")).toBeTruthy();
    expect(
      screen.getByText(
        "The Google Sheets destination is not configured for this demo.",
      ),
    ).toBeTruthy();
    expect(screen.queryByText("Email confirmation")).toBeNull();
    expect(
      screen.queryByRole("link", { name: "Open Google Sheets result" }),
    ).toBeNull();
  });
});
