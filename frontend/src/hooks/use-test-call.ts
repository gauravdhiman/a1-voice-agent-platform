import { useCallback, useRef, useState } from "react";
import {
  Room,
  RoomEvent,
  LocalAudioTrack,
  RemoteAudioTrack,
  createLocalTracks,
} from "livekit-client";

export interface TestCallState {
  isConnecting: boolean;
  isConnected: boolean;
  error: string | null;
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
  remoteAudioTrack: RemoteAudioTrack | null;
  localAudioTrack: LocalAudioTrack | null;
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
  });

  const [remoteAudioTrack, setRemoteAudioTrack] = useState<RemoteAudioTrack | null>(null);
  const [localAudioTrack, setLocalAudioTrack] = useState<LocalAudioTrack | null>(null);

  const roomRef = useRef<Room | null>(null);
  const audioRef = useRef<{
    localTracks: LocalAudioTrack[];
    remoteAudio: RemoteAudioTrack | null;
  }>({
    localTracks: [],
    remoteAudio: null,
  });

  const endCall = useCallback(() => {
    // Clean up any attached audio elements
    document.querySelectorAll('audio[data-livekit]').forEach(el => el.remove());

    if (roomRef.current) {
      roomRef.current.disconnect();
      roomRef.current = null;
    }

    audioRef.current = {
      localTracks: [],
      remoteAudio: null,
    };

    setRemoteAudioTrack(null);
    setLocalAudioTrack(null);

    setState({
      isConnecting: false,
      isConnected: false,
      error: null,
    });

    onDisconnected?.();
  }, [onDisconnected]);

  const toggleMute = useCallback(() => {
    const audioTrack = audioRef.current.localTracks[0];
    if (audioTrack) {
      if (audioTrack.isMuted) {
        audioTrack.unmute();
      } else {
        audioTrack.mute();
      }
    }
  }, []);

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
      const { token, serverUrl, roomName } = await agentService.getTestToken(agentId);

      if (!token || !serverUrl || !roomName) {
        throw new Error("Failed to get test token");
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
        .on(RoomEvent.ParticipantConnected, (participant) => {
          console.log("Participant connected:", participant.identity);
        })
        .on(RoomEvent.ParticipantDisconnected, (participant) => {
          console.log("Participant disconnected:", participant.identity);
        })
        .on(RoomEvent.Disconnected, () => {
          console.log("Room disconnected");
          endCall();
        })
        .on(RoomEvent.TrackSubscribed, (track, _publication, participant) => {
          console.log("Track subscribed:", track.sid, "from", participant.identity, "kind:", track.kind);
          if (track.kind === "audio") {
            audioRef.current.remoteAudio = track as unknown as RemoteAudioTrack;
            setRemoteAudioTrack(track as unknown as RemoteAudioTrack);
            
            // Attach and play the audio track
            const audioElement = track.attach();
            audioElement.autoplay = true;
            audioElement.setAttribute('data-livekit', 'true');
            document.body.appendChild(audioElement);
            
            console.log("Attached audio element for track:", track.sid);
          }
        })
        .on(RoomEvent.TrackUnsubscribed, (track) => {
          console.log("Track unsubscribed:", track.sid);
          if (audioRef.current.remoteAudio?.sid === track.sid) {
            audioRef.current.remoteAudio = null;
            setRemoteAudioTrack(null);
          }
        });

      await room.connect(serverUrl, token, {
        autoSubscribe: true,
      });

      console.log("Room connected, local participant:", room.localParticipant.identity);

      // Get audio track using LiveKit's native method
      try {
        const tracks = await createLocalTracks({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
          },
          video: false,
        });

        const audioTrack = tracks.find(
          (track) => track.kind === "audio"
        ) as LocalAudioTrack | undefined;

        if (!audioTrack) {
          throw new Error("No audio track created");
        }

        console.log("Created audio track, sid:", audioTrack.sid);
        
        audioRef.current.localTracks = [audioTrack];
        setLocalAudioTrack(audioTrack);
        
        // Publish the track
        await room.localParticipant.publishTrack(audioTrack);
        
        console.log("Published audio track");
      } catch (audioError) {
        console.error("Failed to get microphone access:", audioError);
        throw new Error("Microphone access denied. Please allow microphone access to test the agent.");
      }

      setState((prev) => ({
        ...prev,
        isConnecting: false,
        isConnected: true,
      }));

      onConnected?.();
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Failed to start test call");
      console.error("Test call error:", error);

      setState((prev) => ({
        ...prev,
        isConnecting: false,
        error: error.message,
      }));

      onError?.(error);
      endCall();
    }
  }, [agentId, state.isConnecting, state.isConnected, endCall, onConnected, onError]);

  return {
    ...state,
    startCall,
    endCall,
    toggleMute,
    remoteAudioTrack,
    localAudioTrack,
  };
}
