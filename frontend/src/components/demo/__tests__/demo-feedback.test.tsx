import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { trackMock, submitMock } = vi.hoisted(() => ({
  trackMock: vi.fn(),
  submitMock: vi.fn(),
}));

vi.mock("@/lib/analytics/posthog", () => ({
  trackEvent: (...args: unknown[]) => trackMock(...args),
}));

vi.mock("@/services/demo-public-service", () => ({
  demoPublicService: {
    submitDemoFeedback: (...args: unknown[]) => submitMock(...args),
  },
}));

import { DemoFeedback } from "@/components/demo/demo-feedback";

describe("DemoFeedback", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("emits one rating event with slug and no PII", async () => {
    const user = userEvent.setup();
    render(<DemoFeedback agentName="Alex" demoSlug="dental" />);

    await user.click(screen.getByRole("button", { name: "Rate 4 out of 5" }));

    expect(trackMock).toHaveBeenCalledTimes(1);
    expect(trackMock).toHaveBeenCalledWith("demo_feedback", {
      demo_slug: "dental",
      rating: 4,
    });
    expect(screen.getByTestId("demo-feedback-thanks")).not.toBeNull();
  });

  it("ignores repeat clicks after the first rating", async () => {
    const user = userEvent.setup();
    render(<DemoFeedback agentName="Alex" demoSlug="dental" />);

    await user.click(screen.getByRole("button", { name: "Rate 5 out of 5" }));
    expect(screen.queryByRole("button", { name: /rate/i })).toBeNull();
    expect(trackMock).toHaveBeenCalledTimes(1);
  });

  it("stores the rating in the platform when a receipt token is present", async () => {
    const user = userEvent.setup();
    submitMock.mockResolvedValue(undefined);
    render(
      <DemoFeedback
        agentName="Alex"
        demoSlug="dental"
        receiptToken="receipt-token"
      />,
    );

    await user.click(screen.getByRole("button", { name: "Rate 4 out of 5" }));

    expect(submitMock).toHaveBeenCalledWith("dental", "receipt-token", 4);
    expect(screen.getByTestId("demo-feedback-thanks")).not.toBeNull();
  });

  it("keeps analytics-only behavior without a receipt token", async () => {
    const user = userEvent.setup();
    render(<DemoFeedback agentName="Alex" demoSlug="dental" />);

    await user.click(screen.getByRole("button", { name: "Rate 4 out of 5" }));

    expect(trackMock).toHaveBeenCalledTimes(1);
    expect(submitMock).not.toHaveBeenCalled();
    expect(screen.getByTestId("demo-feedback-thanks")).not.toBeNull();
  });

  it("still thanks the visitor when the platform write fails", async () => {
    const user = userEvent.setup();
    submitMock.mockRejectedValue(new Error("Network down"));
    render(
      <DemoFeedback
        agentName="Alex"
        demoSlug="dental"
        receiptToken="receipt-token"
      />,
    );

    await user.click(screen.getByRole("button", { name: "Rate 5 out of 5" }));

    expect(screen.getByTestId("demo-feedback-thanks")).not.toBeNull();
  });
});
