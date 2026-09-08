import { useState } from "react";

import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { TagInput } from "../tag-input";

function TagInputHarness({ delimiters }: { delimiters?: readonly string[] }) {
  const [tags, setTags] = useState<string[]>([]);

  return (
    <TagInput
      aria-label="Tags"
      value={tags}
      onChange={setTags}
      delimiters={delimiters}
      placeholder="Add a tag"
    />
  );
}

describe("TagInput", () => {
  it("turns comma and space delimiters into removable pills", async () => {
    const user = userEvent.setup();
    render(<TagInputHarness />);

    const input = screen.getByRole("textbox", { name: "Tags" });
    await user.type(input, "example.com ");
    await user.type(input, "www.example.com,");

    expect(screen.getByText("example.com")).toBeTruthy();
    expect(screen.getByText("www.example.com")).toBeTruthy();

    await user.click(screen.getByRole("button", { name: "Remove example.com" }));

    expect(screen.queryByText("example.com")).toBeNull();
    expect(screen.getByText("www.example.com")).toBeTruthy();
  });

  it("supports custom delimiters, paste-style input, Enter, and Backspace", async () => {
    const user = userEvent.setup();
    render(<TagInputHarness delimiters={[";"]} />);

    const input = screen.getByRole("textbox", { name: "Tags" });
    fireEvent.change(input, { target: { value: "one;two;" } });
    expect(screen.getByText("one")).toBeTruthy();
    expect(screen.getByText("two")).toBeTruthy();

    await user.type(input, "three");
    await user.keyboard("{Enter}");
    expect(screen.getByText("three")).toBeTruthy();

    await user.keyboard("{Backspace}");
    expect(screen.queryByText("three")).toBeNull();
  });
});
