"use client";

import { Suspense, useEffect, useState, useRef, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import { Mic, MicOff, PhoneOff, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { AgentAudioVisualizerWave } from "@/components/agents-ui/agent-audio-visualizer-wave";
import {
  Room,
  RoomEvent,
  LocalAudioTrack,
  RemoteAudioTrack,
  createLocalTracks,
  Track,
} from "livekit-client";

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
  const [agentAudioTrack, setAgentAudioTrack] = useState<RemoteAudioTrack | null>(null);
  const [userAudioTrack, setUserAudioTrack] = useState<LocalAudioTrack | null>(null);

  const roomRef = useRef<Room | null>(null);
  const localTrackRef = useRef<LocalAudioTrack | null>(null);

  const connect = useCallback(async () => {
    if (!agentId) {
      throw new Error("No agent ID provided");
    }

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/embed/agent/${agentId}/token`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "Failed to get embed token");
      }

      const { livekit_token, server_url, room_name } = await response.json();

      if (!livekit_token || !server_url || !room_name) {
        throw new Error("Invalid token response");
      }

      const room = new Room({
        adaptiveStream: true,
        dynacast: true,
        audioCaptureDefaults: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      roomRef.current = room;

      room
        .on(RoomEvent.ParticipantConnected, (p) => console.log("Participant connected:", p.identity))
        .on(RoomEvent.ParticipantDisconnected, (p) => console.log("Participant disconnected:", p.identity))
        .on(RoomEvent.Disconnected, () => console.log("Room disconnected"))
        .on(RoomEvent.TrackSubscribed, (track, _pub, participant) => {
          console.log("Track subscribed:", track.kind, "from", participant.identity);
          if (track.kind === Track.Kind.Audio) {
            setAgentAudioTrack(track as RemoteAudioTrack);
            const el = track.attach();
            el.autoplay = true;
            document.body.appendChild(el);
          }
        })
        .on(RoomEvent.TrackUnsubscribed, (track) => {
          if (track.kind === Track.Kind.Audio) {
            setAgentAudioTrack(null);
          }
        })
        .on(RoomEvent.ActiveSpeakersChanged, (speakers) => {
          const localSid = room.localParticipant.sid;
          const agentSpeaking = speakers.some((s) => s.sid !== localSid);
          const userSpeaking = speakers.some((s) => s.sid === localSid);
          setIsAgentSpeaking(agentSpeaking);
          setIsUserSpeaking(userSpeaking);
        });

      await room.connect(server_url, livekit_token);

      const tracks = await createLocalTracks({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
        video: false,
      });

      const audioTrack = tracks.find((t) => t.kind === "audio") as LocalAudioTrack | undefined;
      if (!audioTrack) throw new Error("No audio track created");

      localTrackRef.current = audioTrack;
      setUserAudioTrack(audioTrack);
      await room.localParticipant.publishTrack(audioTrack);

      setIsConnecting(false);
    } catch (err) {
      console.error("Embed call error:", err);
      throw err;
    }
  }, [agentId]);

  const disconnect = useCallback(() => {
    document.querySelectorAll("audio[data-livekit]").forEach((el) => el.remove());
    if (roomRef.current) {
      roomRef.current.disconnect();
      roomRef.current = null;
    }
    localTrackRef.current = null;
    setUserAudioTrack(null);
    setAgentAudioTrack(null);
  }, []);

  const handleHangUp = useCallback(() => {
    setIsEnded(true);
    disconnect();
    if (window.parent !== window) {
      window.parent.postMessage({ type: "AI_CALL_CLOSE" }, "*");
    }
  }, [disconnect]);

  const toggleMute = useCallback(() => {
    const room = roomRef.current;
    if (!room) {
      console.error("No room reference");
      return;
    }

    // Get the published audio track from the local participant
    const publications = room.localParticipant.audioTrackPublications;
    const audioPub = Array.from(publications.values())[0];
    
    if (!audioPub || !audioPub.track) {
      console.error("No audio track publication found");
      return;
    }

    const track = audioPub.track as LocalAudioTrack;
    console.log("Current track muted state:", track.isMuted);

    if (track.isMuted) {
      track.unmute();
      setIsMuted(false);
      console.log("Called unmute()");
    } else {
      track.mute();
      setIsMuted(true);
      console.log("Called mute()");
    }
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
              audioTrack={agentAudioTrack ?? undefined}
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
              audioTrack={userAudioTrack ?? undefined}
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
