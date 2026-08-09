"use client";

import React, { useEffect, useState } from "react";
import {
  Dialog,
  DialogContent,
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
  X,
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
  const [error, setError] = useState<string | null>(null);

  const {
    isConnecting,
    isConnected,
    startCall,
    endCall,
    toggleMute,
    isAgentSpeaking,
    isUserSpeaking,
    isMuted,
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

  const handleHangUp = () => {
    endCall();
    onOpenChange(false);
  };

  const handleDialogOpenChange = (nextOpen: boolean) => {
    if (!nextOpen) {
      handleHangUp();
      return;
    }
    onOpenChange(true);
  };

  return (
    <Dialog open={open} onOpenChange={handleDialogOpenChange}>
      <DialogContent 
        className="sm:max-w-md"
        hideCloseButton
        onInteractOutside={(e) => e.preventDefault()}
      >
        <DialogTitle className="sr-only">Test Call with {agentName}</DialogTitle>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="absolute right-4 top-4"
          onClick={handleHangUp}
          aria-label="Close test call"
        >
          <X className="h-4 w-4" />
        </Button>
        <div className="flex flex-col items-center py-4 space-y-4">
          {error && (
            <>
              <div className="flex items-center gap-2 text-destructive p-3 bg-destructive/10 rounded-md w-full">
                <AlertCircle className="h-4 w-4 flex-shrink-0" />
                <p className="text-sm">{error}</p>
              </div>
              <Button type="button" variant="outline" onClick={handleHangUp}>
                Close
              </Button>
            </>
          )}

          {!isConnected && !error && (
            <div className="flex flex-col items-center justify-center py-8 space-y-4">
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
              <div className="text-center">
                {isConnecting && (
                  <p className="text-sm text-muted-foreground">
                    Connecting to {agentName}...
                  </p>
                )}
                {!isConnecting && (
                  <Button
                    onClick={startCall}
                    disabled={isConnecting}
                    className="w-full max-w-xs"
                  >
                    <Phone className="mr-2 h-4 w-4" />
                    Start Test Call
                  </Button>
                )}
              </div>
            </div>
          )}

          {isConnected && (
            <>
              <div className="w-full max-w-sm space-y-4">
                <div>
                  <div className="text-center mb-2">
                    <span className="text-sm font-medium text-gray-700">{agentName}</span>
                  </div>
                  <div className="h-32 bg-white rounded-xl shadow-sm border overflow-hidden">
                    <AgentAudioVisualizerWave
                      state={isAgentSpeaking ? "speaking" : "listening"}
                      color="#22c55e"
                      className="w-full h-full"
                    />
                  </div>
                </div>

                <div>
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

              <div className="flex items-center justify-center gap-4 pt-2">
                <Button
                  variant={isMuted ? "destructive" : "outline"}
                  size="icon"
                  onClick={toggleMute}
                  className="h-14 w-14 rounded-full"
                >
                  {isMuted ? (
                    <MicOff className="h-6 w-6" />
                  ) : (
                    <Mic className="h-6 w-6" />
                  )}
                </Button>

                <Button
                  variant="destructive"
                  size="icon"
                  onClick={handleHangUp}
                  className="h-14 w-14 rounded-full"
                >
                  <PhoneOff className="h-6 w-6" />
                </Button>
              </div>
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
