"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, Loader2, Mic, MicOff, PhoneOff } from "lucide-react";
import { AgentAudioVisualizerWave } from "@/components/agents-ui/agent-audio-visualizer-wave";
import { Button } from "@/components/ui/button";
import {
  publicOrgPageService,
  readStoredAccessToken,
} from "@/services/public-org-page-service";
import {
  Room,
  RoomEvent,
  LocalAudioTrack,
  RemoteAudioTrack,
  createLocalTracks,
  Track,
} from "livekit-client";

function PublicCallContent() {
  const params = useParams<{ slug: string; agentId: string }>();
  const { slug, agentId } = params;

  const [isConnecting, setIsConnecting] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isEnded, setIsEnded] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [isAgentSpeaking, setIsAgentSpeaking] = useState(false);
  const [isUserSpeaking, setIsUserSpeaking] = useState(false);
  const [agentAudioTrack, setAgentAudioTrack] = useState<RemoteAudioTrack | null>(
    null,
  );
  const [userAudioTrack, setUserAudioTrack] = useState<LocalAudioTrack | null>(
    null,
  );

  const roomRef = useRef<Room | null>(null);
  const localTrackRef = useRef<LocalAudioTrack | null>(null);

  const disconnect = useCallback(() => {
    const room = roomRef.current;
    if (room) {
      room.disconnect();
      roomRef.current = null;
    }
    localTrackRef.current = null;
    setUserAudioTrack(null);
    setAgentAudioTrack(null);
  }, []);

  const connect = useCallback(async () => {
    const accessToken = readStoredAccessToken(slug);
    const data = await publicOrgPageService.getCallToken(slug, agentId, accessToken);

    const { livekit_token, server_url, room_name } = data;
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
      .on(RoomEvent.TrackSubscribed, (track) => {
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
        setIsAgentSpeaking(speakers.some((s) => s.sid !== localSid));
        setIsUserSpeaking(speakers.some((s) => s.sid === localSid));
      });

    await room.connect(server_url, livekit_token);

    const tracks = await createLocalTracks({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
      video: false,
    });

    const audioTrack = tracks.find((t) => t.kind === Track.Kind.Audio) as
      | LocalAudioTrack
      | undefined;
    if (audioTrack) {
      localTrackRef.current = audioTrack;
      setUserAudioTrack(audioTrack);
      await room.localParticipant.publishTrack(audioTrack);
    }

    setIsConnecting(false);
  }, [slug, agentId]);

  const handleHangUp = useCallback(() => {
    setIsEnded(true);
    disconnect();
  }, [disconnect]);

  const toggleMute = useCallback(() => {
    const room = roomRef.current;
    if (!room) return;

    const publications = room.localParticipant.audioTrackPublications;
    const audioPub = Array.from(publications.values())[0];
    if (!audioPub?.track) return;

    const track = audioPub.track as LocalAudioTrack;
    if (track.isMuted) {
      track.unmute();
      setIsMuted(false);
    } else {
      track.mute();
      setIsMuted(true);
    }
  }, []);

  useEffect(() => {
    connect().catch((err) => {
      setError(err instanceof Error ? err.message : "Failed to connect");
      setIsConnecting(false);
    });
    return () => disconnect();
  }, [connect, disconnect]);

  if (isConnecting) {
    return (
      <div className="flex min-h-dvh flex-col items-center justify-center bg-background px-4">
        <Loader2 className="mb-4 h-8 w-8 animate-spin text-primary" />
        <p className="text-muted-foreground">Connecting to agent...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-dvh flex-col items-center justify-center bg-background px-4">
        <p className="mb-2 font-medium text-destructive">Connection error</p>
        <p className="mb-4 text-center text-sm text-muted-foreground">{error}</p>
        <Button asChild variant="outline">
          <Link href={`/o/${slug}`}>Back to agents</Link>
        </Button>
      </div>
    );
  }

  if (isEnded) {
    return (
      <div className="flex min-h-dvh flex-col items-center justify-center bg-background px-4">
        <p className="mb-2 text-lg font-medium">Call ended</p>
        <p className="mb-6 text-sm text-muted-foreground">Thank you for calling!</p>
        <Button asChild>
          <Link href={`/o/${slug}`}>Back to agents</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="flex min-h-dvh flex-col bg-background">
      <header className="flex items-center gap-3 border-b px-4 py-3">
        <Button asChild variant="ghost" size="icon" className="shrink-0">
          <Link href={`/o/${slug}`} aria-label="Back">
            <ArrowLeft className="h-5 w-5" />
          </Link>
        </Button>
        <div className="min-w-0 flex-1">
          <h1 className="truncate font-semibold">Voice call</h1>
          <p className="text-xs text-muted-foreground">Connected</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 animate-pulse rounded-full bg-green-500" />
          <span className="text-xs text-green-600">Live</span>
        </div>
      </header>

      <div className="flex flex-1 flex-col items-center justify-center gap-8 p-4">
        <div className="w-full max-w-sm">
          <p className="mb-2 text-center text-sm font-medium text-muted-foreground">
            Agent
          </p>
          <div className="h-32 overflow-hidden rounded-xl border bg-card">
            <AgentAudioVisualizerWave
              audioTrack={agentAudioTrack ?? undefined}
              state={isAgentSpeaking ? "speaking" : "listening"}
              color="#22c55e"
              className="h-full w-full"
            />
          </div>
        </div>

        <div className="w-full max-w-sm">
          <p className="mb-2 text-center text-sm font-medium text-muted-foreground">
            You
            {isMuted ? (
              <span className="ml-2 text-xs text-destructive">(Muted)</span>
            ) : null}
          </p>
          <div className="h-32 overflow-hidden rounded-xl border bg-card">
            <AgentAudioVisualizerWave
              audioTrack={userAudioTrack ?? undefined}
              state={isMuted ? "idle" : isUserSpeaking ? "speaking" : "listening"}
              color={isMuted ? "#9ca3af" : "#3b82f6"}
              className="h-full w-full"
            />
          </div>
        </div>
      </div>

      <footer className="flex items-center justify-center gap-6 border-t px-4 py-6 pb-[max(1.5rem,env(safe-area-inset-bottom))]">
        <Button
          type="button"
          variant={isMuted ? "destructive" : "outline"}
          size="lg"
          className="h-14 w-14 rounded-full"
          onClick={toggleMute}
          aria-label={isMuted ? "Unmute" : "Mute"}
        >
          {isMuted ? <MicOff className="h-6 w-6" /> : <Mic className="h-6 w-6" />}
        </Button>
        <Button
          type="button"
          variant="destructive"
          size="lg"
          className="h-14 w-14 rounded-full"
          onClick={handleHangUp}
          aria-label="End call"
        >
          <PhoneOff className="h-6 w-6" />
        </Button>
      </footer>
    </div>
  );
}

export default function PublicOrgCallPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-dvh items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      }
    >
      <PublicCallContent />
    </Suspense>
  );
}
