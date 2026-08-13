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
    render(<PhoneNumberSearch creditBalance={500} />);

    await user.type(screen.getByLabelText(/area code/i), "480");
    const patternInput = screen.getByLabelText(/phone number pattern/i);
    await user.type(patternInput, "480{Enter}");

    await waitFor(() => {
      expect(searchAvailable).toHaveBeenCalledWith({
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

  it("sends Begin as the selected prefix match mode", async () => {
    const user = userEvent.setup();
    render(<PhoneNumberSearch creditBalance={500} />);

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
    await user.type(screen.getByLabelText(/phone number pattern/i), "480{Enter}");

    await waitFor(() => {
      expect(searchAvailable).toHaveBeenCalledWith(
        expect.objectContaining({ contains: "480", search_mode: "begins_with" }),
      );
    });
  });

  it("disables search and explains the minimum credit requirement", async () => {
    const user = userEvent.setup();
    render(<PhoneNumberSearch creditBalance={100} />);

    const searchButton = screen.getByRole("button", { name: /search numbers/i });
    expect(searchButton).toBeDisabled();
    expect(screen.getByRole("alert")).toHaveTextContent(
      /search is unavailable.*minimum of 200 credits/i,
    );

    await user.type(screen.getByLabelText(/phone number pattern/i), "480{Enter}");
    expect(searchAvailable).not.toHaveBeenCalled();
  });

  it("uses a readable warning style when a returned number costs too much", async () => {
    const user = userEvent.setup();
    render(<PhoneNumberSearch creditBalance={200} />);

    fireEvent.submit(
      screen.getByRole("form", { name: /available phone number search/i }),
    );

    await waitFor(() => {
      expect(screen.getByText(/insufficient credits/i)).toHaveClass("text-red-900");
    });
  });

  it("shows a toast when the provider search fails", async () => {
    const user = userEvent.setup();
    searchAvailable.mockRejectedValueOnce(new Error("provider unavailable"));
    render(<PhoneNumberSearch creditBalance={200} />);

    await user.type(screen.getByLabelText(/phone number pattern/i), "480{Enter}");

    await waitFor(() => expect(searchAvailable).toHaveBeenCalledTimes(1));
  });

  it("allows selecting a result that fits the current balance", async () => {
    const user = userEvent.setup();
    const onNumberSelected = vi.fn();
    searchAvailable.mockResolvedValueOnce({
      ...SEARCH_RESPONSE,
      items: [
        AVAILABLE_NUMBER,
        { ...AVAILABLE_NUMBER, phone_number: "+14805550101", monthly_cost_credits: 200 },
      ],
    });
    render(
      <PhoneNumberSearch
        creditBalance={200}
        onNumberSelected={onNumberSelected}
      />,
    );

    await user.type(screen.getByLabelText(/phone number pattern/i), "480{Enter}");
    const selectButtons = await screen.findAllByRole("button", { name: "Select" });
    await user.click(selectButtons[1]);

    expect(onNumberSelected).toHaveBeenCalledWith(
      expect.objectContaining({ phone_number: "+14805550101" }),
    );
  });
});
