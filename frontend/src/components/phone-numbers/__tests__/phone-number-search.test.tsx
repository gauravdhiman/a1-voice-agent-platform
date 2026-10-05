import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { AvailablePhoneNumber } from "@/types/phone-number";

const { searchAvailable } = vi.hoisted(() => ({
  searchAvailable: vi.fn(),
}));

vi.mock("@/services/phone-number-service", () => ({
  phoneNumberService: { searchAvailable },
}));

vi.mock("sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn() },
}));

import { PhoneNumberSearch } from "../phone-number-search";

const AVAILABLE_NUMBER: AvailablePhoneNumber = {
  phone_number: "+14805550100",
  phone_number_type: "local",
  country_code: "US",
  area_code: "480",
  monthly_cost_credits: 500,
  capabilities: { voice: true },
  locality: "Phoenix",
  postal_code: "85001",
};

const SEARCH_RESPONSE = {
  items: [AVAILABLE_NUMBER],
  total_count: 1,
  page: 1,
  page_size: 50,
  total_pages: 1,
};

describe("PhoneNumberSearch", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    searchAvailable.mockResolvedValue(SEARCH_RESPONSE);
  });

  it("submits the search form when Enter is pressed", async () => {
    const user = userEvent.setup();
    render(<PhoneNumberSearch organizationId="org-1" creditBalance={500} />);

    await user.type(screen.getByLabelText(/area code/i), "480");
    const patternInput = screen.getByLabelText(/phone number pattern/i);
    await user.type(patternInput, "480{Enter}");

    await waitFor(() => {
      expect(searchAvailable).toHaveBeenCalledWith({
        organization_id: "org-1",
        country_code: "US",
        phone_number_type: "local",
        area_code: "480",
        contains: "480",
        search_mode: "contains",
        page: 1,
        page_size: 50,
      });
    });
  });

  it("does not offer unsupported mobile inventory in v1", () => {
    render(<PhoneNumberSearch organizationId="org-1" creditBalance={500} />);

    expect(screen.queryByRole("option", { name: "Mobile" })).toBeNull();
  });

  it("sends Begin as the selected prefix match mode", async () => {
    const user = userEvent.setup();
    render(<PhoneNumberSearch organizationId="org-1" creditBalance={500} />);

    const matchSelect = Array.from(document.querySelectorAll("select")).find(
      (select) => select.value === "contains",
    );
    expect(matchSelect).toBeDefined();
    fireEvent.change(matchSelect as HTMLSelectElement, {
      target: { value: "begins_with" },
    });
    expect(screen.getByLabelText(/phone number pattern/i)).toHaveAttribute(
      "maxLength",
      "16",
    );
    await user.type(
      screen.getByLabelText(/phone number pattern/i),
      "480{Enter}",
    );

    await waitFor(() => {
      expect(searchAvailable).toHaveBeenCalledWith(
        expect.objectContaining({
          contains: "480",
          search_mode: "begins_with",
        }),
      );
    });
  });

  it("allows searching without credits and blocks selection of paid numbers", async () => {
    const user = userEvent.setup();
    render(<PhoneNumberSearch organizationId="org-1" creditBalance={100} />);

    const searchButton = screen.getByRole("button", {
      name: /search numbers/i,
    });
    expect((searchButton as HTMLButtonElement).disabled).toBe(false);

    await user.click(searchButton);
    await waitFor(() => expect(searchAvailable).toHaveBeenCalledTimes(1));
    const selectButton = await screen.findByRole("button", { name: "Select" });
    expect((selectButton as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByText(/insufficient credits/i)).toBeTruthy();
  });

  it("uses a readable warning style when a returned number costs too much", async () => {
    const user = userEvent.setup();
    render(<PhoneNumberSearch organizationId="org-1" creditBalance={200} />);

    fireEvent.submit(
      screen.getByRole("form", { name: /available phone number search/i }),
    );

    await waitFor(() => {
      expect(screen.getByText(/insufficient credits/i)).toHaveClass(
        "text-red-900",
      );
    });
  });

  it("shows a search error instead of reporting an empty inventory", async () => {
    const user = userEvent.setup();
    const message =
      "Phone number search is temporarily unavailable. Please try again later.";
    searchAvailable.mockRejectedValueOnce(new Error(message));
    render(<PhoneNumberSearch organizationId="org-1" creditBalance={200} />);

    await user.click(screen.getByRole("button", { name: /search numbers/i }));

    await waitFor(() => expect(searchAvailable).toHaveBeenCalledTimes(1));
    expect(screen.getByRole("alert").textContent).toBe(message);
    expect(screen.queryByText("0 numbers found")).toBeNull();
    expect(screen.queryByText("No available numbers found")).toBeNull();
  });

  it("allows selecting a result that fits the current balance", async () => {
    const user = userEvent.setup();
    const onNumberSelected = vi.fn();
    searchAvailable.mockResolvedValueOnce({
      ...SEARCH_RESPONSE,
      items: [
        AVAILABLE_NUMBER,
        {
          ...AVAILABLE_NUMBER,
          phone_number: "+14805550101",
          monthly_cost_credits: 200,
        },
      ],
    });
    render(
      <PhoneNumberSearch
        organizationId="org-1"
        creditBalance={200}
        onNumberSelected={onNumberSelected}
      />,
    );

    await user.type(
      screen.getByLabelText(/phone number pattern/i),
      "480{Enter}",
    );
    const resultCard = (await screen.findByText("+1 (480) 555-0100")).closest(
      "div.rounded-lg",
    );
    expect(resultCard).toBeTruthy();
    expect(resultCard?.className).toContain("flex-col");
    expect(resultCard?.className).toContain("lg:flex-row");
    const selectButtons = await screen.findAllByRole("button", {
      name: "Select",
    });
    expect(selectButtons[0]).toHaveClass("w-full", "lg:w-auto");
    await user.click(selectButtons[1]);

    expect(onNumberSelected).toHaveBeenCalledWith(
      expect.objectContaining({ phone_number: "+14805550101" }),
    );
  });

  it("formats whole-dollar US rental equivalents without trailing decimals", async () => {
    const user = userEvent.setup();
    searchAvailable.mockResolvedValueOnce({
      ...SEARCH_RESPONSE,
      items: [{ ...AVAILABLE_NUMBER, monthly_cost_credits: 80 }],
    });
    render(<PhoneNumberSearch organizationId="org-1" creditBalance={485} />);

    await user.click(screen.getByRole("button", { name: /search numbers/i }));

    expect(await screen.findByText("80 credits/mo · $2/mo value")).toBeTruthy();
  });

  it("allows a zero-balance organization to choose its included number", async () => {
    const user = userEvent.setup();
    const onNumberSelected = vi.fn();
    searchAvailable.mockResolvedValueOnce({
      ...SEARCH_RESPONSE,
      items: [
        {
          ...AVAILABLE_NUMBER,
          monthly_cost_credits: 0,
          is_included_in_plan: true,
        },
      ],
    });
    render(
      <PhoneNumberSearch
        organizationId="org-1"
        creditBalance={0}
        onNumberSelected={onNumberSelected}
      />,
    );

    await user.click(screen.getByRole("button", { name: /search numbers/i }));
    const selectButton = await screen.findByRole("button", { name: "Select" });

    expect(screen.getByText("Included with plan")).toBeTruthy();
    expect((selectButton as HTMLButtonElement).disabled).toBe(false);
    await user.click(selectButton);
    expect(onNumberSelected).toHaveBeenCalledWith(
      expect.objectContaining({ is_included_in_plan: true }),
    );
  });

  it("lets the available numbers section fill the drawer height", async () => {
    render(
      <PhoneNumberSearch
        organizationId="org-1"
        creditBalance={500}
        className="min-h-full"
      />,
    );

    fireEvent.submit(
      screen.getByRole("form", { name: /available phone number search/i }),
    );

    const availableNumbersCard = (
      await screen.findByText("Available Numbers")
    ).closest('[data-slot="card"]');

    expect(availableNumbersCard).toHaveClass("flex-1", "min-h-0");
    expect(
      availableNumbersCard?.querySelector('[data-slot="card-content"]'),
    ).toHaveClass("flex-1", "min-h-0");
  });
});
