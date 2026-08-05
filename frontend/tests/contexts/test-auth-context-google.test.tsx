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

function GoogleAuthInvoker({
  invitationToken,
  includeNonce = true,
}: {
  invitationToken?: string;
  includeNonce?: boolean;
}) {
  const { signInWithGoogleIdToken } = useAuth();
  const [status, setStatus] = useState("");

  return (
    <>
      <button
        type="button"
        onClick={async () => {
          try {
            const credentials = {
              token: "google-id-token",
              ...(includeNonce ? { nonce: "google-raw-nonce" } : {}),
              ...(invitationToken ? { invitationToken } : {}),
            };
            await signInWithGoogleIdToken(credentials);
            setStatus("success");
          } catch (error) {
            setStatus(error instanceof Error ? error.message : "failed");
          }
        }}
      >
        Continue with Google
      </button>
      <output>{status}</output>
    </>
  );
}

describe("AuthProvider Google ID-token sign-in", () => {
  const signInWithIdToken = vi.fn();
  const updateUser = vi.fn();

  beforeEach(() => {
    signInWithIdToken.mockReset();
    updateUser.mockReset();
    vi.mocked(authService.processInvitation).mockReset();
    signInWithIdToken.mockResolvedValue({
      data: {
        user: {
          id: "google-user",
          email: "jane@example.com",
          user_metadata: {
            first_name: "Jane",
            last_name: "Doe",
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

    (
      supabase.auth as unknown as {
        signInWithIdToken: typeof signInWithIdToken;
        updateUser: typeof updateUser;
      }
    ).signInWithIdToken = signInWithIdToken;
    (supabase.auth as unknown as { updateUser: typeof updateUser }).updateUser =
      updateUser;
  });

  it("passes the Google credential and raw nonce to Supabase", async () => {
    const user = userEvent.setup();

    render(
      <AuthProvider>
        <GoogleAuthInvoker />
      </AuthProvider>,
    );

    await user.click(
      await screen.findByRole("button", { name: "Continue with Google" }),
    );

    await waitFor(() => {
      expect(signInWithIdToken).toHaveBeenCalledWith({
        provider: "google",
        token: "google-id-token",
        nonce: "google-raw-nonce",
      });
    });
    expect(screen.getByText("success")).toBeInTheDocument();
  });

  it("supports exchanges without a nonce", async () => {
    const user = userEvent.setup();

    render(
      <AuthProvider>
        <GoogleAuthInvoker includeNonce={false} />
      </AuthProvider>,
    );

    await user.click(
      await screen.findByRole("button", { name: "Continue with Google" }),
    );

    await waitFor(() => {
      expect(signInWithIdToken).toHaveBeenCalledWith({
        provider: "google",
        token: "google-id-token",
      });
    });
  });

  it("processes an invitation after a Google sign-up", async () => {
    const user = userEvent.setup();

    render(
      <AuthProvider>
        <GoogleAuthInvoker invitationToken="invite-token" />
      </AuthProvider>,
    );

    await user.click(
      await screen.findByRole("button", { name: "Continue with Google" }),
    );

    await waitFor(() => {
      expect(authService.processInvitation).toHaveBeenCalledWith(
        "invite-token",
        "google-user",
      );
    });
  });

  it("does not block sign-in when invitation processing returns an error", async () => {
    const user = userEvent.setup();
    vi.mocked(authService.processInvitation).mockResolvedValueOnce({
      success: false,
      error: "Invitation expired",
    });

    render(
      <AuthProvider>
        <GoogleAuthInvoker invitationToken="invite-token" />
      </AuthProvider>,
    );

    await user.click(
      await screen.findByRole("button", { name: "Continue with Google" }),
    );

    expect(await screen.findByText("success")).toBeInTheDocument();
  });

  it("does not block sign-in when invitation processing throws", async () => {
    const user = userEvent.setup();
    vi.mocked(authService.processInvitation).mockRejectedValueOnce(
      new Error("Invitation service unavailable"),
    );

    render(
      <AuthProvider>
        <GoogleAuthInvoker invitationToken="invite-token" />
      </AuthProvider>,
    );

    await user.click(
      await screen.findByRole("button", { name: "Continue with Google" }),
    );

    expect(await screen.findByText("success")).toBeInTheDocument();
  });

  it("normalizes missing Google first and last names", async () => {
    const user = userEvent.setup();
    signInWithIdToken.mockResolvedValueOnce({
      data: {
        user: {
          id: "google-user",
          email: "jane@example.com",
          user_metadata: { name: "Jane Doe" },
        },
      },
      error: null,
    });

    render(
      <AuthProvider>
        <GoogleAuthInvoker />
      </AuthProvider>,
    );

    await user.click(
      await screen.findByRole("button", { name: "Continue with Google" }),
    );

    await waitFor(() => {
      expect(updateUser).toHaveBeenCalledWith({
        data: {
          name: "Jane Doe",
          first_name: "Jane",
          last_name: "Doe",
        },
      });
    });
  });

  it("keeps authentication successful when metadata synchronization fails", async () => {
    const user = userEvent.setup();
    updateUser.mockResolvedValueOnce({
      error: new Error("Profile update failed"),
    });
    signInWithIdToken.mockResolvedValueOnce({
      data: {
        user: {
          id: "google-user",
          email: "jane@example.com",
          user_metadata: { name: "Jane Doe" },
        },
      },
      error: null,
    });

    render(
      <AuthProvider>
        <GoogleAuthInvoker />
      </AuthProvider>,
    );

    await user.click(
      await screen.findByRole("button", { name: "Continue with Google" }),
    );

    expect(await screen.findByText("success")).toBeInTheDocument();
  });

  it("keeps authentication successful when metadata synchronization throws", async () => {
    const user = userEvent.setup();
    updateUser.mockRejectedValueOnce(new Error("Profile service unavailable"));
    signInWithIdToken.mockResolvedValueOnce({
      data: {
        user: {
          id: "google-user",
          email: "jane@example.com",
          user_metadata: { name: "Jane Doe" },
        },
      },
      error: null,
    });

    render(
      <AuthProvider>
        <GoogleAuthInvoker />
      </AuthProvider>,
    );

    await user.click(
      await screen.findByRole("button", { name: "Continue with Google" }),
    );

    expect(await screen.findByText("success")).toBeInTheDocument();
  });

  it("rejects a successful exchange that does not return a user", async () => {
    const user = userEvent.setup();
    signInWithIdToken.mockResolvedValueOnce({
      data: { user: null },
      error: null,
    });

    render(
      <AuthProvider>
        <GoogleAuthInvoker />
      </AuthProvider>,
    );

    await user.click(
      await screen.findByRole("button", { name: "Continue with Google" }),
    );

    expect(
      await screen.findByText("Google sign-in did not return a user."),
    ).toBeInTheDocument();
  });

  it("surfaces Supabase ID-token errors to the caller", async () => {
    const user = userEvent.setup();
    signInWithIdToken.mockResolvedValueOnce({
      data: { user: null },
      error: new Error("Invalid Google ID token"),
    });

    render(
      <AuthProvider>
        <GoogleAuthInvoker />
      </AuthProvider>,
    );

    await user.click(
      await screen.findByRole("button", { name: "Continue with Google" }),
    );

    expect(
      await screen.findByText("Invalid Google ID token"),
    ).toBeInTheDocument();
  });
});
