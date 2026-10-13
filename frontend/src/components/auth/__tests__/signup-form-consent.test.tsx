import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent, { type UserEvent } from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const useSearchParamsMock = vi.fn(() => new URLSearchParams());

vi.mock("next/navigation", () => ({
  useSearchParams: () => useSearchParamsMock(),
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
}));

vi.mock("@/contexts/auth-context", () => ({
  useAuth: vi.fn(),
}));

vi.mock("@/components/auth/turnstile-widget", () => ({
  TurnstileWidget: ({ onVerify }: { onVerify: (token: string) => void }) => (
    <button
      type="button"
      data-testid="turnstile-widget"
      onClick={() => onVerify("test-captcha-token")}
    >
      verify
    </button>
  ),
}));

vi.mock("@/services/auth-service", () => ({
  authService: {
    checkEmailAvailability: vi.fn(async () => ({ exists: false })),
  },
}));

import { useAuth } from "@/contexts/auth-context";
import { SignUpForm } from "../signup-form";

describe("SignUpForm legal consent gating", () => {
  const signUp = vi.fn();

  beforeEach(() => {
    signUp.mockReset();
    signUp.mockResolvedValue({
      user: { id: "user-1" },
      emailVerificationRequired: false,
      error: null,
      joinedOrganizationId: null,
      joinedOrganizationName: null,
    });
    useSearchParamsMock.mockReturnValue(new URLSearchParams());
    vi.mocked(useAuth).mockReturnValue({ signUp } as never);
  });

  const fillValidFields = async (user: UserEvent) => {
    await user.type(screen.getByLabelText(/first name/i), "Jane");
    await user.type(screen.getByLabelText(/last name/i), "Doe");
    await user.type(screen.getByLabelText(/email/i), "jane@example.com");
    await user.type(screen.getByLabelText(/^password$/i), "Password123!");
    await user.type(screen.getByLabelText(/confirm password/i), "Password123!");
  };

  it("keeps the create-account submit disabled until the terms checkbox is checked", async () => {
    const user = userEvent.setup();
    render(<SignUpForm />);

    const submitButton = screen.getByRole("button", {
      name: /create account/i,
    }) as HTMLButtonElement;
    const checkbox = screen.getByRole("checkbox") as HTMLInputElement;

    expect(submitButton.disabled).toBe(true);
    expect(checkbox.checked).toBe(false);

    await fillValidFields(user);

    // Fields are valid but consent is still missing: submit stays disabled.
    expect(submitButton.disabled).toBe(true);

    await user.click(checkbox);
    await waitFor(() => {
      expect(
        (
          screen.getByRole("button", {
            name: /create account/i,
          }) as HTMLButtonElement
        ).disabled,
      ).toBe(false);
    });
  });

  it("links to the Terms & Conditions and Privacy Policy in a new tab", () => {
    render(<SignUpForm />);

    const termsLink = screen.getByRole("link", {
      name: /terms & conditions/i,
    });
    const privacyLink = screen.getByRole("link", { name: /privacy policy/i });

    expect(termsLink.getAttribute("target")).toBe("_blank");
    expect(termsLink.getAttribute("rel")).toBe("noopener noreferrer");
    expect(termsLink.getAttribute("href")).toBe("/terms");
    expect(privacyLink.getAttribute("target")).toBe("_blank");
    expect(privacyLink.getAttribute("rel")).toBe("noopener noreferrer");
    expect(privacyLink.getAttribute("href")).toBe("/privacy");
  });

  it("disables OAuth signup buttons until the terms checkbox is checked", async () => {
    const user = userEvent.setup();
    render(<SignUpForm />);

    const googleButton = screen.getByTestId("google-oauth-redirect-button");
    const linkedinButton = screen.getByTestId("linkedin-oauth-redirect-button");

    expect(googleButton.getAttribute("aria-disabled")).toBe("true");
    expect(linkedinButton.getAttribute("aria-disabled")).toBe("true");

    await user.click(screen.getByRole("checkbox"));

    expect(googleButton.getAttribute("aria-disabled")).toBe("false");
    expect(linkedinButton.getAttribute("aria-disabled")).toBe("false");
  });

  it("passes terms_accepted through to the signUp call on submit", async () => {
    const user = userEvent.setup();
    render(<SignUpForm />);

    await fillValidFields(user);
    await user.click(screen.getByRole("checkbox"));
    await user.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(signUp).toHaveBeenCalledTimes(1);
    });
    expect(signUp).toHaveBeenCalledWith(
      expect.objectContaining({ terms_accepted: true }),
    );
  });

  it("does not submit when the consent checkbox is unchecked", async () => {
    const user = userEvent.setup();
    render(<SignUpForm />);

    await fillValidFields(user);
    const submitButton = screen.getByRole("button", {
      name: /create account/i,
    }) as HTMLButtonElement;
    expect(submitButton.disabled).toBe(true);

    fireEvent.submit(submitButton.closest("form") as HTMLFormElement);
    expect(signUp).not.toHaveBeenCalled();
  });
});
