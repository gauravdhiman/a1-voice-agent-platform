/**
 * Shared Pipecat WebSocket voice client helpers for browser calls.
 *
 * Used by dashboard test call, embed widget, and public org call pages.
 */

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
  const client = new PipecatClient({
    transport: new WebSocketTransport(),
    enableMic: true,
    enableCam: false,
    callbacks: {
      onConnected: () => callbacks.onConnected?.(),
      onDisconnected: () => callbacks.onDisconnected?.(),
      onError: (err) => {
        const error =
          err instanceof Error ? err : new Error(String(err ?? "Voice error"));
        callbacks.onError?.(error);
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
