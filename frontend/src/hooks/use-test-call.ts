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

  const endCall = useCallback(() => {
    void disconnectPipecatVoiceCall(pipecatRef.current);
    pipecatRef.current = null;

    setIsMuted(false);

    setState({
      isConnecting: false,
      isConnected: false,
      error: null,
      isAgentSpeaking: false,
      isUserSpeaking: false,
    });

    onDisconnected?.();
  }, [onDisconnected]);

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

    try {
      const { agentService } = await import("@/services/agent-service");
      const bootstrap = await agentService.getTestToken(agentId);

      if (!bootstrap.token || !bootstrap.wsUrl) {
        throw new Error("Failed to get Pipecat voice session");
      }

      const client = await connectPipecatVoiceCall(
        bootstrap.token,
        bootstrap.wsUrl,
        {
          onConnected: () => {
            setState((prev) => ({
              ...prev,
              isConnecting: false,
              isConnected: true,
            }));
            onConnected?.();
          },
          onDisconnected: () => {
            endCall();
          },
          onError: (error) => {
            setState((prev) => ({
              ...prev,
              isConnecting: false,
              error: error.message,
            }));
            onError?.(error);
          },
          onSpeakingChange: ({ isAgentSpeaking, isUserSpeaking }) => {
            setState((prev) => ({
              ...prev,
              isAgentSpeaking,
              isUserSpeaking,
            }));
          },
        },
      );

      pipecatRef.current = client;
    } catch (err) {
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
