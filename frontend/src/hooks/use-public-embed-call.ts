import { useCallback, useRef, useState } from "react";
import {
  Room,
  RoomEvent,
  LocalAudioTrack,
  RemoteAudioTrack,
  createLocalTracks,
  Track,
} from "livekit-client";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface EmbedCallState {
  token: string | null;
  serverUrl: string | null;
  roomName: string | null;
  isMuted: boolean;
  isAgentSpeaking: boolean;
  isUserSpeaking: boolean;
}

export function usePublicEmbedCall(agentId: string | null) {
  const [state, setState] = useState<EmbedCallState>({
    token: null,
    serverUrl: null,
    roomName: null,
    isMuted: false,
    isAgentSpeaking: false,
    isUserSpeaking: false,
  });

  const [agentAudioTrack, setAgentAudioTrack] = useState<RemoteAudioTrack | null>(null);

  const roomRef = useRef<Room | null>(null);
  const localAudioTrackRef = useRef<LocalAudioTrack | null>(null);

  const connect = useCallback(async () => {
    if (!agentId) {
      throw new Error("No agent ID provided");
    }

    try {
      // Call the public embed API to get token
      const response = await fetch(`${API_BASE_URL}/api/v1/embed/agent/${agentId}/token`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Failed to get embed token");
      }

      const data = await response.json();
      const { livekit_token, server_url, room_name } = data;

      if (!livekit_token || !server_url || !room_name) {
        throw new Error("Invalid token response");
      }

      // Create and connect to room
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

      // Set up event listeners
      room
        .on(RoomEvent.ParticipantConnected, (participant) => {
          console.log("Participant connected:", participant.identity);
        })
        .on(RoomEvent.ParticipantDisconnected, (participant) => {
          console.log("Participant disconnected:", participant.identity);
        })
        .on(RoomEvent.Disconnected, () => {
          console.log("Room disconnected");
        })
        .on(RoomEvent.TrackSubscribed, (track, _publication, participant) => {
          console.log("Track subscribed:", track.kind, "from", participant.identity);
          if (track.kind === Track.Kind.Audio) {
            setAgentAudioTrack(track as RemoteAudioTrack);
            // Attach audio
            const audioElement = track.attach();
            audioElement.autoplay = true;
            document.body.appendChild(audioElement);
          }
        })
        .on(RoomEvent.TrackUnsubscribed, (track) => {
          console.log("Track unsubscribed:", track.sid);
          if (track.kind === Track.Kind.Audio) {
            setAgentAudioTrack(null);
          }
        })
        .on(RoomEvent.ActiveSpeakersChanged, (speakers) => {
          // Check if agent is speaking (not the local participant)
          const agentSpeaking = speakers.some(
            (speaker) => speaker.sid !== room.localParticipant.sid
          );
          setState((prev) => ({
            ...prev,
            isAgentSpeaking: agentSpeaking,
          }));
        });

      await room.connect(server_url, livekit_token);

      // Get microphone access and publish
      const tracks = await createLocalTracks({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
        video: false,
      });

      const audioTrack = tracks.find((t) => t.kind === "audio") as LocalAudioTrack | undefined;

      if (!audioTrack) {
        throw new Error("No audio track created");
      }

      localAudioTrackRef.current = audioTrack;
      await room.localParticipant.publishTrack(audioTrack);

      // Listen for local speaking events
      room.localParticipant.on("isSpeakingChanged", (speaking) => {
        setState((prev) => ({
          ...prev,
          isUserSpeaking: speaking,
        }));
      });

      setState({
        token: livekit_token,
        serverUrl: server_url,
        roomName: room_name,
        isMuted: false,
        isAgentSpeaking: false,
        isUserSpeaking: false,
      });

      return { success: true };
    } catch (error) {
      console.error("Embed call connection error:", error);
      throw error;
    }
  }, [agentId]);

  const disconnect = useCallback(() => {
    // Clean up audio elements
    document.querySelectorAll("audio[data-livekit]").forEach((el) => el.remove());

    if (roomRef.current) {
      roomRef.current.disconnect();
      roomRef.current = null;
    }

    localAudioTrackRef.current = null;
    setAgentAudioTrack(null);
    setState({
      token: null,
      serverUrl: null,
      roomName: null,
      isMuted: false,
      isAgentSpeaking: false,
      isUserSpeaking: false,
    });
  }, []);

  const toggleMute = useCallback(() => {
    const audioTrack = localAudioTrackRef.current;
    if (!audioTrack) {
      console.error("No audio track found");
      return;
    }

    if (audioTrack.isMuted) {
      audioTrack.unmute();
      setState((prev) => ({ ...prev, isMuted: false }));
      console.log("Microphone unmuted");
    } else {
      audioTrack.mute();
      setState((prev) => ({ ...prev, isMuted: true }));
      console.log("Microphone muted");
    }
  }, []);

  return {
    ...state,
    userAudioTrack: localAudioTrackRef.current,
    agentAudioTrack,
    connect,
    disconnect,
    toggleMute,
  };
}
