import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { listMock, updateMock, feedbackMock } = vi.hoisted(() => ({
  listMock: vi.fn(),
  updateMock: vi.fn(),
  feedbackMock: vi.fn(),
}));

vi.mock("@/contexts/auth-context", () => ({
  useAuth: () => ({
    user: { hasRole: (role: string) => role === "platform_admin" },
  }),
}));

vi.mock("@/services/lead-service", () => ({
  leadService: {
    listInterestLeads: (...args: unknown[]) => listMock(...args),
    updateInterestLeadStatus: (...args: unknown[]) => updateMock(...args),
    listDemoFeedback: (...args: unknown[]) => feedbackMock(...args),
  },
}));

import PlatformInterestPage from "../page";

function row(overrides = {}) {
  return {
    id: "lead-1",
    name: "Sam Owner",
    business_name: "Bright Smiles",
    email: "sam@example.com",
    phone: null,
    vertical: "dental",
    message: "Miss after-hours calls.",
    source: "outcome-form",
    demo_slug: "copper-ridge-service-request",
    status: "new",
    created_at: "2026-09-04T00:00:00+00:00",
    contacted_at: null,
    ...overrides,
  };
}

describe("PlatformInterestPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listMock.mockResolvedValue({ success: true, data: [row()] });
    feedbackMock.mockResolvedValue({
      success: true,
      data: { summary: [], recent: [] },
    });
  });

  it("lists interest with source attribution and message preview", async () => {
    render(<PlatformInterestPage />);

    expect(await screen.findByText("Sam Owner")).not.toBeNull();
    expect(screen.getByText("sam@example.com")).not.toBeNull();
    expect(screen.getByText("outcome-form")).not.toBeNull();
    expect(screen.getByText("Miss after-hours calls.")).not.toBeNull();
  });

  it("advances a lead to the next follow-up status", async () => {
    const user = userEvent.setup();
    updateMock.mockResolvedValue({
      success: true,
      data: row({ status: "contacted" }),
    });
    render(<PlatformInterestPage />);

    await screen.findByText("Sam Owner");
    await user.click(screen.getByRole("button", { name: "Mark contacted" }));

    expect(updateMock).toHaveBeenCalledWith("lead-1", "contacted");
    expect(await screen.findByText("contacted")).not.toBeNull();
  });

  it("explains the empty funnel", async () => {
    listMock.mockResolvedValue({ success: true, data: [] });
    render(<PlatformInterestPage />);

    expect(await screen.findByText(/no interest yet/i)).not.toBeNull();
  });

  it("summarizes stored demo ratings per demo", async () => {
    feedbackMock.mockResolvedValue({
      success: true,
      data: {
        summary: [
          {
            demo_slug: "copper-ridge-service-request",
            count: 4,
            average_rating: 4.5,
          },
        ],
        recent: [],
      },
    });
    render(<PlatformInterestPage />);

    expect(await screen.findByText("Demo ratings")).not.toBeNull();
    expect(
      screen.getByTestId("demo-rating-copper-ridge-service-request"),
    ).not.toBeNull();
    expect(screen.getByText("4.5")).not.toBeNull();
    expect(screen.getByText("4 ratings")).not.toBeNull();
  });

  it("hides the ratings card when no ratings exist yet", async () => {
    render(<PlatformInterestPage />);

    await screen.findByText("Sam Owner");
    expect(screen.queryByText("Demo ratings")).toBeNull();
  });
});
