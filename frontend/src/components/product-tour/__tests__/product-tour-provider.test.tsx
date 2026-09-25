import React from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  getProductTourStorageKey,
  readProductTourStatus,
} from "@/lib/product-tour";

const mockUseAuth = vi.hoisted(() => vi.fn());
const mockUseUserPermissions = vi.hoisted(() => vi.fn());
const mockUseJoyride = vi.hoisted(() => vi.fn());
const mockUsePathname = vi.hoisted(() => vi.fn(() => "/dashboard"));
const mockPush = vi.hoisted(() => vi.fn());
const mockControls = {
  reset: vi.fn(),
  start: vi.fn(),
  stop: vi.fn(),
  skip: vi.fn(),
};
const localStorageValues = new Map<string, string>();
const localStorageMock = {
  clear: () => localStorageValues.clear(),
  getItem: (key: string) => localStorageValues.get(key) ?? null,
  removeItem: (key: string) => localStorageValues.delete(key),
  setItem: (key: string, value: string) => localStorageValues.set(key, value),
};

vi.mock("@/contexts/auth-context", () => ({
  useAuth: () => mockUseAuth(),
}));

vi.mock("@/hooks/use-user-permissions", () => ({
  useUserPermissions: () => mockUseUserPermissions(),
}));

vi.mock("next/navigation", () => ({
  usePathname: () => mockUsePathname(),
  useRouter: () => ({ push: mockPush }),
}));

vi.mock("react-joyride", () => ({
    ACTIONS: { COMPLETE: "complete", SKIP: "skip" },
  EVENTS: { TOUR_START: "tour:start", TOUR_END: "tour:end" },
  STATUS: { FINISHED: "finished", SKIPPED: "skipped" },
    useJoyride: (props: unknown) => {
    mockUseJoyride(props);
    return { controls: mockControls, Tour: <div data-testid="joyride" /> };
  },
}));

import {
  ProductTourProvider,
  ProductTourTooltip,
  useProductTour,
} from "../product-tour-provider";

function RestartButton() {
  const { restartProductTour } = useProductTour();
  return <button onClick={restartProductTour}>Restart walkthrough</button>;
}

function OpenButton() {
  const { openProductTour } = useProductTour();
  return <button onClick={openProductTour}>Open walkthrough</button>;
}

function renderTour() {
  return render(
    <ProductTourProvider>
      <div data-tour="brand" />
      <div data-tour="agents-page" />
      <div data-tour="calls-page" />
      <RestartButton />
      <OpenButton />
    </ProductTourProvider>,
  );
}

