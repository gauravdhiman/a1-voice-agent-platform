import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
  IndustryPage,
  type IndustryPageContent,
} from "@/components/seo/industry-page";

const content: IndustryPageContent = {
  slug: "dental",
  headline: "Your dental practice, always answering",
  subhead: "Books cleanings while you work.",
  pains: ["Missed after-hours calls."],
  outcomes: [{ title: "Booking", description: "Books visits." }],
  demoSlug: "pleasant-pediatric-appointments",
  demoName: "Alex",
  demoBlurb: "Try the live demo.",
  faqs: [{ question: "What does it cost?", answer: "Pilots from $79/mo." }],
};

describe("IndustryPage", () => {
  it("renders the vertical story with demo and request-demo CTAs", () => {
    render(<IndustryPage content={content} />);

    expect(
      screen.getByRole("heading", {
        name: "Your dental practice, always answering",
      }),
    ).not.toBeNull();
    expect(screen.getByText("Missed after-hours calls.")).not.toBeNull();
    const demoLinks = screen.getAllByRole("link", { name: /talk to alex now/i });
    expect(demoLinks.length).toBeGreaterThan(0);
    expect(
      demoLinks[0].getAttribute("href"),
    ).toBe("/demo/pleasant-pediatric-appointments");
    expect(
      screen.getAllByRole("link", { name: /request a demo/i }).length,
    ).toBeGreaterThan(0);
  });

  it("emits FAQ JSON-LD for search engines", () => {
    const { container } = render(<IndustryPage content={content} />);
    const script = container.querySelector(
      'script[type="application/ld+json"]',
    );
    expect(script).not.toBeNull();
    const payload = JSON.parse(script?.textContent ?? "{}");
    expect(payload["@type"]).toBe("FAQPage");
    expect(payload.mainEntity).toHaveLength(1);
    expect(payload.mainEntity[0].name).toBe("What does it cost?");
  });
});
