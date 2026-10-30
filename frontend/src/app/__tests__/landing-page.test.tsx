/** Public homepage contracts: business messaging, working funnel links, scoped
 * persistent themes, mobile navigation, and an explicit ambient-motion control. */
import React from "react";
import { fireEvent, render, screen, cleanup } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import LandingPage from "../page";
import { ThemeProvider } from "@/contexts/theme-context";

vi.mock("@/components/home/particle-field", () => ({
  ParticleField: () => <canvas aria-hidden="true" />,
}));

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

describe("Homepage experience", () => {
  it("leads with business outcomes and real demo entry points", () => {
    render(
      <ThemeProvider>
        <LandingPage />
      </ThemeProvider>,
    );
    expect(screen.getAllByText("24x7 AI").length).toBeGreaterThan(0);
    expect(
      screen.getByRole("heading", {
        level: 1,
        name: /never miss a call\.\s*never miss a customer/i,
      }),
    ).toBeTruthy();
    expect(screen.getByText(/no coding required/i)).toBeTruthy();
    expect(screen.getByText("Up to 85%")).toBeTruthy();
    expect(screen.getByText("42%")).toBeTruthy();
    expect(screen.getByText("56%")).toBeTruthy();
    expect(
      screen
        .getByRole("link", { name: /try a live demo call/i })
        .getAttribute("href"),
    ).toBe("#demos");
    expect(
      screen
        .getByRole("link", { name: /request setup call/i })
        .getAttribute("href"),
    ).toBe("/request-demo");
    expect(
      screen.getByRole("link", { name: /talk to alex/i }).getAttribute("href"),
    ).toBe("/demo/pleasant-pediatric-appointments");
    expect(
      screen
        .getByRole("link", { name: /talk to jordan/i })
        .getAttribute("href"),
    ).toBe("/demo/copper-ridge-service-request");
    expect(
      screen
        .getByRole("link", { name: /talk to sofia/i })
        .getAttribute("href"),
    ).toBe("/demo/verdi-table-restaurant");
    expect(screen.queryByText(/acme corp|techstart|sarah chen/i)).toBeNull();
    expect(screen.getByText(/plans from \$79\/month/i)).toBeTruthy();
    expect(screen.queryByText(/\$99|\$0/)).toBeNull();
  });

  it("links the guided tour band to the platform tour", () => {
    render(
      <ThemeProvider>
        <LandingPage />
      </ThemeProvider>,
    );
    expect(
      screen.getByRole("link", { name: /take the guided tour/i }).getAttribute(
        "href",
      ),
    ).toBe("/how-it-works");
    expect(
      screen
        .getByRole("link", { name: /set instructions.*rules, not code/i })
        .getAttribute("href"),
    ).toBe("/how-it-works#tour-teach-skills");
  });

  it("covers one use case per chapter and generalizes tooling in the journey", () => {
    render(
      <ThemeProvider>
        <LandingPage />
      </ThemeProvider>,
    );
    expect(
      screen.getByRole("heading", { name: /routine questions/i }),
    ).toBeTruthy();
    expect(
      screen.getByRole("heading", { name: /you're booked/i }),
    ).toBeTruthy();
    expect(
      screen.getByRole("heading", { name: /close up shop/i }),
    ).toBeTruthy();
    expect(
      screen.queryByText(/syncs everything to google calendar/i),
    ).toBeNull();
    expect(screen.queryByText(/logged to google sheets/i)).toBeNull();
  });

  it("lists industries and names specific tools only in integrations", () => {
    render(
      <ThemeProvider>
        <LandingPage />
      </ThemeProvider>,
    );
    expect(
      screen.getByRole("heading", { name: /take the call/i }),
    ).toBeTruthy();
    expect(
      screen
        .getByRole("link", { name: /dental & medical/i })
        .getAttribute("href"),
    ).toBe("/dental-appointment-booking");
    expect(
      screen
        .getByRole("link", { name: /hvac, plumbing & roofing/i })
        .getAttribute("href"),
    ).toBe("/hvac-service-call-answering");
    expect(
      screen
        .getByRole("link", { name: /plumbing & emergency home services/i })
        .getAttribute("href"),
    ).toBe("/plumbing-service-requests");
    expect(
      screen
        .getByRole("link", { name: /independent auto repair/i })
        .getAttribute("href"),
    ).toBe("/auto-repair-service-booking");
    expect(
      screen.getByRole("heading", { name: /plugs into the tools/i }),
    ).toBeTruthy();
  });

  it("links live demos from the header and covers six integrations", () => {
    render(
      <ThemeProvider>
        <LandingPage />
      </ThemeProvider>,
    );
    const demoLinks = screen.getAllByRole("link", { name: "Live demos" });
    expect(demoLinks.length).toBeGreaterThanOrEqual(2);
    expect(
      demoLinks.some((link) => link.getAttribute("href") === "/#demos"),
    ).toBe(true);
    expect(document.getElementById("demos")).toBeTruthy();
    for (const name of [
      /business calendar/i,
      /records & crm/i,
      /your business number/i,
      /your website/i,
      /custom business tools/i,
    ]) {
      expect(screen.getByRole("heading", { name })).toBeTruthy();
    }
    expect(
      screen.getByRole("heading", { name: /need more than a front desk/i }),
    ).toBeTruthy();
    expect(
      screen
        .getAllByRole("link", { name: /explore custom ai solutions/i })
        .some((link) => link.getAttribute("href") === "https://cognients.com"),
    ).toBe(true);
    expect(
      screen
        .getByRole("link", {
          name: /visit cognitive entities llc/i,
        })
        .getAttribute("href"),
    ).toBe("https://cognients.com");
  });

  it("changes theme, persists the choice, and restores it on return", () => {
    const { container, unmount } = render(
      <ThemeProvider>
        <LandingPage />
      </ThemeProvider>,
    );
    fireEvent.click(screen.getByRole("switch", { name: "Switch to day mode" }));
    expect(container.querySelector("[data-theme='day']")).toBeTruthy();
    expect(localStorage.getItem("theme")).toBe("light");
    unmount();
    render(
      <ThemeProvider>
        <LandingPage />
      </ThemeProvider>,
    );
    expect(
      screen.getByRole("switch", { name: "Switch to night mode" }),
    ).toBeTruthy();
    fireEvent.click(
      screen.getByRole("switch", { name: "Switch to night mode" }),
    );
    expect(localStorage.getItem("theme")).toBe("dark");
  });

  it("keeps theme switching usable when storage is unavailable", () => {
    const read = vi.spyOn(localStorage, "getItem").mockImplementation(() => {
      throw new Error("Storage denied");
    });
    const write = vi.spyOn(localStorage, "setItem").mockImplementation(() => {
      throw new Error("Storage denied");
    });
    render(
      <ThemeProvider>
        <LandingPage />
      </ThemeProvider>,
    );
    fireEvent.click(screen.getByRole("switch", { name: "Switch to day mode" }));
    expect(
      screen.getByRole("switch", { name: "Switch to night mode" }),
    ).toBeTruthy();
    read.mockRestore();
    write.mockRestore();
  });

  it("provides a reversible message-rotation control", () => {
    render(
      <ThemeProvider>
        <LandingPage />
      </ThemeProvider>,
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Pause message rotation" }),
    );
    expect(
      screen
        .getByRole("button", { name: "Play message rotation" })
        .getAttribute("aria-pressed"),
    ).toBe("true");
    fireEvent.click(
      screen.getByRole("button", { name: "Play message rotation" }),
    );
    expect(
      screen
        .getByRole("button", { name: "Pause message rotation" })
        .getAttribute("aria-pressed"),
    ).toBe("false");
  });

  it("opens mobile navigation and dismisses it on selection or Escape", () => {
    render(
      <ThemeProvider>
        <LandingPage />
      </ThemeProvider>,
    );
    fireEvent.click(screen.getByLabelText("Open navigation"));
    expect(screen.getByLabelText("Mobile navigation")).toBeTruthy();
    fireEvent.keyDown(screen.getByLabelText("Mobile navigation"), {
      key: "Escape",
    });
    expect(screen.queryByLabelText("Mobile navigation")).toBeNull();
    fireEvent.click(screen.getByLabelText("Open navigation"));
    fireEvent.click(
      screen
        .getByLabelText("Mobile navigation")
        .querySelector('a[href="/#demos"]')!,
    );
    expect(screen.queryByLabelText("Mobile navigation")).toBeNull();
  });
});
