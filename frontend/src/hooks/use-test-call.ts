"use client";

import { useCallback, useRef, useState } from "react";
import type { PipecatClient } from "@pipecat-ai/client-js";
import {
  connectPipecatVoiceCall,
  disconnectPipecatVoiceCall,
} from "@/lib/pipecat-voice-client";

/**
 * Browser test-call hook using Pipecat WebSocket transport.
 */

export interface TestCallState {
  isConnecting: boolean;
  isConnected: boolean;
  error: string | null;
  isAgentSpeaking: boolean;
  isUserSpeaking: boolean;
}

export interface UseTestCallOptions {
  agentId: string;
  onConnected?: () => void;
  onDisconnected?: () => void;
  onError?: (error: Error) => void;
}

export interface UseTestCallResult extends TestCallState {
  startCall: () => Promise<void>;
  endCall: () => void;
  toggleMute: () => void;
  isMuted: boolean;
}

export function useTestCall({
  agentId,
  onConnected,
  onDisconnected,
  onError,
}: UseTestCallOptions): UseTestCallResult {
  const [state, setState] = useState<TestCallState>({
    isConnecting: false,
    isConnected: false,
    error: null,
    isAgentSpeaking: false,
    isUserSpeaking: false,
  });

  const [isMuted, setIsMuted] = useState(false);

  const pipecatRef = useRef<PipecatClient | null>(null);
  const connectionAttemptRef = useRef(0);

  const resetCallState = useCallback(() => {
    setIsMuted(false);
    setState({
      isConnecting: false,
      isConnected: false,
      error: null,
      isAgentSpeaking: false,
      isUserSpeaking: false,
    });
  }, []);

  const endCall = useCallback(() => {
    // Invalidate an in-flight connection before clearing the client. The
    // connection helper can finish after the user hangs up.
    connectionAttemptRef.current += 1;
    // Clear the ref before disconnecting. Pipecat can synchronously emit
    // onDisconnected during disconnect(), and the callback must not attempt
    // to send a second close message on an already-closed socket.
    const client = pipecatRef.current;
    pipecatRef.current = null;
    if (client) {
      void disconnectPipecatVoiceCall(client);
    }

    resetCallState();
    if (client) onDisconnected?.();
  }, [onDisconnected, resetCallState]);

  const handleTransportDisconnected = useCallback(() => {
    // A server/network close has already completed transport teardown. Do not
    // call client.disconnect() again; just release the client and update UI.
    const client = pipecatRef.current;
    pipecatRef.current = null;
    if (!client) return;

    resetCallState();
    onDisconnected?.();
  }, [onDisconnected, resetCallState]);

  const toggleMute = useCallback(() => {
    if (!pipecatRef.current) return;
    const next = !isMuted;
    pipecatRef.current.enableMic(!next);
    setIsMuted(next);
  }, [isMuted]);

  const startCall = useCallback(async () => {
    if (state.isConnecting || state.isConnected) {
      return;
    }

    setState((prev) => ({
      ...prev,
      isConnecting: true,
      error: null,
    }));
    const attempt = ++connectionAttemptRef.current;
    const isCurrentAttempt = () => connectionAttemptRef.current === attempt;

    try {
      const { agentService } = await import("@/services/agent-service");
      const bootstrap = await agentService.getTestToken(agentId);

      if (!bootstrap.token || !bootstrap.wsUrl) {
        throw new Error("Failed to get Pipecat voice session");
      }
      if (!isCurrentAttempt()) return;

      const client = await connectPipecatVoiceCall(
        bootstrap.token,
        bootstrap.wsUrl,
        {
          onClientCreated: (client) => {
            if (isCurrentAttempt()) {
              // Keep the client reachable while connect() is still awaiting
              // the transport handshake so Hang Up can close the socket.
              pipecatRef.current = client;
            } else {
              void disconnectPipecatVoiceCall(client);
            }
          },
          onConnected: () => {
            if (!isCurrentAttempt()) return;
            setState((prev) => ({
              ...prev,
              isConnecting: false,
              isConnected: true,
            }));
            onConnected?.();
          },
          onDisconnected: () => {
            if (!isCurrentAttempt()) return;
            handleTransportDisconnected();
          },
          onError: (error) => {
            if (!isCurrentAttempt()) return;
            setState((prev) => ({
              ...prev,
              isConnecting: false,
              error: error.message,
            }));
            onError?.(error);
          },
          onSpeakingChange: ({ isAgentSpeaking, isUserSpeaking }) => {
            if (!isCurrentAttempt()) return;
            setState((prev) => ({
              ...prev,
              isAgentSpeaking,
              isUserSpeaking,
            }));
          },
        },
      );

      if (!isCurrentAttempt()) return;
      pipecatRef.current = client;
    } catch (err) {
      if (!isCurrentAttempt()) return;
      const error =
        err instanceof Error ? err : new Error("Failed to start test call");
      console.error("Test call error:", error);

      setState((prev) => ({
        ...prev,
        isConnecting: false,
        error: error.message,
      }));

      onError?.(error);
      endCall();
    }
  }, [
    agentId,
    state.isConnecting,
    state.isConnected,
    endCall,
    handleTransportDisconnected,
    onConnected,
    onError,
  ]);

  return {
    ...state,
    startCall,
    endCall,
    toggleMute,
    isMuted,
  };
}
