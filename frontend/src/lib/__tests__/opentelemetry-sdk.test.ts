import { trace } from "@opentelemetry/api";
import { afterEach, expect, it, vi } from "vitest";

const exports = vi.hoisted(() => ({ traces: vi.fn(), logs: vi.fn() }));

class TestExporter {
  export(_items: unknown, done: (result: { code: number }) => void) { done({ code: 0 }); }
  shutdown() { return Promise.resolve(); }
  forceFlush() { return Promise.resolve(); }
  selectAggregationTemporality() { return 1; }
}

vi.mock("@opentelemetry/exporter-trace-otlp-http", () => ({ OTLPTraceExporter: class extends TestExporter {
  export(items: unknown, done: (result: { code: number }) => void) { exports.traces(items); super.export(items, done); }
} }));
vi.mock("@opentelemetry/exporter-logs-otlp-http", () => ({ OTLPLogExporter: class extends TestExporter {
  export(items: unknown, done: (result: { code: number }) => void) { exports.logs(items); super.export(items, done); }
} }));
vi.mock("@opentelemetry/exporter-metrics-otlp-http", () => ({ OTLPMetricExporter: TestExporter }));

afterEach(() => { trace.disable(); vi.unstubAllEnvs(); vi.useRealTimers(); });

it("initializes real SDK 2 providers and exports traces and logs through constructor processors", async () => {
  vi.useFakeTimers();
  vi.stubEnv("NEXT_PUBLIC_OTEL_ENABLED", "true");
  const sdk = await import("../opentelemetry");
  sdk.initOpenTelemetry();
  try {
    expect(sdk.tracerProvider).toBeTruthy();
    expect(sdk.loggerProvider).toBeTruthy();
    expect(sdk.meterProvider).toBeTruthy();
    sdk.getTracer("readiness")?.startSpan("readiness.test").end();
    sdk.getLogger("readiness")?.emit({ body: "readiness.test" });
    await sdk.tracerProvider?.forceFlush();
    await sdk.loggerProvider?.forceFlush();
    expect(exports.traces).toHaveBeenCalled();
    expect(exports.logs).toHaveBeenCalled();
  } finally {
    await Promise.all([sdk.tracerProvider?.shutdown(), sdk.loggerProvider?.shutdown(), sdk.meterProvider?.shutdown()]);
    vi.clearAllTimers();
  }
});
