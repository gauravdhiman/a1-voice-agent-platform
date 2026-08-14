import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const mockSetTheme = vi.fn();
vi.mock("@/contexts/theme-context", () => ({
  useTheme: () => ({ theme: "system", setTheme: mockSetTheme }),
}));

import SettingsPage from "../page";

describe("SettingsPage", () => {
  it("does not duplicate the walkthrough entry point", () => {
    render(<SettingsPage />);

    expect(screen.queryByText("Guided walkthrough")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /restart walkthrough/i }),
    ).not.toBeInTheDocument();
  });
});
