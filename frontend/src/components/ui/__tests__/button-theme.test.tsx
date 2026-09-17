import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Button } from "../button";
import { Select, SelectTrigger, SelectValue } from "../select";

describe("shared control theme classes", () => {
  it("keeps outline buttons on the neutral input border token", () => {
    render(
      <Button variant="outline" aria-label="Neutral action">
        Neutral action
      </Button>,
    );

    const button = screen.getByRole("button", { name: "Neutral action" });
    expect(button.className).toContain("border-input");
    expect(button.className).not.toContain("aria-invalid:border-destructive");
  });

  it("uses the invalid border only through an active aria state", () => {
    render(
      <Button variant="outline" aria-invalid="true">
        Invalid action
      </Button>,
    );

    const button = screen.getByRole("button", { name: "Invalid action" });
    expect(button.className).toContain(
      "aria-[invalid=true]:border-[color:var(--destructive)]",
    );
  });

  it("keeps select triggers on the same neutral border token", () => {
    render(
      <Select>
        <SelectTrigger aria-label="Theme">
          <SelectValue placeholder="Theme" />
        </SelectTrigger>
      </Select>,
    );

    const trigger = screen.getByRole("combobox", { name: "Theme" });
    expect(trigger.className).toContain("border-input");
    expect(trigger.className).not.toContain("aria-invalid:border-destructive");
  });
});
