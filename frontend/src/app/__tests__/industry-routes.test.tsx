/** New vertical landing pages render their story with working CTAs. */
import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import RestaurantsPage from "../restaurant-order-taking/page";
import SalonsPage from "../salon-appointment-booking/page";
import RealEstatePage from "../real-estate-lead-capture/page";
import PlumbingPage from "../plumbing-service-requests/page";
import AutoRepairPage from "../auto-repair-service-booking/page";
import VeterinaryPage from "../veterinary-appointment-booking/page";

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
  {
    name: "plumbing",
    Page: PlumbingPage,
    heading: "The crew is on a job. The next job still gets captured.",
    primaryHref: "/request-demo",
  },
  {
    name: "auto repair",
    Page: AutoRepairPage,
    heading: "Turn the service call into scheduled work.",
    primaryHref: "/request-demo",
  },
  {
    name: "veterinary",
    Page: VeterinaryPage,
    heading: "Keep the front desk present for every pet parent.",
    primaryHref: "/request-demo",
  },
])("$name landing page", ({ Page, heading, demoHref, primaryHref }) => {
  it("renders its headline with the right primary entry point", () => {
    render(<Page />);
    expect(screen.getByRole("heading", { name: heading })).toBeTruthy();
    const expectedPrimaryHref = demoHref ?? primaryHref;
    expect(
      screen
        .getAllByRole("link")
        .some((link) => link.getAttribute("href") === expectedPrimaryHref),
    ).toBe(true);
    expect(
      screen
        .getAllByRole("link")
        .some((link) => link.getAttribute("href") === "/request-demo"),
    ).toBe(true);
    expect(screen.queryByText(/acme corp|techstart/i)).toBeNull();
  });
});