describe("ProductTourProvider", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Object.defineProperty(window, "localStorage", {
      configurable: true,
      value: localStorageMock,
    });
    window.localStorage.clear();
    mockUsePathname.mockReturnValue("/dashboard");
    mockUseAuth.mockReturnValue({
      user: { id: "user-123" },
      loading: false,
    });
    mockUseUserPermissions.mockReturnValue({
      isPlatformAdmin: false,
      isOrgAdmin: false,
      isLoading: false,
    });
  });

  it("starts the regular-user walkthrough once when no outcome is stored", async () => {
    renderTour();

    await waitFor(() => {
      const latestProps = mockUseJoyride.mock.lastCall?.[0] as {
        run: boolean;
        steps: Array<{ id?: string }>;
      };
      expect(latestProps.run).toBe(true);
      expect(
        (latestProps.steps[0] as { skipBeacon?: boolean }).skipBeacon,
      ).toBe(true);
      expect(latestProps.steps.map((step) => step.id)).toHaveLength(7);
    });
  });

  it("persists a skip event so the tour does not immediately return", async () => {
    renderTour();

    await waitFor(() => expect(mockUseJoyride).toHaveBeenCalled());
    const latestProps = mockUseJoyride.mock.lastCall?.[0] as {
      onEvent: (data: unknown, controls: unknown) => void;
    };

    act(() => {
      latestProps.onEvent(
        { action: "skip", status: "skipped", type: "tour:end" },
        mockControls,
      );
    });

    expect(readProductTourStatus(window.localStorage, "user-123")).toBe(
      "skipped",
    );
  });

  it("persists a completed event and does not auto-start a completed tour", async () => {
    renderTour();

    await waitFor(() => expect(mockUseJoyride).toHaveBeenCalled());
    const latestProps = mockUseJoyride.mock.lastCall?.[0] as {
      onEvent: (data: unknown, controls: unknown) => void;
    };

    act(() => {
      latestProps.onEvent(
        { action: "complete", status: "finished", type: "tour:end" },
        mockControls,
      );
    });

    expect(readProductTourStatus(window.localStorage, "user-123")).toBe(
      "completed",
    );

    mockUseJoyride.mockClear();
    renderTour();
    await waitFor(() => {
      const latestProps = mockUseJoyride.mock.lastCall?.[0] as {
        run: boolean;
      };
      expect(latestProps.run).toBe(false);
    });
  });

  it("uses the complete role-specific step set for platform users", async () => {
    mockUseUserPermissions.mockReturnValue({
      isPlatformAdmin: true,
      isOrgAdmin: true,
      isLoading: false,
    });

    renderTour();

    await waitFor(() => {
      const latestProps = mockUseJoyride.mock.lastCall?.[0] as {
        steps: Array<{ id?: string }>;
      };
      expect(latestProps.steps).toHaveLength(17);
    });
  });

  it("clears the outcome and restarts from the beginning on request", async () => {
    window.localStorage.setItem(getProductTourStorageKey("user-123"), "completed");
    renderTour();

    fireEvent.click(screen.getByRole("button", { name: "Restart walkthrough" }));

    expect(
      readProductTourStatus(window.localStorage, "user-123"),
    ).toBeNull();
    await waitFor(() => {
      const latestProps = mockUseJoyride.mock.lastCall?.[0] as { run: boolean };
      expect(latestProps.run).toBe(true);
    });
  });

  it("starts the requested branch on its route and exposes a return to overview", async () => {
    renderTour();

    await waitFor(() => expect(mockUseJoyride).toHaveBeenCalled());
    const mainProps = mockUseJoyride.mock.lastCall?.[0] as {
      steps: Array<{ data?: { onExplore?: () => void } }>;
    };

    act(() => {
      mainProps.steps[2].data?.onExplore?.();
    });

    await waitFor(() => expect(mockPush).toHaveBeenCalledWith("/agents"));
    const branchProps = mockUseJoyride.mock.lastCall?.[0] as {
      steps: Array<{ data?: { onBack?: () => void }; id?: string }>;
    };
    expect(branchProps.steps[0].id).toBe("agents-overview");
    expect(branchProps.steps[0].data?.onBack).toBeTypeOf("function");
  });

  it("automatically starts a contextual tour on the first visit to an internal page", async () => {
    mockUsePathname.mockReturnValue("/agents");
    window.localStorage.setItem(getProductTourStorageKey("user-123"), "completed");
    renderTour();

    await waitFor(() => {
      const latestProps = mockUseJoyride.mock.lastCall?.[0] as {
        run: boolean;
        steps: Array<{ id?: string }>;
      };
      expect(latestProps.run).toBe(true);
      expect(latestProps.steps[0].id).toBe("agents-overview");
    });
  });

  it("opens the contextual tour from the global help action", async () => {
    mockUsePathname.mockReturnValue("/agents");
    window.localStorage.setItem(getProductTourStorageKey("user-123"), "completed");
    renderTour();

    fireEvent.click(screen.getByRole("button", { name: "Open walkthrough" }));

    await waitFor(() => {
      const latestProps = mockUseJoyride.mock.lastCall?.[0] as {
        run: boolean;
        steps: Array<{ id?: string }>;
      };
      expect(latestProps.run).toBe(true);
      expect(latestProps.steps[0].id).toBe("agents-overview");
    });
  });

  it("keeps a contextual tour on its page after completion", async () => {
    mockUsePathname.mockReturnValue("/calls");
    window.localStorage.setItem(getProductTourStorageKey("user-123"), "completed");
    renderTour();

    await waitFor(() => {
      const latestProps = mockUseJoyride.mock.lastCall?.[0] as {
        run: boolean;
        steps: Array<{ id?: string }>;
      };
      expect(latestProps.run).toBe(true);
      expect(latestProps.steps[0].id).toBe("calls-overview");
    });

    const latestProps = mockUseJoyride.mock.lastCall?.[0] as {
      onEvent: (data: unknown, controls: unknown) => void;
    };
    act(() => {
      latestProps.onEvent(
        { action: "complete", status: "finished", type: "tour:end" },
        mockControls,
      );
    });

    expect(
      readProductTourStatus(window.localStorage, "user-123", "member", "calls"),
    ).toBe("completed");
    expect(mockPush).not.toHaveBeenCalled();
  });

  it("uses app theme tokens for the tooltip surface and controls", () => {
    const noop = () => undefined;
    const props = {
      backProps: {
        "aria-label": "Back",
        "data-action": "back",
        onClick: noop,
        role: "button",
        title: "Back",
      },
      closeProps: {
        "aria-label": "Close",
        "data-action": "close",
        onClick: noop,
        role: "button",
        title: "Close",
      },
      continuous: true,
      controls: mockControls,
      index: 0,
      isLastStep: false,
      primaryProps: {
        "aria-label": "Next",
        "data-action": "primary",
        onClick: noop,
        role: "button",
        title: "Next",
      },
      size: 2,
      skipProps: {
        "aria-label": "Skip tour",
        "data-action": "skip",
        onClick: noop,
        role: "button",
        title: "Skip tour",
      },
      step: {
        content: "Theme-aware content",
        data: { tour: "main" },
        title: "Theme-aware tour",
      },
      tooltipProps: { "aria-modal": true, role: "dialog" },
    } as unknown as Parameters<typeof ProductTourTooltip>[0];

    render(<ProductTourTooltip {...props} />);

    const tooltip = screen.getByRole("dialog");
    expect(tooltip.className).toContain("bg-popover");
    expect(tooltip.className).toContain("text-popover-foreground");
    const nextButton = screen.getByRole("button", { name: "Next" });
    expect(nextButton.className).toContain("bg-primary");
    expect(nextButton.className).toContain("text-primary-foreground");
  });
});
