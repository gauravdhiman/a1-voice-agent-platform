/** Shared public theme: persisted day/night choice and common chrome. */
import React from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  PUBLIC_THEME_STORAGE_KEY,
  PublicThemeProvider,
  usePublicTheme,
} from "./public-theme-context";
import { PublicThemeRoot } from "./public-theme-root";
import { PublicHeader } from "./public-header";
import { PublicFooter } from "./public-footer";

function ThemeProbe() {
  const { theme } = usePublicTheme();
  return <span data-testid="theme-probe">{theme}</span>;
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
  it("starts in night mode and persists the toggle", () => {
    const { container } = render(
      <PublicThemeRoot>
        <ThemeProbe />
      </PublicThemeRoot>,
    );
    expect(screen.getByTestId("theme-probe").textContent).toBe("night");
    expect(container.querySelector("[data-theme='night']")).toBeTruthy();
    expect(container.querySelector(".dark")).toBeTruthy();
  });

  it("restores a persisted day choice and toggles back", () => {
    localStorage.setItem(PUBLIC_THEME_STORAGE_KEY, "day");
    render(
      <PublicThemeRoot>
        <PublicHeader />
      </PublicThemeRoot>,
    );
    expect(
      screen.getByRole("button", { name: "Switch to night mode" }),
    ).toBeTruthy();
    fireEvent.click(
      screen.getByRole("button", { name: "Switch to night mode" }),
    );
    expect(localStorage.getItem(PUBLIC_THEME_STORAGE_KEY)).toBe("night");
    expect(
      screen.getByRole("button", { name: "Switch to day mode" }),
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
      <PublicThemeProvider>
        <PublicHeader />
      </PublicThemeProvider>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Switch to day mode" }));
    expect(
      screen.getByRole("button", { name: "Switch to night mode" }),
    ).toBeTruthy();
  });
});

describe("Public chrome", () => {
  it("links the homepage sections, sign-in, and demo request", () => {
    render(
      <PublicThemeRoot>
        <PublicHeader />
        <PublicFooter />
      </PublicThemeRoot>,
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
        .getAllByRole("link", { name: /request a demo/i })
        .every((link) => link.getAttribute("href") === "/request-demo"),
    ).toBe(true);
    expect(
      screen
        .getAllByRole("link", { name: /sign in/i })
        .every((link) => link.getAttribute("href") === "/auth/signin"),
    ).toBe(true);
  });
});
