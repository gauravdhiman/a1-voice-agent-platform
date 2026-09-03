import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { trackMock } = vi.hoisted(() => ({
  trackMock: vi.fn(),
}));

vi.mock("@/lib/analytics/posthog", () => ({
  trackEvent: (...args: unknown[]) => trackMock(...args),
}));

import { DemoFeedback } from "@/components/demo/demo-feedback";

describe("DemoFeedback", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("emits one rating event with slug and no PII", async () => {
    const user = userEvent.setup();
    render(<DemoFeedback demoSlug="dental" />);

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
    render(<DemoFeedback demoSlug="dental" />);

    await user.click(screen.getByRole("button", { name: "Rate 5 out of 5" }));
    expect(screen.queryByRole("button", { name: /rate/i })).toBeNull();
    expect(trackMock).toHaveBeenCalledTimes(1);
  });
});
