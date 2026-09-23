/** Single site-wide theme: one persisted choice honored on public pages. */
import React from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ThemeProvider, useTheme } from "@/contexts/theme-context";
import {
  PUBLIC_THEME_STORAGE_KEY,
  usePublicTheme,
} from "./public-theme-context";
import { PublicThemeRoot } from "./public-theme-root";
import { PublicHeader } from "./public-header";
import { PublicFooter } from "./public-footer";
import { SiteThemeSwitch, ThemeSwitch } from "./theme-switch";

function ThemeProbe() {
  const { theme } = usePublicTheme();
  return <span data-testid="theme-probe">{theme}</span>;
}

function DashboardProbe() {
  const { theme, setTheme } = useTheme();
  return (
    <button data-testid="dashboard-probe" onClick={() => setTheme("dark")}>
      dashboard:{theme}
    </button>
  );
}

beforeEach(() => {
  const values = new Map<string, string>();
  vi.stubGlobal("localStorage", {
    getItem: vi.fn((key: string) => values.get(key) ?? null),
    setItem: vi.fn((key: string, value: string) => values.set(key, value)),
  });
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("Public theme choice", () => {
  it("starts in night mode and persists the toggle under one key", () => {
    expect(PUBLIC_THEME_STORAGE_KEY).toBe("theme");
    const { container } = render(
      <ThemeProvider>
        <PublicThemeRoot>
          <ThemeProbe />
        </PublicThemeRoot>
      </ThemeProvider>,
    );
    expect(screen.getByTestId("theme-probe").textContent).toBe("night");
    expect(container.querySelector("[data-theme='night']")).toBeTruthy();
    expect(container.querySelector(".dark")).toBeTruthy();
  });

  it("restores a persisted light choice and toggles back to dark", () => {
    localStorage.setItem("theme", "light");
    render(
      <ThemeProvider>
        <PublicThemeRoot>
          <PublicHeader />
        </PublicThemeRoot>
      </ThemeProvider>,
    );
    expect(
      screen.getByRole("switch", { name: "Switch to night mode" }),
    ).toBeTruthy();
    fireEvent.click(
      screen.getByRole("switch", { name: "Switch to night mode" }),
    );
    expect(localStorage.getItem("theme")).toBe("dark");
    expect(
      screen.getByRole("switch", { name: "Switch to day mode" }),
    ).toBeTruthy();
  });

  it("migrates the legacy public-pages key without losing the choice", () => {
    localStorage.setItem("247ai-home-theme", "day");
    render(
      <ThemeProvider>
        <PublicThemeRoot>
          <ThemeProbe />
        </PublicThemeRoot>
      </ThemeProvider>,
    );
    expect(screen.getByTestId("theme-probe").textContent).toBe("day");
    expect(localStorage.getItem("theme")).toBe("light");
  });

  it("shares one state between the public toggle and dashboard controls", () => {
    render(
      <ThemeProvider>
        <PublicThemeRoot>
          <PublicHeader />
          <DashboardProbe />
        </PublicThemeRoot>
      </ThemeProvider>,
    );
    // Public toggle writes an explicit choice the dashboard sees.
    fireEvent.click(screen.getByRole("switch", { name: "Switch to day mode" }));
    expect(screen.getByTestId("dashboard-probe").textContent).toContain(
      "light",
    );
    // A dashboard control flips the public surface back.
    fireEvent.click(screen.getByTestId("dashboard-probe"));
    expect(
      screen.getByRole("switch", { name: "Switch to day mode" }),
    ).toBeTruthy();
  });

  it("keeps switching when storage is unavailable", () => {
    vi.spyOn(localStorage, "getItem").mockImplementation(() => {
      throw new Error("Storage denied");
    });
    vi.spyOn(localStorage, "setItem").mockImplementation(() => {
      throw new Error("Storage denied");
    });
    render(
      <ThemeProvider>
        <PublicHeader />
      </ThemeProvider>,
    );
    fireEvent.click(screen.getByRole("switch", { name: "Switch to day mode" }));
    expect(
      screen.getByRole("switch", { name: "Switch to night mode" }),
    ).toBeTruthy();
  });
});

describe("ThemeSwitch", () => {
  it("positions the knob and labels by state, toggling on click", () => {
    const onToggle = vi.fn();
    const { rerender } = render(
      <ThemeSwitch dark={false} onToggle={onToggle} />,
    );
    const off = screen.getByRole("switch", { name: "Switch to night mode" });
    expect(off.getAttribute("aria-checked")).toBe("false");
    expect(off.getAttribute("data-dark")).toBe("false");
    fireEvent.click(off);
    expect(onToggle).toHaveBeenCalledTimes(1);
    rerender(<ThemeSwitch dark onToggle={onToggle} />);
    const on = screen.getByRole("switch", { name: "Switch to day mode" });
    expect(on.getAttribute("aria-checked")).toBe("true");
    expect(on.getAttribute("data-dark")).toBe("true");
  });

  it("follows the resolved site theme in the dashboard wiring", () => {
    localStorage.setItem("theme", "dark");
    render(
      <ThemeProvider>
        <SiteThemeSwitch />
      </ThemeProvider>,
    );
    expect(
      screen.getByRole("switch", { name: "Switch to day mode" }),
    ).toBeTruthy();
    fireEvent.click(screen.getByRole("switch"));
    expect(localStorage.getItem("theme")).toBe("light");
  });
});

describe("Public chrome", () => {
  it("links the homepage sections, sign-in, and conversation CTA", () => {
    render(
      <ThemeProvider>
        <PublicThemeRoot>
          <PublicHeader />
          <PublicFooter />
        </PublicThemeRoot>
      </ThemeProvider>,
    );
    for (const name of [
      "Use cases",
      "Live demos",
      "For your business",
      "Integrations",
      "Pricing",
    ]) {
      expect(screen.getAllByRole("link", { name }).length).toBeGreaterThan(0);
    }
    expect(
      screen
        .getAllByRole("link", { name: /let's talk/i })
        .every((link) => link.getAttribute("href") === "/request-demo"),
    ).toBe(true);
    expect(
      screen
        .getAllByRole("link", { name: /sign in/i })
        .every((link) => link.getAttribute("href") === "/auth/signin"),
    ).toBe(true);
  });

  it("opens a right-drawer navigation and closes it on selection", () => {
    render(
      <ThemeProvider>
        <PublicThemeRoot>
          <PublicHeader />
        </PublicThemeRoot>
      </ThemeProvider>,
    );

    fireEvent.click(screen.getByLabelText("Open navigation"));
    const mobileNavigation = screen.getByLabelText("Mobile navigation");
    const liveDemosLink = mobileNavigation.querySelector(
      'a[href="/#demos"]',
    );
    expect(liveDemosLink).toBeTruthy();

    fireEvent.click(liveDemosLink!);
    expect(
      screen.queryByRole("navigation", { name: "Mobile navigation" }),
    ).toBeNull();
  });
});
