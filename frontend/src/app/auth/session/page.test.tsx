import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const {
  replaceMock,
  setSessionMock,
  getSessionMock,
  getUserMock,
  exchangeHandoffMock,
  markInviteWelcomePendingMock,
} = vi.hoisted(() => ({
  replaceMock: vi.fn(),
  setSessionMock: vi.fn(),
  getSessionMock: vi.fn(),
  getUserMock: vi.fn(),
  exchangeHandoffMock: vi.fn(),
  markInviteWelcomePendingMock: vi.fn(),
}));

const useSearchParamsMock = vi.fn(
  () => new URLSearchParams("handoff=test-handoff-token"),
);

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: replaceMock }),
  useSearchParams: () => useSearchParamsMock(),
}));

vi.mock("@/lib/supabase", () => ({
  supabase: {
    auth: {
      setSession: setSessionMock,
      getSession: getSessionMock,
      getUser: getUserMock,
    },
  },
}));

vi.mock("@/services/auth-service", () => ({
  authService: {
    processInvitation: vi.fn().mockResolvedValue({ success: true }),
  },
}));

vi.mock("@/services/oauth-session-service", () => ({
  exchangeOAuthSessionHandoff: exchangeHandoffMock,
}));

vi.mock("@/lib/invite-welcome", () => ({
  markInviteWelcomePending: markInviteWelcomePendingMock,
  consumeInviteWelcome: vi.fn(),
  peekInviteWelcome: vi.fn(),
  INVITE_WELCOME_STORAGE_KEY: "invite_welcome_v1",
}));

import OAuthSessionPage, {
  __resetOAuthSessionHandoffForTests,
} from "./page.client";

describe("OAuthSessionPage", () => {
  const locationReplaceMock = vi.fn();

  beforeEach(() => {
    __resetOAuthSessionHandoffForTests();
    replaceMock.mockReset();
    setSessionMock.mockReset();
    getSessionMock.mockReset();
    getUserMock.mockReset();
    exchangeHandoffMock.mockReset();
    markInviteWelcomePendingMock.mockReset();
    locationReplaceMock.mockReset();
    useSearchParamsMock.mockReturnValue(
      new URLSearchParams("handoff=test-handoff-token"),
    );
    window.history.replaceState = vi.fn();
    Object.defineProperty(window, "location", {
      configurable: true,
      value: {
        ...window.location,
        search: "?handoff=test-handoff-token",
        pathname: "/auth/session",
        replace: locationReplaceMock,
      },
    });
    getSessionMock.mockResolvedValue({ data: { session: null } });
    exchangeHandoffMock.mockResolvedValue({
      success: true,
      data: {
        access_token: "test-access",
        refresh_token: "test-refresh",
        expires_in: 3600,
        token_type: "bearer",
      },
    });
    setSessionMock.mockResolvedValue({ error: null });
    getUserMock.mockResolvedValue({ data: { user: { id: "user-1" } } });
  });

  it("exchanges the handoff token and redirects to dashboard", async () => {
    render(<OAuthSessionPage />);

    await waitFor(() => {
      expect(exchangeHandoffMock).toHaveBeenCalledWith("test-handoff-token");
    });
    expect(setSessionMock).toHaveBeenCalledWith({
      access_token: "test-access",
      refresh_token: "test-refresh",
    });
    expect(locationReplaceMock).toHaveBeenCalledWith("/dashboard");
  });

  it("marks invite welcome when an invitation token is present", async () => {
    useSearchParamsMock.mockReturnValue(
      new URLSearchParams(
        "handoff=test-handoff-token&invitation_token=invite-123",
      ),
    );
    Object.defineProperty(window, "location", {
      configurable: true,
      value: {
        ...window.location,
        search: "?handoff=test-handoff-token&invitation_token=invite-123",
        pathname: "/auth/session",
        replace: locationReplaceMock,
      },
    });

    const { authService } = await import("@/services/auth-service");
    vi.mocked(authService.processInvitation).mockResolvedValueOnce({
      success: true,
      data: {
        organization_id: "org-1",
        organization_name: "Acme Plumbing",
      },
    });

    render(<OAuthSessionPage />);

    await waitFor(() => {
      expect(authService.processInvitation).toHaveBeenCalledWith(
        "invite-123",
        "user-1",
      );
    });
    expect(markInviteWelcomePendingMock).toHaveBeenCalledWith({
      organizationId: "org-1",
      organizationName: "Acme Plumbing",
    });
    expect(locationReplaceMock).toHaveBeenCalledWith("/dashboard");
  });

  it("redirects immediately when a session already exists", async () => {
    getSessionMock.mockResolvedValue({
      data: { session: { access_token: "existing" } },
    });

    render(<OAuthSessionPage />);

    await waitFor(() => {
      expect(locationReplaceMock).toHaveBeenCalledWith("/dashboard");
    });
    expect(exchangeHandoffMock).not.toHaveBeenCalled();
  });

  it("redirects when handoff exchange fails but session was already stored", async () => {
    exchangeHandoffMock.mockResolvedValue({
      success: false,
      error: "Authentication could not be completed.",
    });
    getSessionMock
      .mockResolvedValueOnce({ data: { session: null } })
      .mockResolvedValueOnce({
        data: { session: { access_token: "existing" } },
      });

    render(<OAuthSessionPage />);

    await waitFor(() => {
      expect(locationReplaceMock).toHaveBeenCalledWith("/dashboard");
    });
  });

  it("shows an error when the handoff token is missing", async () => {
    useSearchParamsMock.mockReturnValue(new URLSearchParams());
    Object.defineProperty(window, "location", {
      configurable: true,
      value: {
        ...window.location,
        search: "",
        pathname: "/auth/session",
        replace: locationReplaceMock,
      },
    });

    render(<OAuthSessionPage />);

    expect(
      await screen.findByText("Authentication could not be completed."),
    ).toBeTruthy();
  });
});
