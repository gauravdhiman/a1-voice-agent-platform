/**
 * Public demo visualizer choices.
 *
 * The demo intentionally exposes only the two finalized visualizations. Any
 * missing or obsolete A/B-test value falls back to the radial experience.
 */
export type DemoVisualizer = "radial" | "lk-bars";

/**
 * Resolves a public demo query value to one of the supported visualizers.
 *
 * @param value - Optional `visualizer` query parameter.
 * @returns The selected final visualizer, defaulting to radial.
 */
export function resolveDemoVisualizer(value: string | null | undefined): DemoVisualizer {
  return value === "lk-bars" ? "lk-bars" : "radial";
}
