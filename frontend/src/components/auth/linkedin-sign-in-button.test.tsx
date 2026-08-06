import React from "react";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/services/linkedin-auth-service", () => ({
  linkedinAuthService: {
    getAuthorizationUrl: vi.fn(),
  },
}));

import { linkedinAuthService } from "@/services/linkedin-auth-service";
import { LinkedInSignInButton } from "./linkedin-sign-in-button";

const session = {
  accessToken: "access-token",
  refreshToken: "refresh-token",
  expiresIn: 3600,
};

function dispatchLinkedInMessage(
  popup: Window,
  data: Record<string, unknown>,
): void {
  const event = new MessageEvent("message", {
    origin: window.location.origin,
    data,
  });
  Object.defineProperty(event, "source", { value: popup });
  window.dispatchEvent(event);
}

describe("LinkedInSignInButton", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("opens LinkedIn directly and returns a session from the callback", async () => {
    const user = userEvent.setup();
    const popup = {
      closed: false,
      close: vi.fn(),
      location: { href: "" },
    } as unknown as Window;
    vi.spyOn(window, "open").mockReturnValue(popup);
    vi.mocked(linkedinAuthService.getAuthorizationUrl).mockResolvedValue({
      success: true,
      data: {
        authorizationUrl:
          "https://www.linkedin.com/oauth/v2/authorization?state=signed",
        state: "signed-state",
      },
    });
    const onSession = vi.fn();
    const onError = vi.fn();

    render(
      <LinkedInSignInButton
        text="signin_with"
        onSession={onSession}
        onError={onError}
      />,
    );

    await user.click(
      screen.getByRole("button", { name: "Sign in with LinkedIn" }),
    );
    await waitFor(() => {
      expect(popup.location.href).toBe(
        "https://www.linkedin.com/oauth/v2/authorization?state=signed",
      );
    });

    act(() => {
      dispatchLinkedInMessage(popup, {
        type: "linkedin-oauth-success",
        state: "signed-state",
        session,
      });
    });

    await waitFor(() => {
      expect(onSession).toHaveBeenCalledWith(session);
    });
    expect(onError).not.toHaveBeenCalled();
    expect(popup.close).toHaveBeenCalled();
  });

  it("keeps the popup flow alive when the parent rerenders on loading", async () => {
    const user = userEvent.setup();
    const popup = {
      closed: false,
      close: vi.fn(),
      location: { href: "" },
    } as unknown as Window;
    vi.spyOn(window, "open").mockReturnValue(popup);
    vi.mocked(linkedinAuthService.getAuthorizationUrl).mockResolvedValue({
      success: true,
      data: {
        authorizationUrl:
          "https://www.linkedin.com/oauth/v2/authorization?state=signed",
        state: "signed-state",
      },
    });
    const onSession = vi.fn();
    const onError = vi.fn();

    function Harness() {
      const [, setRenderCount] = React.useState(0);
      return (
        <LinkedInSignInButton
          text="signin_with"
          onSession={(value) => onSession(value)}
          onError={(value) => onError(value)}
          onLoadingChange={(loading) => {
            if (loading) {
              setRenderCount((count) => count + 1);
            }
          }}
        />
      );
    }

    render(<Harness />);
    await user.click(
      screen.getByRole("button", { name: "Sign in with LinkedIn" }),
    );
    await waitFor(() => expect(popup.location.href).toContain("linkedin"));

    act(() => {
      dispatchLinkedInMessage(popup, {
        type: "linkedin-oauth-success",
        state: "signed-state",
        session,
      });
    });

    await waitFor(() => expect(onSession).toHaveBeenCalledWith(session));
    expect(onError).not.toHaveBeenCalled();
  });

  it("reports when the browser blocks the popup", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "open").mockReturnValue(null);
    const onSession = vi.fn();
    const onError = vi.fn();

    render(
      <LinkedInSignInButton
        text="signup_with"
        onSession={onSession}
        onError={onError}
      />,
    );

    await user.click(
      screen.getByRole("button", { name: "Sign up with LinkedIn" }),
    );

    expect(onSession).not.toHaveBeenCalled();
    expect(onError).toHaveBeenCalledWith(
      "Please allow popups to sign in with LinkedIn.",
    );
  });

  it("reports a backend error and closes the reserved popup", async () => {
    const user = userEvent.setup();
    const popup = {
      closed: false,
      close: vi.fn(),
      location: { href: "" },
    } as unknown as Window;
    vi.spyOn(window, "open").mockReturnValue(popup);
    vi.mocked(linkedinAuthService.getAuthorizationUrl).mockResolvedValue({
      success: false,
      error: "LinkedIn sign-in is not configured.",
    });
    const onSession = vi.fn();
    const onError = vi.fn();

    render(
      <LinkedInSignInButton
        text="signin_with"
        onSession={onSession}
        onError={onError}
      />,
    );

    await user.click(
      screen.getByRole("button", { name: "Sign in with LinkedIn" }),
    );

    await waitFor(() =>
      expect(onError).toHaveBeenCalledWith(
        "LinkedIn sign-in is not configured.",
      ),
    );
    expect(popup.close).toHaveBeenCalled();
  });

  it("returns callback errors only after validating the popup state", async () => {
    const user = userEvent.setup();
    const popup = {
      closed: false,
      close: vi.fn(),
      location: { href: "" },
    } as unknown as Window;
    vi.spyOn(window, "open").mockReturnValue(popup);
    vi.mocked(linkedinAuthService.getAuthorizationUrl).mockResolvedValue({
      success: true,
      data: {
        authorizationUrl: "https://www.linkedin.com/oauth/v2/authorization",
        state: "expected-state",
      },
    });
    const onSession = vi.fn();
    const onError = vi.fn();

    render(
      <LinkedInSignInButton
        text="signin_with"
        onSession={onSession}
        onError={onError}
      />,
    );
    await user.click(
      screen.getByRole("button", { name: "Sign in with LinkedIn" }),
    );
    await waitFor(() => expect(popup.location.href).toContain("linkedin"));

    act(() => {
      dispatchLinkedInMessage(popup, {
        type: "linkedin-oauth-error",
        state: "expected-state",
        message: "LinkedIn denied access.",
      });
    });

    await waitFor(() =>
      expect(onError).toHaveBeenCalledWith("LinkedIn denied access."),
    );
    expect(onSession).not.toHaveBeenCalled();
    expect(popup.close).toHaveBeenCalled();
  });

  it("reports when the user closes the popup before callback completion", async () => {
    const user = userEvent.setup();
    const popup = {
      closed: true,
      close: vi.fn(),
      location: { href: "" },
    } as unknown as Window;
    vi.spyOn(window, "open").mockReturnValue(popup);
    vi.spyOn(window, "setInterval").mockImplementation((handler) => {
      if (typeof handler === "function") {
        handler();
      }
      return 1 as unknown as ReturnType<typeof window.setInterval>;
    });
    vi.mocked(linkedinAuthService.getAuthorizationUrl).mockResolvedValue({
      success: true,
      data: {
        authorizationUrl: "https://www.linkedin.com/oauth/v2/authorization",
        state: "expected-state",
      },
    });
    const onSession = vi.fn();
    const onError = vi.fn();

    render(
      <LinkedInSignInButton
        text="signin_with"
        onSession={onSession}
        onError={onError}
      />,
    );
    await user.click(
      screen.getByRole("button", { name: "Sign in with LinkedIn" }),
    );
    await waitFor(() => expect(popup.location.href).toContain("linkedin"));

    expect(onError).toHaveBeenCalledWith(
      "The LinkedIn sign-in window was closed.",
    );
  });

  it("ignores callback messages with an unexpected state", async () => {
    const user = userEvent.setup();
    const popup = {
      closed: false,
      close: vi.fn(),
      location: { href: "" },
    } as unknown as Window;
    vi.spyOn(window, "open").mockReturnValue(popup);
    vi.mocked(linkedinAuthService.getAuthorizationUrl).mockResolvedValue({
      success: true,
      data: {
        authorizationUrl: "https://www.linkedin.com/oauth/v2/authorization",
        state: "expected-state",
      },
    });
    const onSession = vi.fn();
    const onError = vi.fn();

    render(
      <LinkedInSignInButton
        text="signin_with"
        onSession={onSession}
        onError={onError}
      />,
    );

    await user.click(
      screen.getByRole("button", { name: "Sign in with LinkedIn" }),
    );
    await waitFor(() => expect(popup.location.href).toContain("linkedin"));

    act(() => {
      dispatchLinkedInMessage(popup, {
        type: "linkedin-oauth-success",
        state: "unexpected-state",
        session,
      });
    });

    expect(onSession).not.toHaveBeenCalled();
    expect(onError).not.toHaveBeenCalled();
  });
});
