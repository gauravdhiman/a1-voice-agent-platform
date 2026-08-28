"use client";

import * as React from "react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import {
  Loader2,
  Mic,
  MicOff,
  PhoneOff,
  ArrowLeft,
  Sparkles,
  Building2,
} from "lucide-react";
import { AgentAudioRadialV4 } from "@/components/agents-ui/agent-audio-radial-v4";
import { AgentAudioVisualizerBarV4 } from "@/components/agents-ui/agent-audio-visualizer-livekit-bar-v4";
import { resolveDemoVisualizer } from "@/components/agents-ui/demo-visualizer-config";
import type { LevelMediaManager } from "@/lib/level-media-manager";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  demoPublicService,
  type DemoAgentPublic,
} from "@/services/demo-public-service";
import type { PipecatClient } from "@pipecat-ai/client-js";
import {
  connectPipecatVoiceCall,
  disconnectPipecatVoiceCall,
} from "@/lib/pipecat-voice-client";
import { getPublicVoiceCallErrorMessage } from "@/lib/voice-call-messages";
import {
  DEMO_TRIAL_EXHAUSTED_MESSAGE,
  formatDemoCallsRemaining,
  formatDemoDuration,
  isDemoCallLimitReached,
} from "@/lib/demo-call-limits";

/**
 * Reads normalized local microphone bands for the public demo visualizers.
 *
 * @param track - Local microphone track supplied by the voice transport.
 * @param barCount - Number of normalized bands to produce.
 * @param isActive - Whether the transport currently reports user speech.
 * @param analyzeWhenInactive - Keeps the analyser alive for the LiveKit bars so a
 * strong mic signal can animate the bars even if the speech event is delayed.
 * @param smoothingTimeConstant - Audio analyser smoothing, from 0 (fast) to 1 (calm).
 * @returns A normalized volume value for each visualizer bar.
 */
function useTrackVolumeBands(
  track: MediaStreamTrack | null | undefined,
  barCount: number,
  isActive: boolean,
  analyzeWhenInactive = false,
  smoothingTimeConstant = 0.75,
): number[] {
  const [bands, setBands] = React.useState<number[]>(() =>
    Array.from({ length: barCount }, () => 0),
  );
  React.useEffect(() => {
    if (!track || (!isActive && !analyzeWhenInactive)) {
      setBands(Array.from({ length: barCount }, () => 0.08));
      return;
    }
    let ctx: AudioContext | null = null;
    let analyser: AnalyserNode | null = null;
    let source: MediaStreamAudioSourceNode | null = null;
    let rafId = 0;
    let cancelled = false;
    try {
      const AC =
        window.AudioContext ??
        (window as unknown as { webkitAudioContext?: typeof AudioContext })
          .webkitAudioContext;
      if (!AC) return;
      ctx = new AC();
      if (ctx.state === "suspended") void ctx.resume();
      source = ctx.createMediaStreamSource(new MediaStream([track]));
      analyser = ctx.createAnalyser();
      analyser.fftSize = 512;
      analyser.smoothingTimeConstant = smoothingTimeConstant;
      source.connect(analyser);
    } catch {
      return;
    }
    const freq = new Uint8Array(analyser.frequencyBinCount);
    const tick = () => {
      if (cancelled || !analyser) return;
      analyser.getByteFrequencyData(freq);
      const binHz = (ctx?.sampleRate ?? 48000) / analyser.fftSize;
      const lo = Math.max(1, Math.floor(80 / binHz));
      const hi = Math.min(freq.length, Math.floor(6000 / binHz));
      const usable = hi - lo;
      const perBand = Math.max(1, Math.floor(usable / barCount));
      const next: number[] = [];
      for (let i = 0; i < barCount; i++) {
        let sum = 0;
        for (let b = 0; b < perBand; b++)
          sum += freq[lo + i * perBand + b] ?? 0;
        const v = sum / (perBand * 255);
        const boost = 1 + (i / barCount) * 1.1;
        next.push(Math.min(1, v * boost * 1.4));
      }
      setBands(next);
      rafId = requestAnimationFrame(tick);
    };
    rafId = requestAnimationFrame(tick);
    return () => {
      cancelled = true;
      cancelAnimationFrame(rafId);
      try {
        source?.disconnect();
        void ctx?.close();
      } catch {
        /* ignore */
      }
    };
  }, [track, barCount, isActive, analyzeWhenInactive, smoothingTimeConstant]);
  return bands;
}

