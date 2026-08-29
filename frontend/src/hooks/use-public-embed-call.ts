import { useCallback, useRef, useState } from "react";
import type { PipecatClient } from "@pipecat-ai/client-js";
import {
  connectPipecatVoiceCall,
  disconnectPipecatVoiceCall,
} from "@/lib/pipecat-voice-client";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface EmbedCallState {
  token: string | null;
  wsUrl: string | null;
  sessionId: string | null;
  isMuted: boolean;
  isAgentSpeaking: boolean;
  isUserSpeaking: boolean;
}

/**
 * Hook for public embed widget calls over Pipecat WebSocket transport.
 */
export function usePublicEmbedCall(agentId: string | null) {
  const [state, setState] = useState<EmbedCallState>({
    token: null,
    wsUrl: null,
    sessionId: null,
    isMuted: false,
    isAgentSpeaking: false,
    isUserSpeaking: false,
  });

  const pipecatRef = useRef<PipecatClient | null>(null);
  const connectionAttemptRef = useRef(0);

  const connect = useCallback(async () => {
    if (!agentId) {
      throw new Error("No agent ID provided");
    }

    const attempt = ++connectionAttemptRef.current;
    const isCurrentAttempt = () => connectionAttemptRef.current === attempt;

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/embed/agent/${agentId}/token`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
        },
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Failed to get embed token");
      }
      if (!isCurrentAttempt()) return { success: false };

      const data = await response.json();
      const { token, wsUrl, sessionId } = data;

      if (!token || !wsUrl || !sessionId) {
        throw new Error("Invalid token response");
      }
      if (!isCurrentAttempt()) return { success: false };

      const client = await connectPipecatVoiceCall(token, wsUrl, {
        onClientCreated: (createdClient) => {
          if (isCurrentAttempt()) {
            pipecatRef.current = createdClient;
          } else {
            void disconnectPipecatVoiceCall(createdClient);
          }
        },
        onSpeakingChange: ({ isAgentSpeaking, isUserSpeaking }) => {
          if (!isCurrentAttempt()) return;
          setState((prev) => ({
            ...prev,
            isAgentSpeaking,
            isUserSpeaking,
          }));
        },
      });

      if (!isCurrentAttempt()) return { success: false };
      pipecatRef.current = client;

      setState({
        token,
        wsUrl,
        sessionId,
        isMuted: false,
        isAgentSpeaking: false,
        isUserSpeaking: false,
      });

      return { success: true };
    } catch (error) {
      if (!isCurrentAttempt()) return { success: false };
      console.error("Embed call connection error:", error);
      throw error;
    }
  }, [agentId]);

  const disconnect = useCallback(() => {
    connectionAttemptRef.current += 1;
    const client = pipecatRef.current;
    pipecatRef.current = null;
    void disconnectPipecatVoiceCall(client);

    setState({
      token: null,
      wsUrl: null,
      sessionId: null,
      isMuted: false,
      isAgentSpeaking: false,
      isUserSpeaking: false,
    });
  }, []);

  const toggleMute = useCallback(() => {
    if (!pipecatRef.current) {
      console.error("No Pipecat client connected");
      return;
    }

    setState((prev) => {
      const nextMuted = !prev.isMuted;
      pipecatRef.current?.enableMic(!nextMuted);
      return { ...prev, isMuted: nextMuted };
    });
  }, []);

  return {
    ...state,
    connect,
    disconnect,
    toggleMute,
  };
}
