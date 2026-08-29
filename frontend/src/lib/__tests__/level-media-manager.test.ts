import { describe, expect, it } from "vitest";
import {
  BROWSER_RECORDER_CHUNK_BYTES,
  BROWSER_RECORDER_SAMPLE_RATE,
  LevelMediaManager,
} from "@/lib/level-media-manager";

describe("LevelMediaManager", () => {
  it("uses the browser WebSocket recorder contract", () => {
    const manager = new LevelMediaManager();
    const internals = manager as unknown as {
      _recorderChunkSize: number;
      _wavRecorder: { sampleRate: number };
    };

    expect(internals._recorderChunkSize).toBe(BROWSER_RECORDER_CHUNK_BYTES);
    expect(internals._wavRecorder.sampleRate).toBe(
      BROWSER_RECORDER_SAMPLE_RATE,
    );
  });
});
