/**
 * LevelMediaManager — app-side extension of the Pipecat WebSocket transport's
 * WavMediaManager (dependency-injected via `mediaManager`, a documented option;
 * no library code is modified).
 *
 * Overrides bufferBotAudio() to tap the bot's outgoing PCM into an in-app
 * AnalyserNode so the UI can visualise the agent's real audio levels while
 * playback continues unchanged through the parent implementation.
 */

import {
  WavMediaManager,
} from "@pipecat-ai/websocket-transport";

export interface AudioLevels {
  /** Overall RMS 0..1 */
  level: number;
  bass: number;
  mid: number;
  treble: number;
}

export class LevelMediaManager extends WavMediaManager {
  private analyser: AnalyserNode | null = null;
  private audioCtx: AudioContext | null = null;
  private freqData: Uint8Array<ArrayBuffer> | null = null;

  /** Latest levels, read by the rAF loop in the visualiser. */
  readonly levels: AudioLevels = { level: 0, bass: 0, mid: 0, treble: 0 };

  bufferBotAudio(data: ArrayBuffer | Int16Array, id: string): Int16Array {
    // Feed our analyser first (non-blocking), then let the lib play normally.
    try {
      this.ensureAnalyser();
      if (this.analyser && this.audioCtx && this.freqData) {
        const samples =
          data instanceof Int16Array ? data : new Int16Array(data.slice(0));
        const float = new Float32Array(samples.length);
        for (let i = 0; i < samples.length; i++) {
          float[i] = samples[i] / 32768;
        }
        const buf = this.audioCtx.createBuffer(1, float.length, this.audioCtx.sampleRate);
        buf.copyToChannel(float, 0);
        // ScriptProcessor-free path: use an AudioBufferSource → analyser
        const src = this.audioCtx.createBufferSource();
        src.buffer = buf;
        src.connect(this.analyser);
        src.start();
      }
    } catch {
      /* analysis is best-effort; never break playback */
    }
    return super.bufferBotAudio(data, id) as Int16Array;
  }

  private ensureAnalyser() {
    if (!this.audioCtx) {
      const AC =
        window.AudioContext ??
        (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
      if (!AC) return;
      this.audioCtx = new AC();
    }
    if (this.analyser) return;
    if (this.audioCtx.state === "suspended") void this.audioCtx.resume();
    this.analyser = this.audioCtx.createAnalyser();
    this.analyser.fftSize = 1024;
    this.analyser.smoothingTimeConstant = 0.8;
    this.freqData = new Uint8Array(new ArrayBuffer(this.analyser.frequencyBinCount));
  }

  /** Called by the visualiser each frame to refresh level values. */
  readLevels(): AudioLevels {
    if (!this.analyser || !this.freqData) return this.levels;
    this.analyser.getByteFrequencyData(this.freqData);
    const binHz = (this.audioCtx?.sampleRate ?? 24000) / this.analyser.fftSize;
    const bandAvg = (from: number, to: number): number => {
      let sum = 0;
      for (let i = from; i < to; i++) sum += this.freqData![i];
      return sum / ((to - from) * 255);
    };
    const lo = Math.max(1, Math.floor(80 / binHz));
    const midSplit = Math.floor(2000 / binHz);
    const hiEnd = Math.min(this.freqData.length, Math.floor(6000 / binHz));
    const bass = bandAvg(lo, Math.max(lo + 1, midSplit));
    const mid = bandAvg(Math.max(lo + 1, midSplit), hiEnd);
    const treble = bandAvg(hiEnd, this.freqData.length);
    this.levels.level = Math.min(1, bass * 0.5 + mid * 0.35 + treble * 0.15);
    this.levels.bass = bass;
    this.levels.mid = mid;
    this.levels.treble = treble;
    return this.levels;
  }
}
