"use client";

import React, { useEffect, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import {
  Mic,
  MicOff,
  Phone,
  PhoneOff,
  Loader2,
  AlertCircle,
} from "lucide-react";
import { useTestCall } from "@/hooks/use-test-call";
import { AgentAudioVisualizerWave } from "@/components/agents-ui/agent-audio-visualizer-wave";

interface TestCallModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  agentId: string;
  agentName: string;
}

export function TestCallModal({
  open,
  onOpenChange,
  agentId,
  agentName,
}: TestCallModalProps) {
  const [isMuted, setIsMuted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const {
    isConnecting,
    isConnected,
    startCall,
    endCall,
    toggleMute,
    remoteAudioTrack,
    localAudioTrack,
  } = useTestCall({
    agentId,
    onConnected: () => {
      setError(null);
    },
    onDisconnected: () => {
      onOpenChange(false);
    },
    onError: (err) => {
      setError(err.message);
    },
  });

  const callInitiatedRef = React.useRef(false);

  useEffect(() => {
    if (open && !isConnected && !isConnecting && !callInitiatedRef.current) {
      callInitiatedRef.current = true;
      setError(null);
      startCall();
    }
    
    if (!open) {
      callInitiatedRef.current = false;
    }
  }, [open, isConnected, isConnecting, startCall]);

  const handleClose = () => {
    if (isConnected) {
      endCall();
    }
    onOpenChange(false);
  };

  const handleToggleMute = () => {
    toggleMute();
    setIsMuted(!isMuted);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Test Agent</DialogTitle>
          <DialogDescription>
            Test {agentName} by speaking directly in your browser
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col items-center py-4 space-y-4">
          {error && (
            <div className="flex items-center gap-2 text-destructive p-3 bg-destructive/10 rounded-md w-full">
              <AlertCircle className="h-4 w-4 flex-shrink-0" />
              <p className="text-sm">{error}</p>
            </div>
          )}

          {/* Main visualization area */}
          <div className="flex items-center justify-center gap-8 py-4">
            {isConnected ? (
              <>
                {/* User visualizer */}
                <div className="flex flex-col items-center gap-2">
                  <div className="w-20 h-20">
                    <AgentAudioVisualizerWave
                      size="sm"
                      state="speaking"
                      color="#3b82f6"
                      audioTrack={localAudioTrack ?? undefined}
                    />
                  </div>
                  <span className="text-xs text-muted-foreground">You</span>
                </div>

                {/* Connection indicator */}
                <div className="flex flex-col items-center gap-1">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                  <div className="w-8 h-px bg-border" />
                </div>

                {/* Agent visualizer */}
                <div className="flex flex-col items-center gap-2">
                  <div className="w-20 h-20">
                    <AgentAudioVisualizerWave
                      size="sm"
                      state="speaking"
                      color="#22c55e"
                      audioTrack={remoteAudioTrack ?? undefined}
                    />
                  </div>
                  <span className="text-xs text-muted-foreground">{agentName}</span>
                </div>
              </>
            ) : (
              <div
                className={`w-24 h-24 rounded-full flex items-center justify-center transition-all duration-300 ${
                  isConnecting ? "bg-yellow-50" : "bg-gray-50"
                }`}
              >
                {isConnecting ? (
                  <Loader2 className="h-10 w-10 text-yellow-500 animate-spin" />
                ) : (
                  <Phone className="h-10 w-10 text-gray-400" />
                )}
              </div>
            )}
          </div>

          {/* Status text */}
          <div className="text-center h-6">
            {isConnecting && (
              <p className="text-sm text-muted-foreground">
                Connecting to {agentName}...
              </p>
            )}
            {isConnected && (
              <p className="text-sm text-green-600 font-medium">
                Connected - Start speaking
              </p>
            )}
            {!isConnecting && !isConnected && !error && (
              <p className="text-sm text-muted-foreground">Ready to connect</p>
            )}
          </div>

          {/* Controls */}
          {isConnected && (
            <div className="flex items-center justify-center gap-4 pt-2">
              <Button
                variant={isMuted ? "destructive" : "outline"}
                size="icon"
                onClick={handleToggleMute}
                className="h-12 w-12 rounded-full"
              >
                {isMuted ? (
                  <MicOff className="h-5 w-5" />
                ) : (
                  <Mic className="h-5 w-5" />
                )}
              </Button>

              <Button
                variant="destructive"
                size="icon"
                onClick={handleClose}
                className="h-12 w-12 rounded-full"
              >
                <PhoneOff className="h-5 w-5" />
              </Button>
            </div>
          )}

          {!isConnected && (
            <Button
              onClick={startCall}
              disabled={isConnecting}
              className="w-full max-w-xs"
            >
              {isConnecting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Connecting...
                </>
              ) : (
                <>
                  <Phone className="mr-2 h-4 w-4" />
                  Start Test Call
                </>
              )}
            </Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
