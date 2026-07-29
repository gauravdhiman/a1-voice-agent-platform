/**
 * Tests for the /platform/presets page (platform admin only).
 *
 * Contract (mirrors /platform/tools):
 *   - A platform admin sees the "Voice Presets" heading + the inline
 *     `<PlatformPresetsManager>`.
 *   - Anyone else gets `<AccessDenied>` (frontend gate; the backend
 *     independently enforces platform_admin on every write endpoint and on
 *     draft reads).
 */
import React from "react";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockUseAuth = vi.fn();

vi.mock("@/contexts/auth-context", () => ({
  useAuth: () => mockUseAuth(),
}));

// Stub the manager so the test asserts it is rendered (not its internals).
vi.mock("@/components/presets/platform-presets-manager", () => ({
  PlatformPresetsManager: () => <div data-testid="platform-presets-manager" />,
}));

vi.mock("@/components/ui/access-denied", () => ({
  AccessDenied: ({ description }: { description: string }) => (
    <div data-testid="access-denied" data-description={description} />
  ),
}));

import PlatformPresetsPage from "../page";

describe("/platform/presets page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the heading + PlatformPresetsManager for a platform admin", () => {
    mockUseAuth.mockReturnValue({
      user: { hasRole: (role: string) => role === "platform_admin" },
    });

    render(<PlatformPresetsPage />);

    expect(
      screen.getByRole("heading", { name: /Voice Presets/i }),
    ).toBeInTheDocument();
    expect(screen.getByTestId("platform-presets-manager")).toBeInTheDocument();
    expect(screen.queryByTestId("access-denied")).not.toBeInTheDocument();
  });

  it("denies an org admin (no platform_admin role)", () => {
    mockUseAuth.mockReturnValue({
      user: { hasRole: (role: string) => role === "org_admin" },
    });

    render(<PlatformPresetsPage />);

    expect(screen.getByTestId("access-denied")).toBeInTheDocument();
    expect(
      screen.queryByTestId("platform-presets-manager"),
    ).not.toBeInTheDocument();
  });

  it("denies a regular member", () => {
    mockUseAuth.mockReturnValue({
      user: { hasRole: (_role: string) => false },
    });

    render(<PlatformPresetsPage />);

    expect(screen.getByTestId("access-denied")).toBeInTheDocument();
  });

  it("denies when there is no user (signed out / loading)", () => {
    mockUseAuth.mockReturnValue({ user: null });

    render(<PlatformPresetsPage />);

    expect(screen.getByTestId("access-denied")).toBeInTheDocument();
    expect(
      screen.queryByTestId("platform-presets-manager"),
    ).not.toBeInTheDocument();
  });
});