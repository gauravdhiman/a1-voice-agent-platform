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

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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

  const disconnect = useCallback(() => {
    void disconnectPipecatVoiceCall(pipecatRef.current);
    pipecatRef.current = null;
  }, []);

  const connect = useCallback(async () => {
    if (!agentId) {
      throw new Error("No agent ID provided");
    }

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/embed/agent/${agentId}/token`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
        },
      );

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "Failed to get embed token");
      }

      const { token, wsUrl, sessionId } = await response.json();

      if (!token || !wsUrl || !sessionId) {
        throw new Error("Invalid token response");
      }

      const client = await connectPipecatVoiceCall(token, wsUrl, {
        onSpeakingChange: ({ isAgentSpeaking, isUserSpeaking }) => {
          setIsAgentSpeaking(isAgentSpeaking);
          setIsUserSpeaking(isUserSpeaking);
        },
      });

      pipecatRef.current = client;
      setIsConnecting(false);
    } catch (err) {
      console.error("Embed call error:", err);
      throw err;
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

    connect().catch((err) => {
      setError(err instanceof Error ? err.message : "Failed to connect");
      setIsConnecting(false);
    });

    return () => disconnect();
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
