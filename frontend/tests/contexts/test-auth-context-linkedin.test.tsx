import React, { useState } from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/hooks/use-user-profile", () => ({
  useUserProfile: vi.fn(() => ({
    data: [],
    isLoading: false,
    refetch: vi.fn().mockResolvedValue({}),
  })),
}));

vi.mock("@/services/auth-service", () => ({
  authService: {
    processInvitation: vi.fn(),
  },
}));

import { supabase } from "@/lib/supabase";
import { AuthProvider, useAuth } from "@/contexts/auth-context";
import { authService } from "@/services/auth-service";

function LinkedInAuthInvoker({
  invitationToken,
}: {
  invitationToken?: string;
}) {
  const { signInWithLinkedInSession } = useAuth();
  const [status, setStatus] = useState("");

  return (
    <>
      <button
        type="button"
        onClick={async () => {
          try {
            await signInWithLinkedInSession({
              accessToken: "access-token",
              refreshToken: "refresh-token",
              expiresIn: 3600,
              invitationToken,
            });
            setStatus("success");
          } catch (error) {
            setStatus(error instanceof Error ? error.message : "failed");
          }
        }}
      >
        Continue with LinkedIn
      </button>
      <output>{status}</output>
    </>
  );
}

describe("AuthProvider direct LinkedIn sign-in", () => {
  const setSession = vi.fn();
  const updateUser = vi.fn();

  beforeEach(() => {
    setSession.mockReset();
    updateUser.mockReset();
    vi.mocked(authService.processInvitation).mockReset();
    setSession.mockResolvedValue({
      data: {
        user: {
          id: "linkedin-user",
          email: "person@example.com",
          user_metadata: {
            given_name: "Person",
            family_name: "Example",
          },
        },
      },
      error: null,
    });
    updateUser.mockResolvedValue({ error: null });
    vi.mocked(authService.processInvitation).mockResolvedValue({
      success: true,
      data: {},
    });

    (supabase.auth as unknown as { setSession: typeof setSession }).setSession =
      setSession;
    (supabase.auth as unknown as { updateUser: typeof updateUser }).updateUser =
      updateUser;
  });

  it("applies the LinkedIn session with Supabase and processes invitations", async () => {
    const user = userEvent.setup();

    render(
      <AuthProvider>
        <LinkedInAuthInvoker invitationToken="invite-token" />
      </AuthProvider>,
    );

    await user.click(
      await screen.findByRole("button", { name: "Continue with LinkedIn" }),
    );

    await waitFor(() => {
      expect(setSession).toHaveBeenCalledWith({
        access_token: "access-token",
        refresh_token: "refresh-token",
      });
      expect(authService.processInvitation).toHaveBeenCalledWith(
        "invite-token",
        "linkedin-user",
      );
    });
    expect(screen.getByText("success")).toBeInTheDocument();
  });

  it("surfaces a Supabase session error", async () => {
    const user = userEvent.setup();
    setSession.mockResolvedValueOnce({
      data: { user: null },
      error: new Error("Invalid session"),
    });

    render(
      <AuthProvider>
        <LinkedInAuthInvoker />
      </AuthProvider>,
    );

    await user.click(
      await screen.findByRole("button", { name: "Continue with LinkedIn" }),
    );

    expect(await screen.findByText("Invalid session")).toBeInTheDocument();
  });
});
