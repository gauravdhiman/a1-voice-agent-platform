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
    expect(screen.getByText(/monthly plans from \$49/i)).toBeTruthy();
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

  it("shows all five chapters with illustrative previews", () => {
    render(<HowItWorksPage />);
    for (const name of [
      /describe your business in plain words/i,
      /one AI assistant, your number and website/i,
      /tools you already use/i,
      /teach it your way of working/i,
      /without listening to each one/i,
    ]) {
      expect(screen.getByRole("heading", { name })).toBeTruthy();
    }
    expect(screen.getAllByText("Illustrative preview").length).toBeGreaterThan(0);
    expect(
      document.querySelectorAll('[data-looping-preview="true"]').length,
    ).toBeGreaterThanOrEqual(5);
  });

  it("shows distinct scenes across setup, phone, and call-review chapters", () => {
    render(<HowItWorksPage />);
    expect(screen.getByText("Agent saved")).toBeTruthy();
    expect(screen.getByText("Front desk · test line")).toBeTruthy();
    expect(screen.getByText("Live, able to answer now")).toBeTruthy();
    expect(screen.getByText("(555) 014-2200")).toBeTruthy();
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
