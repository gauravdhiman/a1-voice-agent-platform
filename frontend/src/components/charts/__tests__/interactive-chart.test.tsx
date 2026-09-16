import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
  InteractiveChart,
  weightedIndexAtProgress,
  weightedPositionForIndex,
} from "../interactive-chart";

const points = [
  { label: "Monday", calls: 2 },
  { label: "Tuesday", calls: 5 },
  { label: "Wednesday", calls: 3 },
];

function mountChart() {
  render(
    <InteractiveChart
      data={points}
      chartLabel="Daily calls"
      label={(point) => point.label}
      value={(point) => `${point.calls} calls`}
      className="h-32"
    >
      {({ activeIndex }) => (
        <svg aria-hidden="true" data-active-index={activeIndex ?? "none"} />
      )}
    </InteractiveChart>,
  );

  const chart = screen.getByRole("group", { name: "Daily calls" });
  Object.defineProperty(chart, "getBoundingClientRect", {
    configurable: true,
    value: () => ({
      x: 0,
      y: 0,
      left: 0,
      right: 100,
      top: 0,
      bottom: 128,
      width: 100,
      height: 128,
      toJSON: () => ({}),
    }),
  });
  return chart;
}

describe("InteractiveChart", () => {
  it("updates the tooltip and crosshair as the pointer moves across the plot", () => {
    const chart = mountChart();

    fireEvent.pointerMove(chart, { pointerType: "mouse", clientX: 55 });
    expect(screen.getByRole("tooltip").getAttribute("aria-label")).toBe(
      "Tuesday, 5 calls",
    );
    expect(chart.querySelector("[data-chart-crosshair]")?.getAttribute("style")).toContain(
      "left: 50%",
    );

    fireEvent.pointerMove(chart, { pointerType: "mouse", clientX: 95 });
    expect(screen.getByRole("tooltip").getAttribute("aria-label")).toBe(
      "Wednesday, 3 calls",
    );
  });

  it("supports keyboard browsing and announces the selected point", () => {
    const chart = mountChart();

    fireEvent.focus(chart);
    expect(screen.getByRole("tooltip").getAttribute("aria-live")).toBe("polite");
    expect(screen.getByRole("tooltip").getAttribute("aria-label")).toBe(
      "Monday, 2 calls",
    );

    fireEvent.keyDown(chart, { key: "ArrowRight" });
    expect(screen.getByRole("tooltip").getAttribute("aria-label")).toBe(
      "Tuesday, 5 calls",
    );

    fireEvent.keyDown(chart, { key: "End" });
    expect(screen.getByRole("tooltip").getAttribute("aria-label")).toBe(
      "Wednesday, 3 calls",
    );
  });

  it("keeps a touch selection visible after the finger leaves the plot", () => {
    const chart = mountChart();

    fireEvent.pointerDown(chart, { pointerType: "touch", clientX: 90 });
    fireEvent.pointerLeave(chart, { pointerType: "touch" });

    expect(screen.getByRole("tooltip").getAttribute("aria-label")).toBe(
      "Wednesday, 3 calls",
    );
  });
});

describe("weighted chart scales", () => {
  it("maps pointer positions to the visible weighted segment", () => {
    const weights = [12, 5, 2, 1];

    expect(weightedIndexAtProgress(0.7, weights)).toBe(1);
    expect(weightedIndexAtProgress(0.9, weights)).toBe(2);
    expect(weightedPositionForIndex(0, weights)).toBe(0.3);
    expect(weightedPositionForIndex(1, weights)).toBe(0.725);
  });
});
