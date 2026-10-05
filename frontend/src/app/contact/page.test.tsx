import { render, screen, waitFor } from "@testing-library/react";
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

vi.mock("@/components/auth/turnstile-widget", () => ({
  TurnstileWidget: () => null,
}));

import ContactPage from "./page";

describe("ContactPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("submits the full contact request through the lead intake workflow", async () => {
    const user = userEvent.setup();
    submitMock.mockResolvedValue({ success: true });
    render(<ContactPage />);

    await user.type(screen.getByLabelText(/your name/i), "Sam Owner");
    await user.type(screen.getByLabelText(/business name/i), "Bright Smiles");
    await user.type(screen.getByLabelText(/work email/i), "sam@example.com");
    await user.type(screen.getByLabelText(/phone number/i), "+14805550100");
    await user.selectOptions(
      screen.getByLabelText(/business type/i),
      "dental",
    );
    await user.type(
      screen.getByLabelText(/how can we help/i),
      "We need after-hours call coverage.",
    );
    await user.click(screen.getByRole("button", { name: /send message/i }));

    await waitFor(() => {
      expect(submitMock).toHaveBeenCalledWith({
        name: "Sam Owner",
        businessName: "Bright Smiles",
        email: "sam@example.com",
        phone: "+14805550100",
        vertical: "dental",
        message: "We need after-hours call coverage.",
        source: "contact-us",
        captchaToken: undefined,
      });
    });
    expect(await screen.findByTestId("contact-success")).toBeTruthy();
  });

  it("shows an actionable message when the lead submission fails", async () => {
    const user = userEvent.setup();
    submitMock.mockResolvedValue({
      success: false,
      error: "Could not send your message. Please try again.",
    });
    render(<ContactPage />);

    await user.type(screen.getByLabelText(/your name/i), "Sam Owner");
    await user.type(screen.getByLabelText(/work email/i), "sam@example.com");
    await user.click(screen.getByRole("button", { name: /send message/i }));

    expect(
      await screen.findByText("Could not send your message. Please try again."),
    ).toBeTruthy();
    expect(screen.queryByTestId("contact-success")).toBeNull();
  });
});
