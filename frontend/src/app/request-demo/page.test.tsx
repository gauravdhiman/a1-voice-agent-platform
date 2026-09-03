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

import RequestDemoPage from "./page";

describe("RequestDemoPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("submits the form and shows the fixed success copy", async () => {
    const user = userEvent.setup();
    submitMock.mockResolvedValue({ success: true });

    render(<RequestDemoPage />);

    await user.type(screen.getByLabelText(/your name/i), "Sam Owner");
    await user.type(screen.getByLabelText(/business name/i), "Bright Smiles");
    await user.type(screen.getByLabelText(/work email/i), "sam@example.com");
    await user.click(
      screen.getByRole("button", { name: /request my demo/i }),
    );

    await waitFor(() => {
      expect(submitMock).toHaveBeenCalledWith(
        expect.objectContaining({
          name: "Sam Owner",
          email: "sam@example.com",
          source: "request-demo",
        }),
      );
    });
    expect(
      await screen.findByTestId("request-demo-success"),
    ).not.toBeNull();
  });

  it("blocks invalid email without calling the service", async () => {
    const user = userEvent.setup();
    render(<RequestDemoPage />);

    await user.type(screen.getByLabelText(/your name/i), "Sam Owner");
    await user.type(screen.getByLabelText(/work email/i), "not-an-email");
    await user.click(
      screen.getByRole("button", { name: /request my demo/i }),
    );

    await screen.findByText(/valid email address/i);
    expect(submitMock).not.toHaveBeenCalled();
  });

  it("shows the service error without revealing email state", async () => {
    const user = userEvent.setup();
    submitMock.mockResolvedValue({
      success: false,
      error: "Could not send your request.",
    });
    render(<RequestDemoPage />);

    await user.type(screen.getByLabelText(/your name/i), "Sam Owner");
    await user.type(screen.getByLabelText(/work email/i), "sam@example.com");
    await user.click(
      screen.getByRole("button", { name: /request my demo/i }),
    );

    await screen.findByText("Could not send your request.");
    expect(
      screen.queryByTestId("request-demo-success"),
    ).toBeNull();
  });
});
