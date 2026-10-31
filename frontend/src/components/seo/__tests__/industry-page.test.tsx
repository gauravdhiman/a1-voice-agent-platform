import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
  IndustryPage,
  type IndustryPageContent,
} from "@/components/seo/industry-page";
import { formatMonthlyPrice, PLANS } from "@/lib/pricing/plans";

const content: IndustryPageContent = {
  slug: "dental",
  headline: "Your dental practice, always answering",
  subhead: "Books cleanings while you work.",
  pains: ["Missed after-hours calls."],
  outcomes: [{ title: "Booking", description: "Books visits." }],
  demoSlug: "pleasant-pediatric-appointments",
  demoBlurb: "Try the live demo.",
  proof: {
    eyebrow: "THE CALL, BY THE NUMBERS",
    title: "The next step should be easy.",
    description: "A compact proof section.",
    points: [{ value: "43%", label: "of calls are leads." }],
    sourceNote: "Directional benchmark.",
    sources: [{ label: "Research", href: "https://example.com/research" }],
  },
  faqs: [
    {
      question: "What does it cost?",
      answer: `Plans from ${formatMonthlyPrice(PLANS.STARTER.monthlyUSD)}.`,
    },
  ],
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
    const demoLinks = screen.getAllByRole("link", {
      name: /try the live demo/i,
    });
    expect(demoLinks.length).toBeGreaterThan(0);
    expect(demoLinks[0].getAttribute("href")).toBe(
      "/demo/pleasant-pediatric-appointments",
    );
    expect(
      screen.getAllByRole("link", { name: /request a demo/i }).length,
    ).toBeGreaterThan(0);
    expect(screen.getByText("43%")).not.toBeNull();
    expect(
      screen.getByRole("link", { name: /research/i }).getAttribute("href"),
    ).toBe("https://example.com/research");
    const toolsHeading = screen.getByRole("heading", {
      name: /your existing business tools/i,
    });
    expect(toolsHeading).toBeTruthy();
    expect(toolsHeading.parentElement?.parentElement?.className).toContain(
      "outcomeGrid",
    );
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

  it("uses a request-workflow CTA when a vertical has no public demo", () => {
    const noDemoContent: IndustryPageContent = {
      ...content,
      demoSlug: undefined,
      demoBlurb: "No public demo yet.",
    };

    render(<IndustryPage content={noDemoContent} />);

    expect(
      screen
        .getByRole("link", { name: /request this workflow/i })
        .getAttribute("href"),
    ).toBe("/request-demo");
    expect(
      screen.queryByRole("link", { name: /try the live demo/i }),
    ).toBeNull();
    expect(screen.getByText("No public demo yet.")).not.toBeNull();
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
