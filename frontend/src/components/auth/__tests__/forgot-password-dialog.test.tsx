import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { postMock } = vi.hoisted(() => ({
  postMock: vi.fn(),
}));

vi.mock("@/lib/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/client")>();
  return { ...actual, apiClient: { post: postMock } };
});

import { ForgotPasswordDialog } from "@/components/auth/forgot-password-dialog";

describe("ForgotPasswordDialog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  function renderOpen() {
    render(<ForgotPasswordDialog open onOpenChange={vi.fn()} />);
  }

  it("requests a reset through the backend and confirms", async () => {
    const user = userEvent.setup();
    postMock.mockResolvedValue({ data: { message: "If an account exists" } });
    renderOpen();

    await user.type(
      screen.getByLabelText(/email address/i),
      "sam@example.com",
    );
    await user.click(
      screen.getByRole("button", { name: /send reset email/i }),
    );

    expect(postMock).toHaveBeenCalledWith("/api/v1/auth/password-reset", {
      email: "sam@example.com",
    });
    expect(await screen.findByText("Email Sent!")).not.toBeNull();
  });

  it("shows the backend failure without leaking account state", async () => {
    const user = userEvent.setup();
    postMock.mockRejectedValue(new Error("Network down"));
    renderOpen();

    await user.type(
      screen.getByLabelText(/email address/i),
      "sam@example.com",
    );
    await user.click(
      screen.getByRole("button", { name: /send reset email/i }),
    );

    expect(await screen.findByText("Network down")).not.toBeNull();
    expect(screen.queryByText("Email Sent!")).toBeNull();
  });
});
