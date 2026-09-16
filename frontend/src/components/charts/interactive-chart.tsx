"use client";

import {
  useId,
  useRef,
  useState,
  type KeyboardEvent,
  type PointerEvent,
  type ReactNode,
} from "react";
import { cn } from "@/lib/utils";

/** The selected data point exposed to a chart's visual marks. */
export interface InteractiveChartSelection<T> {
  activeIndex: number | null;
  activeItem: T | null;
  activePosition: number | null;
}

/** Shared interaction contract for data-driven charts. */
export interface InteractiveChartProps<T> {
  data: readonly T[];
  chartLabel: string;
  label: (item: T) => string;
  value: (item: T) => string;
  className?: string;
  getIndexForProgress?: (progress: number, data: readonly T[]) => number;
  getPositionForIndex?: (index: number, data: readonly T[]) => number;
  children: (selection: InteractiveChartSelection<T>) => ReactNode;
}

/** Select a weighted segment from a normalized horizontal pointer position. */
export function weightedIndexAtProgress(
  progress: number,
  weights: readonly number[],
): number {
  if (weights.length === 0) return -1;

  const safeWeights = weights.map((weight) =>
    Number.isFinite(weight) ? Math.max(weight, 0) : 0,
  );
  const total = safeWeights.reduce((sum, weight) => sum + weight, 0);
  const normalizedProgress = Math.min(1, Math.max(0, progress));

  if (total === 0) {
    return Math.min(
      weights.length - 1,
      Math.floor(normalizedProgress * weights.length),
    );
  }

  const target = normalizedProgress * total;
  let cumulative = 0;
  for (let index = 0; index < safeWeights.length; index += 1) {
    cumulative += safeWeights[index];
    if (target < cumulative || index === safeWeights.length - 1) {
      return index;
    }
  }

  return safeWeights.length - 1;
}

/** Return the center of a weighted segment as a normalized chart position. */
export function weightedPositionForIndex(
  index: number,
  weights: readonly number[],
): number {
  if (weights.length === 0) return 0.5;

  const safeWeights = weights.map((weight) =>
    Number.isFinite(weight) ? Math.max(weight, 0) : 0,
  );
  const total = safeWeights.reduce((sum, weight) => sum + weight, 0);
  const safeIndex = Math.min(weights.length - 1, Math.max(0, Math.trunc(index)));

  if (total === 0) return (safeIndex + 0.5) / weights.length;

  const before = safeWeights
    .slice(0, safeIndex)
    .reduce((sum, weight) => sum + weight, 0);
  return (before + safeWeights[safeIndex] / 2) / total;
}

/** Select an equal-width bar from a normalized horizontal pointer position. */
export function uniformBandIndexAtProgress(
  progress: number,
  count: number,
): number {
  if (count <= 0) return -1;
  const normalizedProgress = Math.min(1, Math.max(0, progress));
  return Math.min(count - 1, Math.floor(normalizedProgress * count));
}

/** Return the center of an equal-width bar as a normalized chart position. */
export function uniformBandPositionForIndex(
  index: number,
  count: number,
): number {
  if (count <= 0) return 0.5;
  const safeIndex = Math.min(count - 1, Math.max(0, Math.trunc(index)));
  return (safeIndex + 0.5) / count;
}

/**
 * Add a shared crosshair, immediate readout, and pointer/keyboard/touch selection
 * to a chart. Data points are mapped across the plot unless a chart supplies a
 * custom scale for bars or weighted segments.
 */
