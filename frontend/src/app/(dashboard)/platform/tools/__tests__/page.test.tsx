/**
 * Tests for the /platform/tools page (platform admin only).
 *
 * Contract (mirrors /platform/skills):
 *   - A platform admin sees the "Platform Tools" heading + the inline
 *     `<PlatformToolsManager>`.
 *   - Anyone else gets `<AccessDenied>` (frontend gate; the backend
 *     independently enforces platform_admin on every write endpoint).
 */
import React from "react";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockUseAuth = vi.fn();

vi.mock("@/contexts/auth-context", () => ({
  useAuth: () => mockUseAuth(),
}));

// Stub the manager so the test asserts it is rendered (not its internals,
// which are covered by test-platform-tools-manager.test.tsx).
vi.mock("@/components/tools/platform-tools-manager", () => ({
  PlatformToolsManager: () => <div data-testid="platform-tools-manager" />,
}));

vi.mock("@/components/ui/access-denied", () => ({
  AccessDenied: ({ description }: { description: string }) => (
    <div data-testid="access-denied" data-description={description} />
  ),
}));

import PlatformToolsPage from "../page";

describe("/platform/tools page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the heading + PlatformToolsManager for a platform admin", () => {
    mockUseAuth.mockReturnValue({
      user: { hasRole: (role: string) => role === "platform_admin" },
    });

    render(<PlatformToolsPage />);

    expect(
      screen.getByRole("heading", { name: /Platform Tools/i }),
    ).toBeInTheDocument();
    expect(screen.getByTestId("platform-tools-manager")).toBeInTheDocument();
    expect(screen.queryByTestId("access-denied")).not.toBeInTheDocument();
  });

  it("denies an org admin (no platform_admin role)", () => {
    mockUseAuth.mockReturnValue({
      user: { hasRole: (role: string) => role === "org_admin" },
    });

    render(<PlatformToolsPage />);

    expect(screen.getByTestId("access-denied")).toBeInTheDocument();
    expect(screen.queryByTestId("platform-tools-manager")).not.toBeInTheDocument();
  });

  it("denies a regular member", () => {
    mockUseAuth.mockReturnValue({
      user: { hasRole: (_role: string) => false },
    });

    render(<PlatformToolsPage />);

    expect(screen.getByTestId("access-denied")).toBeInTheDocument();
  });

  it("denies when there is no user (signed out / loading)", () => {
    mockUseAuth.mockReturnValue({ user: null });

    render(<PlatformToolsPage />);

    expect(screen.getByTestId("access-denied")).toBeInTheDocument();
    expect(screen.queryByTestId("platform-tools-manager")).not.toBeInTheDocument();
  });
});