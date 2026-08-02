"use client";

import { useCallback, useRef, useState } from "react";
import {
  Room,
  RoomEvent,
  LocalAudioTrack,
  RemoteAudioTrack,
  createLocalTracks,
} from "livekit-client";
import { PipecatClient, RTVIEvent } from "@pipecat-ai/client-js";
import { WebSocketTransport } from "@pipecat-ai/websocket-transport";

/**
 * Browser test-call hook.
 *
 * Supports two transports based on backend ``VOICE_TRANSPORT``:
 * - ``pipecat`` (default): WebSocket audio via Pipecat client SDK
 * - ``livekit``: legacy LiveKit WebRTC room (rollback path)
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
  /** LiveKit-only; null on Pipecat path (visualizer uses speaking flags). */
  remoteAudioTrack: RemoteAudioTrack | null;
  /** LiveKit-only; null on Pipecat path. */
  localAudioTrack: LocalAudioTrack | null;
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

  const [remoteAudioTrack, setRemoteAudioTrack] =
    useState<RemoteAudioTrack | null>(null);
  const [localAudioTrack, setLocalAudioTrack] =
    useState<LocalAudioTrack | null>(null);
  const [isMuted, setIsMuted] = useState(false);

  const roomRef = useRef<Room | null>(null);
  const pipecatRef = useRef<PipecatClient | null>(null);
  const transportRef = useRef<"pipecat" | "livekit" | null>(null);
  const audioRef = useRef<{
    localTracks: LocalAudioTrack[];
    remoteAudio: RemoteAudioTrack | null;
  }>({
    localTracks: [],
    remoteAudio: null,
  });

  const endCall = useCallback(() => {
    document.querySelectorAll("audio[data-livekit]").forEach((el) => el.remove());

    if (pipecatRef.current) {
      try {
        void pipecatRef.current.disconnect();
      } catch {
        /* ignore */
      }
      pipecatRef.current = null;
    }

    if (roomRef.current) {
      roomRef.current.disconnect();
      roomRef.current = null;
    }

    transportRef.current = null;
    audioRef.current = {
      localTracks: [],
      remoteAudio: null,
    };

    setRemoteAudioTrack(null);
    setLocalAudioTrack(null);
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
    if (transportRef.current === "pipecat" && pipecatRef.current) {
      const next = !isMuted;
      pipecatRef.current.enableMic(!next);
      setIsMuted(next);
      return;
    }

    const audioTrack = audioRef.current.localTracks[0];
    if (audioTrack) {
      if (audioTrack.isMuted) {
        audioTrack.unmute();
        setIsMuted(false);
      } else {
        audioTrack.mute();
        setIsMuted(true);
      }
    }
  }, [isMuted]);

  const startPipecatCall = useCallback(
    async (token: string, wsUrl: string) => {
      const client = new PipecatClient({
        transport: new WebSocketTransport(),
        enableMic: true,
        enableCam: false,
        callbacks: {
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
          onError: (err) => {
            const error =
              err instanceof Error ? err : new Error(String(err ?? "Voice error"));
            setState((prev) => ({
              ...prev,
              isConnecting: false,
              error: error.message,
            }));
            onError?.(error);
          },
        },
      });

      pipecatRef.current = client;
      transportRef.current = "pipecat";

      client.on(RTVIEvent.BotStartedSpeaking, () => {
        setState((prev) => ({ ...prev, isAgentSpeaking: true }));
      });
      client.on(RTVIEvent.BotStoppedSpeaking, () => {
        setState((prev) => ({ ...prev, isAgentSpeaking: false }));
      });
      client.on(RTVIEvent.UserStartedSpeaking, () => {
        setState((prev) => ({ ...prev, isUserSpeaking: true }));
      });
      client.on(RTVIEvent.UserStoppedSpeaking, () => {
        setState((prev) => ({ ...prev, isUserSpeaking: false }));
      });

      // Append token as query param for voice-ws auth
      const url = new URL(wsUrl.replace(/^ws/, "http"));
      url.searchParams.set("token", token);
      const finalWs = url.toString().replace(/^http/, "ws");

      await client.connect({ ws_url: finalWs });
    },
    [endCall, onConnected, onError],
  );

  const startLiveKitCall = useCallback(
    async (token: string, serverUrl: string) => {
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
      transportRef.current = "livekit";

      room
        .on(RoomEvent.Disconnected, () => {
          endCall();
        })
        .on(RoomEvent.ActiveSpeakersChanged, (speakers) => {
          const localSid = room.localParticipant.sid;
          const agentSpeaking = speakers.some((s) => s.sid !== localSid);
          const userSpeaking = speakers.some((s) => s.sid === localSid);
          setState((prev) => ({
            ...prev,
            isAgentSpeaking: agentSpeaking,
            isUserSpeaking: userSpeaking,
          }));
        })
        .on(RoomEvent.TrackSubscribed, (track, _publication, participant) => {
          if (track.kind === "audio") {
            audioRef.current.remoteAudio = track as unknown as RemoteAudioTrack;
            setRemoteAudioTrack(track as unknown as RemoteAudioTrack);

            const audioElement = track.attach();
            audioElement.autoplay = true;
            audioElement.setAttribute("data-livekit", "true");
            document.body.appendChild(audioElement);
          }
          void participant;
        })
        .on(RoomEvent.TrackUnsubscribed, (track) => {
          if (audioRef.current.remoteAudio?.sid === track.sid) {
            audioRef.current.remoteAudio = null;
            setRemoteAudioTrack(null);
          }
        });

      await room.connect(serverUrl, token, {
        autoSubscribe: true,
      });

      const tracks = await createLocalTracks({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
        video: false,
      });

      const audioTrack = tracks.find(
        (track) => track.kind === "audio",
      ) as LocalAudioTrack | undefined;

      if (!audioTrack) {
        throw new Error("No audio track created");
      }

      audioRef.current.localTracks = [audioTrack];
      setLocalAudioTrack(audioTrack);
      await room.localParticipant.publishTrack(audioTrack);

      setState((prev) => ({
        ...prev,
        isConnecting: false,
        isConnected: true,
      }));

      onConnected?.();
    },
    [endCall, onConnected],
  );

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
      const transport = bootstrap.transport ?? "livekit";

      if (transport === "pipecat") {
        if (!bootstrap.token || !bootstrap.wsUrl) {
          throw new Error("Failed to get Pipecat voice session");
        }
        await startPipecatCall(bootstrap.token, bootstrap.wsUrl);
        return;
      }

      if (!bootstrap.token || !bootstrap.serverUrl || !bootstrap.roomName) {
        throw new Error("Failed to get LiveKit test token");
      }
      await startLiveKitCall(bootstrap.token, bootstrap.serverUrl);
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
    onError,
    startPipecatCall,
    startLiveKitCall,
  ]);

  return {
    ...state,
    startCall,
    endCall,
    toggleMute,
    remoteAudioTrack,
    localAudioTrack,
    isMuted,
  };
}