export default function DemoAgentPage() {
  const params = useParams<{ slug: string }>();
  const slug = params.slug;
  const searchParams = useSearchParams();
  const visualizer = resolveDemoVisualizer(searchParams.get("visualizer"));
  const useLiveKitBars = visualizer === "lk-bars";

  const [agent, setAgent] = React.useState<DemoAgentPublic | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  const [callState, setCallState] = React.useState<
    "idle" | "connecting" | "connected" | "ended"
  >("idle");
  const [callError, setCallError] = React.useState<string | null>(null);
  const [isMuted, setIsMuted] = React.useState(false);
  const [isAgentSpeaking, setIsAgentSpeaking] = React.useState(false);
  const [isUserSpeaking, setIsUserSpeaking] = React.useState(false);
  const [agentTrack, setAgentTrack] = React.useState<MediaStreamTrack | null>(
    null,
  );
  const [localTrack, setLocalTrack] = React.useState<MediaStreamTrack | null>(
    null,
  );
  const levelManagerRef = React.useRef<LevelMediaManager | null>(null);
  const [agentVolumeBands, setAgentVolumeBands] = React.useState<number[]>(
    Array.from({ length: 5 }, () => 0.08),
  );
  const userVolumeBands = useTrackVolumeBands(
    isMuted ? null : localTrack,
    5,
    isUserSpeaking,
    useLiveKitBars,
    useLiveKitBars ? 0.55 : 0.75,
  );
  const agentTrackVolumeBands = useTrackVolumeBands(
    agentTrack,
    5,
    isAgentSpeaking && useLiveKitBars,
    useLiveKitBars,
    0.55,
  );

  const pipecatRef = React.useRef<PipecatClient | null>(null);

  React.useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    demoPublicService
      .getDemoAgent(slug)
      .then((data) => {
        if (!cancelled) setAgent(data);
      })
      .catch((e: Error) => {
        if (!cancelled) setError(e.message || "Demo not found");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [slug]);

  const disconnect = React.useCallback(async () => {
    await disconnectPipecatVoiceCall(pipecatRef.current);
    pipecatRef.current = null;
    setAgentTrack(null);
    setLocalTrack(null);
  }, []);

  const handleStartCall = React.useCallback(async () => {
    if (!agent) {
      return;
    }
    if (isDemoCallLimitReached(agent.demo_calls_remaining)) {
      setCallError(DEMO_TRIAL_EXHAUSTED_MESSAGE);
      return;
    }
    setCallError(null);
    setCallState("connecting");
    try {
      const { token, wsUrl, demo_calls_remaining } =
        await demoPublicService.getCallToken(slug);
      if (typeof demo_calls_remaining === "number") {
        setAgent((current) =>
          current ? { ...current, demo_calls_remaining } : current,
        );
      }
      const client = await connectPipecatVoiceCall(token, wsUrl, {
        onSpeakingChange: ({ isAgentSpeaking, isUserSpeaking }) => {
          setIsAgentSpeaking(isAgentSpeaking);
          setIsUserSpeaking(isUserSpeaking);
        },
        onBotAudioTrack: (track) => setAgentTrack(track),
        onLocalAudioTrack: (track) => setLocalTrack(track),
        onLevelManager: (mgr) => {
          levelManagerRef.current = mgr as unknown as LevelMediaManager;
        },
        onDisconnected: () => {
          setAgentTrack(null);
          setLocalTrack(null);
          setCallState("ended");
        },
        onError: (err) => {
          setCallError(getPublicVoiceCallErrorMessage(err) || err.message);
          setCallState("idle");
        },
      });
      pipecatRef.current = client;
      setCallState("connected");
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to start call";
      setCallError(getPublicVoiceCallErrorMessage(e) || msg);
      setAgentTrack(null);
      setLocalTrack(null);
      setCallState("idle");
    }
  }, [agent, slug]);

  const handleHangUp = React.useCallback(async () => {
    await disconnect();
    setCallState("ended");
    setIsAgentSpeaking(false);
    setIsUserSpeaking(false);
  }, [disconnect]);

  React.useEffect(() => {
    if (!useLiveKitBars) return;
    if (!isAgentSpeaking) {
      setAgentVolumeBands(Array.from({ length: 5 }, () => 0.08));
      return;
    }
    const id = setInterval(() => {
      const lvl = levelManagerRef.current?.readLevels().level ?? 0.45;
      setAgentVolumeBands(
        Array.from({ length: 5 }, () =>
          Math.min(1, lvl * 0.75 + Math.random() * 0.22),
        ),
      );
    }, 80);
    return () => clearInterval(id);
  }, [isAgentSpeaking, useLiveKitBars]);

  const toggleMute = React.useCallback(() => {
    const next = !isMuted;
    setIsMuted(next);
    const client = pipecatRef.current as unknown as {
      setMicMuted?: (v: boolean) => void;
      setMicrophoneMuted?: (v: boolean) => void;
    };
    try {
      if (client?.setMicMuted) client.setMicMuted(next);
      else if (client?.setMicrophoneMuted) client.setMicrophoneMuted(next);
    } catch {
      // ignore
    }
  }, [isMuted]);

  React.useEffect(() => {
    return () => {
      void disconnect();
    };
  }, [disconnect]);

  if (loading) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-gradient-to-b from-muted/40 to-background">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (error || !agent) {
    return (
      <div className="flex min-h-dvh flex-col items-center justify-center gap-4 bg-gradient-to-b from-muted/40 to-background p-6 text-center">
        <p className="text-lg font-semibold">Demo not found</p>
        <p className="max-w-sm text-sm text-muted-foreground">
          {error ||
            "This demo link is invalid or the agent is no longer a demo."}
        </p>
        <Button asChild variant="outline">
          <Link href="/">Go home</Link>
        </Button>
      </div>
    );
  }

  const callsRemainingLabel = formatDemoCallsRemaining(
    agent.demo_calls_remaining,
  );
  const durationLabel = formatDemoDuration(
    agent.demo_max_call_duration_seconds,
  );
  const demoCallLimitReached = isDemoCallLimitReached(
    agent.demo_calls_remaining,
  );

  if (callState === "ended") {
    return (
      <div className="flex min-h-dvh flex-col items-center justify-center gap-6 bg-background p-6 text-center">
        <div className="h-20 w-20 rounded-full bg-green-100 flex items-center justify-center">
          <Sparkles className="h-8 w-8 text-green-600" />
        </div>
        <div className="space-y-1">
          <h2 className="text-xl font-semibold">Call ended</h2>
          <p className="text-sm text-muted-foreground">
            Thanks for trying {agent.name}!
          </p>
        </div>
        <Button onClick={() => setCallState("idle")}>Back to demo</Button>
      </div>
    );
  }

  if (callState === "connected" || callState === "connecting") {
    if (callState === "connecting") {
      return (
        <div className="flex min-h-dvh flex-col items-center justify-center gap-4 bg-background">
          <Loader2 className="h-10 w-10 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">
            Connecting to {agent.name}…
          </p>
          <p className="text-xs text-muted-foreground">
            Please allow microphone access when prompted
          </p>
        </div>
      );
    }
    return (
      <div className="flex min-h-dvh flex-col bg-background">
        <header className="flex items-center gap-3 border-b px-4 py-3">
          <Button
            variant="ghost"
            size="icon"
            onClick={handleHangUp}
            aria-label="Back"
          >
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div className="min-w-0 flex-1">
            <h1 className="truncate font-semibold">{agent.name}</h1>
            <p className="text-xs text-muted-foreground truncate">
              {agent.public_description || agent.mission || "Demo agent"}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 animate-pulse rounded-full bg-green-500" />
            <span className="text-xs text-green-600">Live</span>
          </div>
        </header>

        {callError && (
          <div className="mx-4 mt-4 rounded-md border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
            {callError}
          </div>
        )}

        <div className="flex flex-1 flex-col items-center justify-center gap-12 p-4">
          <div className="flex flex-col items-center gap-2">
            {useLiveKitBars ? (
              <AgentAudioVisualizerBarV4
                size="lg"
                state={isAgentSpeaking ? "speaking" : "listening"}
                barCount={5}
                volumeBands={
                  agentTrack ? agentTrackVolumeBands : agentVolumeBands
                }
                color="#22d3ee"
              />
            ) : (
              <AgentAudioRadialV4
                getAudioLevel={() =>
                  levelManagerRef.current?.readLevels().level ?? null
                }
                active={isAgentSpeaking}
                size={220}
                barCount={72}
                color="#22d3ee"
              />
            )}
            <p className="text-sm font-medium text-muted-foreground">
              {agent.name} {isAgentSpeaking ? "is speaking…" : "is listening"}
            </p>
          </div>

          <div className="flex flex-col items-center gap-1">
            {useLiveKitBars ? (
              <AgentAudioVisualizerBarV4
                size="lg"
                state={
                  isMuted ? "idle" : isUserSpeaking ? "speaking" : "listening"
                }
                barCount={5}
                volumeBands={userVolumeBands}
                color={isMuted ? "#9ca3af" : "#818cf8"}
              />
            ) : (
              <AgentAudioRadialV4
                track={isMuted ? null : localTrack}
                active={isUserSpeaking}
                size={220}
                barCount={72}
                color="#818cf8"
              />
            )}
            <p className="text-sm font-medium text-muted-foreground">
              You {isMuted ? "(muted)" : isUserSpeaking ? "are speaking…" : ""}
            </p>
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
            {isMuted ? (
              <MicOff className="h-6 w-6" />
            ) : (
              <Mic className="h-6 w-6" />
            )}
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

  return (
    <div className="min-h-dvh bg-gradient-to-b from-muted/40 to-background">
      <div className="mx-auto max-w-2xl px-4 py-8 md:py-12">
        <div className="mb-6 flex items-center gap-2 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1 rounded-full border bg-background px-2.5 py-1">
            <Sparkles className="h-3 w-3" /> Demo
          </span>
          {agent.organization_name && (
            <span className="inline-flex items-center gap-1">
              <Building2 className="h-3 w-3" /> {agent.organization_name}
            </span>
          )}
        </div>

        <Card className="overflow-hidden" data-demo-visualizer={visualizer}>
          <CardHeader className="pb-3">
            <CardTitle className="text-2xl leading-tight">
              {agent.name}
            </CardTitle>
            {agent.tone && (
              <p className="text-xs text-muted-foreground">
                Tone: {agent.tone}
              </p>
            )}
          </CardHeader>
          <CardContent className="space-y-6">
            {(() => {
              const desc =
                agent.public_description?.trim() ||
                agent.mission?.trim() ||
                agent.persona?.trim() ||
                null;
              return desc ? (
                <div className="rounded-lg border bg-muted/30 p-4">
                  <h3 className="mb-1 text-sm font-semibold">
                    About this agent
                  </h3>
                  <p className="whitespace-pre-wrap text-sm leading-relaxed text-muted-foreground">
                    {desc}
                  </p>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Try a live voice conversation with this demo agent. Demo calls
                  do not use platform credits, but this demo may have trial
                  limits.
                </p>
              );
            })()}
            <div
              className={`rounded-lg border p-4 text-sm ${
                demoCallLimitReached
                  ? "border-destructive/40 bg-destructive/5 text-destructive"
                  : "border-amber-200 bg-amber-50/70 text-amber-950"
              }`}
            >
              <p className="font-medium">
                {demoCallLimitReached
                  ? "This demo is currently unavailable"
                  : "Demo trial availability"}
              </p>
              {!demoCallLimitReached ? (
                <div className="mt-1 space-y-1 text-xs opacity-80">
                  {callsRemainingLabel ? (
                    <div>Calls: {callsRemainingLabel}</div>
                  ) : null}
                  {durationLabel ? <div>Duration: {durationLabel}</div> : null}
                </div>
              ) : null}
              {demoCallLimitReached ? (
                <p className="mt-2 text-xs">{DEMO_TRIAL_EXHAUSTED_MESSAGE}</p>
              ) : null}
            </div>
            {callError && (
              <div className="rounded-md border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
                {callError}
              </div>
            )}

            <Button
              size="lg"
              className="h-12 w-full text-base"
              onClick={handleStartCall}
              disabled={demoCallLimitReached}
            >
              <Mic className="mr-2 h-5 w-5" />
              {demoCallLimitReached
                ? "Demo unavailable"
                : `Talk to ${agent.name}`}
            </Button>
            <p className="text-center text-xs text-muted-foreground">
              You&apos;ll be asked to allow microphone access • Powered by 24x7
              AI
            </p>
          </CardContent>
        </Card>

        <p className="mt-6 text-center text-xs text-muted-foreground">
          Demo agents are for showcasing only.{" "}
          <Link href="/" className="underline underline-offset-4">
            Back to home
          </Link>
        </p>
      </div>
    </div>
  );
}
