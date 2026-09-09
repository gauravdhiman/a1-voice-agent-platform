"use client";

import { Suspense, useEffect, useState, useRef, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import { Mic, MicOff, PhoneOff, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { AgentAudioVisualizerWave } from "@/components/agents-ui/agent-audio-visualizer-wave";
import type { PipecatClient } from "@pipecat-ai/client-js";
import {
  connectPipecatVoiceCall,
  disconnectPipecatVoiceCall,
} from "@/lib/pipecat-voice-client";
import { getCurrentPageSourceUrl } from "@/lib/source-url";
import { getPublicVoiceCallErrorMessage } from "@/lib/voice-call-messages";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface EmbedCallCredentials {
  token: string;
  wsUrl: string;
  sessionId: string;
}

function getEmbeddingPageOrigin(): string | null {
  if (!document.referrer) return null;

  try {
    return new URL(document.referrer).origin;
  } catch {
    return null;
  }
}

function EmbedCallContent() {
  const searchParams = useSearchParams();
  const agentId = searchParams.get("agentId");

  const [isConnecting, setIsConnecting] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isEnded, setIsEnded] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [isAgentSpeaking, setIsAgentSpeaking] = useState(false);
  const [isUserSpeaking, setIsUserSpeaking] = useState(false);

  const pipecatRef = useRef<PipecatClient | null>(null);
  const connectionAttemptRef = useRef(0);
  const credentialsReceivedRef = useRef(false);

  const disconnect = useCallback(() => {
    connectionAttemptRef.current += 1;
    const client = pipecatRef.current;
    pipecatRef.current = null;
    void disconnectPipecatVoiceCall(client);
  }, []);

  const connect = useCallback(async (credentials: EmbedCallCredentials) => {
    if (!agentId) {
      throw new Error("No agent ID provided");
    }

    const attempt = ++connectionAttemptRef.current;
    const isCurrentAttempt = () => connectionAttemptRef.current === attempt;

    try {
      if (!credentials.token || !credentials.wsUrl || !credentials.sessionId) {
        throw new Error("Invalid token response");
      }
      if (!isCurrentAttempt()) return;

      const client = await connectPipecatVoiceCall(
        credentials.token,
        credentials.wsUrl,
        {
          onError: (voiceError) => {
            if (!isCurrentAttempt()) return;
            setError(getPublicVoiceCallErrorMessage(voiceError));
          },
          onClientCreated: (createdClient) => {
            if (isCurrentAttempt()) {
              pipecatRef.current = createdClient;
            } else {
              void disconnectPipecatVoiceCall(createdClient);
            }
          },
          onSpeakingChange: ({ isAgentSpeaking, isUserSpeaking }) => {
            if (!isCurrentAttempt()) return;
            setIsAgentSpeaking(isAgentSpeaking);
            setIsUserSpeaking(isUserSpeaking);
          },
        },
      );

      if (!isCurrentAttempt()) return;
      pipecatRef.current = client;
      setIsConnecting(false);
    } catch (err) {
      if (!isCurrentAttempt()) return;
      const publicMessage = getPublicVoiceCallErrorMessage(err);
      console.error("Embed call error:", err);
      throw new Error(publicMessage);
    }
  }, [agentId]);

  const handleHangUp = useCallback(() => {
    setIsEnded(true);
    disconnect();
    if (window.parent !== window) {
      window.parent.postMessage({ type: "AI_CALL_CLOSE" }, "*");
    }
  }, [disconnect]);

  const toggleMute = useCallback(() => {
    if (!pipecatRef.current) {
      console.error("No Pipecat client connected");
      return;
    }

    setIsMuted((prev) => {
      const next = !prev;
      pipecatRef.current?.enableMic(!next);
      return next;
    });
  }, []);

  useEffect(() => {
    if (!agentId) {
      setError("No agent ID provided");
      setIsConnecting(false);
      return;
    }

    credentialsReceivedRef.current = false;
    const isEmbedded = window.parent !== window;
    const expectedParentOrigin = isEmbedded
      ? getEmbeddingPageOrigin()
      : null;
    let isActive = true;

    const handleConnectionError = (err: unknown) => {
      if (!isActive) return;
      setError(err instanceof Error ? err.message : "Failed to connect");
      setIsConnecting(false);
    };

    const handleInitMessage = (event: MessageEvent<unknown>) => {
      if (!isEmbedded || event.source !== window.parent) return;
      // The message comes from the host page, not from this platform iframe.
      // Referrer may be empty when the host applies a strict no-referrer policy;
      // the event.source check still ensures only the immediate parent can send it.
      if (expectedParentOrigin && event.origin !== expectedParentOrigin) return;
      if (!event.data || typeof event.data !== "object") return;
      const data = event.data as Partial<EmbedCallCredentials> & {
        type?: unknown;
      };
      if (data.type !== "AI_CALL_INIT") return;
      if (credentialsReceivedRef.current) return;
      if (
        typeof data.token !== "string" ||
        typeof data.wsUrl !== "string" ||
        typeof data.sessionId !== "string"
      ) {
        handleConnectionError(new Error("Invalid embed call credentials"));
        return;
      }
      credentialsReceivedRef.current = true;
      connect({
        token: data.token,
        wsUrl: data.wsUrl,
        sessionId: data.sessionId,
      }).catch(handleConnectionError);
    };

    const connectStandalone = async () => {
      const pageSourceUrl = getCurrentPageSourceUrl();
      const sourceUrl = pageSourceUrl
        ? `?source_url=${encodeURIComponent(pageSourceUrl)}`
        : "";
      const response = await fetch(
        `${API_BASE_URL}/api/v1/embed/agent/${agentId}/token${sourceUrl}`,
        { method: "POST" },
      );
      if (!response.ok) {
        const errData = await response.json().catch(() => null);
        throw new Error(getPublicVoiceCallErrorMessage(errData));
      }
      const credentials = (await response.json()) as EmbedCallCredentials;
      await connect(credentials);
    };

    if (isEmbedded) {
      window.addEventListener("message", handleInitMessage);
      window.parent.postMessage({ type: "AI_CALL_READY" }, "*");
    } else {
      connectStandalone().catch(handleConnectionError);
    }

    return () => {
      isActive = false;
      window.removeEventListener("message", handleInitMessage);
      disconnect();
    };
  }, [agentId, connect, disconnect]);

  if (!agentId) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-50">
        <p className="text-red-500">No agent ID provided</p>
      </div>
    );
  }

  if (isConnecting) {
    return (
      <div className="flex flex-col items-center justify-center h-screen bg-gray-50">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500 mb-4" />
        <p className="text-gray-600">Connecting to agent...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-50">
        <div className="text-center px-4">
          <p className="text-red-500 mb-2">Connection Error</p>
          <p className="text-gray-600 text-sm">{error}</p>
          <Button onClick={handleHangUp} className="mt-4" variant="outline">
            Close
          </Button>
        </div>
      </div>
    );
  }

  if (isEnded) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-50">
        <div className="text-center px-4">
          <p className="text-gray-700 font-medium mb-2">Call Ended</p>
          <p className="text-gray-500 text-sm">Thank you for calling!</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      <div className="bg-white border-b px-4 py-3 flex items-center justify-between">
        <div>
          <h1 className="font-semibold text-gray-900">AI Voice Assistant</h1>
          <p className="text-xs text-gray-500">Connected</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
          <span className="text-xs text-green-600">Live</span>
        </div>
      </div>

      <div className="flex-1 flex flex-col items-center justify-center p-4 space-y-8">
        <div className="relative w-full max-w-sm">
          <div className="text-center mb-2">
            <span className="text-sm font-medium text-gray-700">AI Agent</span>
          </div>
          <div className="h-32 bg-white rounded-xl shadow-sm border overflow-hidden">
            <AgentAudioVisualizerWave
              state={isAgentSpeaking ? "speaking" : "listening"}
              color="#22c55e"
              className="w-full h-full"
            />
          </div>
        </div>

        <div className="relative w-full max-w-sm">
          <div className="text-center mb-2">
            <span className="text-sm font-medium text-gray-700">You</span>
            {isMuted && <span className="ml-2 text-xs text-red-500">(Muted)</span>}
          </div>
          <div className="h-32 bg-white rounded-xl shadow-sm border overflow-hidden">
            <AgentAudioVisualizerWave
              state={isMuted ? "idle" : isUserSpeaking ? "speaking" : "listening"}
              color={isMuted ? "#9ca3af" : "#3b82f6"}
              className="w-full h-full"
            />
          </div>
        </div>
      </div>

      <div className="bg-white border-t px-4 py-4 flex items-center justify-center gap-4">
        <Button
          variant={isMuted ? "destructive" : "outline"}
          size="lg"
          className="rounded-full w-14 h-14"
          onClick={toggleMute}
        >
          {isMuted ? <MicOff className="w-6 h-6" /> : <Mic className="w-6 h-6" />}
        </Button>

        <Button
          variant="destructive"
          size="lg"
          className="rounded-full w-14 h-14"
          onClick={handleHangUp}
        >
          <PhoneOff className="w-6 h-6" />
        </Button>
      </div>
    </div>
  );
}

export default function EmbedCallPage() {
  return (
    <Suspense
      fallback={
        <div className="flex flex-col items-center justify-center h-screen bg-gray-50">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500 mb-4" />
          <p className="text-gray-600">Loading...</p>
        </div>
      }
    >
      <EmbedCallContent />
    </Suspense>
  );
}
