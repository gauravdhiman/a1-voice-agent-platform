import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { submitMock } = vi.hoisted(() => ({
  submitMock: vi.fn(),
}));

vi.mock("@/services/lead-service", () => ({
  leadService: {
    submitInterestLead: submitMock,
  },
}));

import { OutcomeInterest } from "@/components/demo/outcome-interest";

describe("OutcomeInterest", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("submits interest with outcome-form source and demo attribution", async () => {
    const user = userEvent.setup();
    submitMock.mockResolvedValue({ success: true });
    render(<OutcomeInterest demoSlug="copper-ridge-service-request" />);

    expect(
      screen.getByRole("heading", {
        name: "Want this to answer your business calls?",
      }),
    ).toBeTruthy();
    await user.type(screen.getByLabelText(/your name/i), "Sam Owner");
    await user.type(screen.getByLabelText(/work email/i), "sam@example.com");
    await user.click(
      screen.getByRole("button", { name: /get this for my business/i }),
    );

    expect(submitMock).toHaveBeenCalledWith(
      expect.objectContaining({
        name: "Sam Owner",
        email: "sam@example.com",
        source: "outcome-form",
        demoSlug: "copper-ridge-service-request",
        vertical: "hvac",
      }),
    );
    expect(screen.getByTestId("outcome-interest-success")).not.toBeNull();
  });

  it("blocks invalid email without calling the service", async () => {
    const user = userEvent.setup();
    render(<OutcomeInterest demoSlug="dental" />);

    await user.type(screen.getByLabelText(/your name/i), "Sam Owner");
    await user.type(screen.getByLabelText(/work email/i), "not-an-email");
    await user.click(
      screen.getByRole("button", { name: /get this for my business/i }),
    );

    expect(await screen.findByText(/valid email address/i)).not.toBeNull();
    expect(submitMock).not.toHaveBeenCalled();
  });
});