export function InteractiveChart<T>({
  data,
  chartLabel,
  label,
  value,
  className,
  getIndexForProgress,
  getPositionForIndex,
  children,
}: InteractiveChartProps<T>) {
  const plotRef = useRef<HTMLDivElement>(null);
  const tooltipId = useId();
  const [storedIndex, setStoredIndex] = useState<number | null>(null);
  const [interactionSource, setInteractionSource] = useState<
    "pointer" | "keyboard"
  >("pointer");
  const activeIndex =
    storedIndex !== null && storedIndex < data.length ? storedIndex : null;
  const activeItem = activeIndex === null ? null : data[activeIndex] ?? null;

  const positionForIndex = (index: number): number => {
    const fallback = data.length === 1 ? 0.5 : index / (data.length - 1);
    const position = getPositionForIndex?.(index, data) ?? fallback;
    return Number.isFinite(position) ? Math.min(1, Math.max(0, position)) : fallback;
  };

  const indexForProgress = (progress: number): number => {
    if (getIndexForProgress) {
      const selected = getIndexForProgress(progress, data);
      return Math.min(data.length - 1, Math.max(0, Math.trunc(selected)));
    }

    let selectedIndex = 0;
    let nearestDistance = Number.POSITIVE_INFINITY;
    data.forEach((_, index) => {
      const distance = Math.abs(positionForIndex(index) - progress);
      if (distance < nearestDistance) {
        selectedIndex = index;
        nearestDistance = distance;
      }
    });
    return selectedIndex;
  };

  const selectFromPointer = (clientX: number) => {
    const bounds = plotRef.current?.getBoundingClientRect();
    if (!bounds || bounds.width <= 0 || data.length === 0) return;

    const progress = Math.min(
      1,
      Math.max(0, (clientX - bounds.left) / bounds.width),
    );
    setInteractionSource("pointer");
    setStoredIndex(indexForProgress(progress));
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (data.length === 0) return;
    if (!(["ArrowLeft", "ArrowRight", "Home", "End"] as string[]).includes(event.key)) {
      return;
    }

    event.preventDefault();
    setInteractionSource("keyboard");
    setStoredIndex((current) => {
      const index = current ?? 0;
      if (event.key === "Home") return 0;
      if (event.key === "End") return data.length - 1;
      if (event.key === "ArrowLeft") return Math.max(0, index - 1);
      return Math.min(data.length - 1, index + 1);
    });
  };

  const activePosition =
    activeIndex === null ? null : positionForIndex(activeIndex);

  return (
    <div
      ref={plotRef}
      role="group"
      aria-label={chartLabel}
      aria-describedby={activeItem ? tooltipId : undefined}
      tabIndex={data.length > 0 ? 0 : -1}
      className={cn(
        "relative w-full cursor-crosshair focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        className,
      )}
      onPointerMove={(event: PointerEvent<HTMLDivElement>) =>
        selectFromPointer(event.clientX)
      }
      onPointerDown={(event: PointerEvent<HTMLDivElement>) => {
        if (event.pointerType === "touch") selectFromPointer(event.clientX);
      }}
      onPointerLeave={(event: PointerEvent<HTMLDivElement>) => {
        if (event.pointerType !== "touch") setStoredIndex(null);
      }}
      onFocus={() => {
        if (activeIndex === null && data.length > 0) {
          setInteractionSource("keyboard");
          setStoredIndex(0);
        }
      }}
      onBlur={() => setStoredIndex(null)}
      onKeyDown={handleKeyDown}
    >
      {children({ activeIndex, activeItem, activePosition })}
      {activePosition !== null && (
        <span
          aria-hidden="true"
          data-chart-crosshair
          className="pointer-events-none absolute inset-y-0 z-10 border-l border-dashed border-primary/60"
          style={{ left: `${activePosition * 100}%` }}
        />
      )}
      {activeItem && activePosition !== null && (
        <div
          id={tooltipId}
          role="tooltip"
          aria-label={`${label(activeItem)}, ${value(activeItem)}`}
          aria-live={interactionSource === "keyboard" ? "polite" : "off"}
          aria-atomic="true"
          className="pointer-events-none absolute top-1 z-20 flex -translate-x-1/2 flex-col whitespace-nowrap rounded-md border bg-popover/95 px-3 py-2 text-xs shadow-md backdrop-blur"
          style={{
            left: `clamp(5.5rem, ${activePosition * 100}%, calc(100% - 5.5rem))`,
          }}
        >
          <span className="text-muted-foreground">{label(activeItem)}</span>
          <span className="mt-0.5 font-semibold tabular-nums">
            {value(activeItem)}
          </span>
        </div>
      )}
    </div>
  );
}
