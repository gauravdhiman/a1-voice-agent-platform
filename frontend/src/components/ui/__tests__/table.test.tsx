import { render, screen } from "@testing-library/react";

import { Table } from "../table";

describe("Table wrapper", () => {
  it("allows a parent data-table scroller to own horizontal overflow", () => {
    render(
      <Table wrapperClassName="overflow-visible" aria-label="Test table">
        <tbody>
          <tr>
            <td>Cell</td>
          </tr>
        </tbody>
      </Table>,
    );

    const table = screen.getByRole("table", { name: "Test table" });
    const wrapper = table.parentElement;

    expect(wrapper?.className.includes("overflow-visible")).toBeTruthy();
    expect(wrapper?.className.includes("overflow-auto")).toBeFalsy();
  });
});
