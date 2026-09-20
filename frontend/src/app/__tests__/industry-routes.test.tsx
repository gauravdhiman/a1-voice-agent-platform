/** New vertical landing pages render their story with working CTAs. */
import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import RestaurantsPage from "../restaurants/page";
import SalonsPage from "../salons/page";
import RealEstatePage from "../real-estate/page";

afterEach(() => {
  cleanup();
});

describe.each([
  {
    name: "restaurants",
    Page: RestaurantsPage,
    heading: "Every call answered, every table filled",
    demoHref: "/demo/verdi-table-restaurant",
  },
  {
    name: "salons",
    Page: SalonsPage,
    heading: "Fully booked chairs, zero phone tag",
    demoHref: "/demo/pleasant-pediatric-appointments",
  },
  {
    name: "real estate",
    Page: RealEstatePage,
    heading: "Every enquiry answered, every viewing booked",
    demoHref: "/demo/copper-ridge-service-request",
  },
])("$name landing page", ({ Page, heading, demoHref }) => {
  it("renders its headline with demo and request-demo entry points", () => {
    render(<Page />);
    expect(screen.getByRole("heading", { name: heading })).toBeTruthy();
    expect(
      screen
        .getAllByRole("link")
        .some((link) => link.getAttribute("href") === demoHref),
    ).toBe(true);
    expect(
      screen
        .getAllByRole("link")
        .some((link) => link.getAttribute("href") === "/request-demo"),
    ).toBe(true);
    expect(screen.queryByText(/acme corp|techstart/i)).toBeNull();
  });
});
