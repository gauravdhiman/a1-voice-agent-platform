/**
 * Shared Pipecat WebSocket voice client helpers for browser calls.
 *
 * Used by dashboard test call, embed widget, and public org call pages.
 */

import {
  BROWSER_RECORDER_SAMPLE_RATE,
  LevelMediaManager,
} from "@/lib/level-media-manager";
import { PipecatClient, RTVIEvent } from "@pipecat-ai/client-js";
import { WebSocketTransport } from "@pipecat-ai/websocket-transport";

export interface PipecatSpeakingState {
  isAgentSpeaking: boolean;
  isUserSpeaking: boolean;
}

export interface PipecatCallCallbacks {
  onConnected?: () => void;
  onDisconnected?: () => void;
  onError?: (error: Error) => void;
  onSpeakingChange?: (state: PipecatSpeakingState) => void;
  /** Fired when the bot's remote audio track becomes available (or is lost). */
  onBotAudioTrack?: (track: MediaStreamTrack | null) => void;
  /** Fired when the local microphone track becomes available (or is lost). */
  onLocalAudioTrack?: (track: MediaStreamTrack | null) => void;
  /**
   * Provides the app-level LevelMediaManager used by the transport so the UI
   * can read real bot audio levels for visualisation.
   */
  onLevelManager?: (manager: LevelMediaManager) => void;
}
/** Turn Pipecat callback payloads into a readable Error for UI display. */
export function normalizeVoiceClientError(err: unknown): Error {
  if (err instanceof Error && typeof err.message === "string" && err.message) {
    return err;
  }
  if (typeof err === "string" && err.trim()) {
    return new Error(err);
  }
  if (err && typeof err === "object") {
    const record = err as Record<string, unknown>;
    if (typeof record.message === "string" && record.message.trim()) {
      return new Error(record.message);
    }
    if (typeof record.error === "string" && record.error.trim()) {
      return new Error(record.error);
    }
    if (record.error && typeof record.error === "object") {
      const nested = record.error as Record<string, unknown>;
      if (typeof nested.message === "string" && nested.message.trim()) {
        return new Error(nested.message);
      }
    }
    try {
      return new Error(JSON.stringify(err));
    } catch {
      /* fall through */
    }
  }
  return new Error("Voice connection error");
}

/**
 * Build a WebSocket URL with the session JWT appended as a query parameter.
 */
export function buildPipecatWebSocketUrl(wsUrl: string, token: string): string {
  const url = new URL(wsUrl.replace(/^ws/i, "http"));
  url.searchParams.set("token", token);
  return url.toString().replace(/^http/i, "ws");
}

/**
 * Connect a Pipecat client to voice-ws and return the client for lifecycle control.
 */
export async function connectPipecatVoiceCall(
  token: string,
  wsUrl: string,
  callbacks: PipecatCallCallbacks = {},
): Promise<PipecatClient> {
  const levelManager = new LevelMediaManager();
  callbacks.onLevelManager?.(levelManager);
  const transport = new WebSocketTransport({
    mediaManager: levelManager,
    recorderSampleRate: BROWSER_RECORDER_SAMPLE_RATE,
  });
  const client = new PipecatClient({
    transport,
    enableMic: true,
    enableCam: false,
    callbacks: {
      onConnected: () => callbacks.onConnected?.(),
      onDisconnected: () => callbacks.onDisconnected?.(),
      onError: (err) => {
        callbacks.onError?.(normalizeVoiceClientError(err));
      },
    },
  });

  client.on(RTVIEvent.BotStartedSpeaking, () => {
    callbacks.onSpeakingChange?.({ isAgentSpeaking: true, isUserSpeaking: false });
  });
  client.on(RTVIEvent.BotStoppedSpeaking, () => {
    callbacks.onSpeakingChange?.({ isAgentSpeaking: false, isUserSpeaking: false });
  });
  client.on(RTVIEvent.UserStartedSpeaking, () => {
    callbacks.onSpeakingChange?.({ isAgentSpeaking: false, isUserSpeaking: true });
  });
  client.on(RTVIEvent.UserStoppedSpeaking, () => {
    callbacks.onSpeakingChange?.({ isAgentSpeaking: false, isUserSpeaking: false });
  });

  await client.connect({ ws_url: buildPipecatWebSocketUrl(wsUrl, token) });

  // Expose live audio tracks for visualization once the transport has them.
  const emitTracks = () => {
    try {
      const tracks = client.tracks();
      callbacks.onBotAudioTrack?.(tracks.bot?.audio ?? null);
      callbacks.onLocalAudioTrack?.(tracks.local.audio ?? null);
    } catch {
      /* transport not ready */
    }
  };
  emitTracks();
  client.on(RTVIEvent.TrackStarted, emitTracks);
  client.on(RTVIEvent.TrackStopped, emitTracks);

  return client;
}

/**
 * Disconnect a Pipecat client without throwing on teardown errors.
 */
export async function disconnectPipecatVoiceCall(
  client: PipecatClient | null,
): Promise<void> {
  if (!client) return;
  try {
    await client.disconnect();
  } catch {
    /* ignore teardown errors */
  }
}
