/** Guided platform tour: five chapters, replayable run-throughs, and working funnel links. */
import React from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import HowItWorksPage from "../how-it-works/page";

afterEach(() => {
  cleanup();
});

describe("Platform tour", () => {
  it("leads with business outcomes and the primary funnel", () => {
    render(<HowItWorksPage />);
    expect(
      screen.getByRole("heading", {
        level: 1,
        name: /from hello to booked, on every call/i,
      }),
    ).toBeTruthy();
    expect(screen.getByText(/no coding required/i)).toBeTruthy();
    expect(screen.getByText(/monthly plans from \$79/i)).toBeTruthy();
    expect(
      screen
        .getAllByRole("link", { name: /request a demo/i })
        .some((link) => link.getAttribute("href") === "/request-demo"),
    ).toBe(true);
    expect(
      screen.getByRole("link", { name: "Hear Alex handle a live demo call" })
        .getAttribute("href"),
    ).toBe("/demo/pleasant-pediatric-appointments");
    expect(screen.queryByText(/lorem|acme corp/i)).toBeNull();
  });

  it("shows all five chapters with replayable run-throughs", () => {
    render(<HowItWorksPage />);
    for (const name of [
      /describe your business/i,
      /one agent, every place/i,
      /tools you already use/i,
      /teach it your way/i,
      /without hearing all/i,
    ]) {
      expect(screen.getByRole("heading", { name })).toBeTruthy();
    }
    expect(screen.getAllByText("Illustrative preview").length).toBeGreaterThan(0);
    const pauseButtons = screen.getAllByRole("button", {
      name: "Pause the run-through",
    });
    expect(pauseButtons.length).toBeGreaterThan(0);
    fireEvent.click(pauseButtons[0]);
    expect(
      screen
        .getAllByRole("button", { name: "Play the run-through" })[0]
        .getAttribute("aria-pressed"),
    ).toBe("true");
    fireEvent.click(
      screen.getAllByRole("button", { name: /replay .* from the start/i })[0],
    );
    expect(
      screen.getAllByRole("button", { name: /pause the run-through/i })[0],
    ).toBeTruthy();
  });

  it("plays a dedicated scene per step, not one generic card", () => {
    render(<HowItWorksPage />);
    expect(screen.getByText("Agent saved")).toBeTruthy();
    fireEvent.click(
      screen.getByRole("button", { name: /step 2: hear it back on a test call/i }),
    );
    expect(screen.getByText("Front desk · test line")).toBeTruthy();
    fireEvent.click(
      screen.getByRole("button", { name: /step 3: approve it/i }),
    );
    expect(screen.getByText("Live, able to answer now")).toBeTruthy();
    fireEvent.click(
      screen.getByRole("button", { name: /step 1: keep your business number/i }),
    );
    expect(screen.getByText("(555) 014-2200")).toBeTruthy();
    fireEvent.click(
      screen.getByRole("button", { name: /step 3: kept for 30 days/i }),
    );
    expect(screen.getByText("Recordings kept 30 days")).toBeTruthy();
  });

  it("closes with the setup spine and sales contact", () => {
    render(<HowItWorksPage />);
    expect(
      screen.getByRole("heading", { name: /easy to set up/i }),
    ).toBeTruthy();
    expect(
      screen.getByRole("heading", { name: /stop losing work/i }),
    ).toBeTruthy();
    expect(
      screen
        .getByRole("link", { name: /talk to sales/i })
        .getAttribute("href"),
    ).toBe("mailto:sales@247ai.live");
  });
});
