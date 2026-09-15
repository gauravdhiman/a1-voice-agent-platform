"use client";

import * as React from "react";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import {
  Loader2,
  Mic,
  MicOff,
  PhoneOff,
  ArrowLeft,
  Sparkles,
  Building2,
  ExternalLink,
  ShieldAlert,
  CheckCircle2,
  Clock3,
  Database,
} from "lucide-react";
import { AgentAudioRadialV4 } from "@/components/agents-ui/agent-audio-radial-v4";
import { AgentAudioVisualizerBarV4 } from "@/components/agents-ui/agent-audio-visualizer-livekit-bar-v4";
import { resolveDemoVisualizer } from "@/components/agents-ui/demo-visualizer-config";
import type { LevelMediaManager } from "@/lib/level-media-manager";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PublicThemeRoot } from "@/components/public-theme/public-theme-root";
import { PublicHeader } from "@/components/public-theme/public-header";
import pt from "@/components/public-theme/public-theme.module.css";
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
import { trackEvent } from "@/lib/analytics/posthog";
import {
  DEMO_TRIAL_EXHAUSTED_MESSAGE,
  formatDemoCallsRemaining,
  formatDemoDuration,
  isDemoCallLimitReached,
} from "@/lib/demo-call-limits";

const GMAIL_ALIAS_HELP_URL =
  "https://support.google.com/mail/answer/22370?hl=en";

/** Example opener lines per demo, so first-time callers know what to say. */
const TRY_SCRIPTS: Record<string, { lines: string[]; note: string }> = {
  "pleasant-pediatric-appointments": {
    lines: [
      "I need a cleaning for my daughter next Thursday.",
      "Do you take new patients?",
    ],
    note: "Alex will check real availability and book it.",
  },
  "copper-ridge-service-request": {
    lines: [
      "My AC is blowing warm air upstairs.",
      "Can someone come out Thursday morning?",
    ],
    note: "Jordan will capture the full request for dispatch.",
  },
};

function tryScriptForSlug(slug: string): { lines: string[]; note: string } {
  return (
    TRY_SCRIPTS[slug] ?? {
      lines: ["Hello, I need some help.", "Can you walk me through it?"],
      note: "The agent will guide the conversation from there.",
    }
  );
}

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
  return (
    <PublicThemeRoot>
      <DemoAgentView />
    </PublicThemeRoot>
  );
}

function DemoAgentView() {
  const params = useParams<{ slug: string }>();
  const slug = params.slug;
  const router = useRouter();
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
  const [hasAcknowledgedDemoPolicy, setHasAcknowledgedDemoPolicy] =
    React.useState(false);
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
  const connectionAttemptRef = React.useRef(0);
  const receiptTokenRef = React.useRef<string | null>(null);
  const callConnectedRef = React.useRef(false);
  const outcomeNavigatedRef = React.useRef(false);

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
    connectionAttemptRef.current += 1;
    const client = pipecatRef.current;
    pipecatRef.current = null;
    await disconnectPipecatVoiceCall(client);
    setAgentTrack(null);
    setLocalTrack(null);
  }, []);

  const showOutcome = React.useCallback(() => {
    if (outcomeNavigatedRef.current) return;
    outcomeNavigatedRef.current = true;
    const receiptToken = receiptTokenRef.current;
    if (receiptToken) {
      trackEvent("demo_completed", { demo_slug: slug });
      router.replace(
        `/demo/${encodeURIComponent(slug)}/outcome?token=${encodeURIComponent(receiptToken)}`,
      );
      return;
    }
    setCallState("ended");
  }, [router, slug]);

  const handleStartCall = React.useCallback(async () => {
    if (!agent) {
      return;
    }
    if (!hasAcknowledgedDemoPolicy) {
      setCallError(
        "Please acknowledge the public-demo notice and use dummy information before starting the call.",
      );
      return;
    }
    if (isDemoCallLimitReached(agent.demo_calls_remaining)) {
      setCallError(DEMO_TRIAL_EXHAUSTED_MESSAGE);
      return;
    }
    const attempt = ++connectionAttemptRef.current;
    const isCurrentAttempt = () => connectionAttemptRef.current === attempt;
    setCallError(null);
    setCallState("connecting");
    callConnectedRef.current = false;
    outcomeNavigatedRef.current = false;
    try {
      const { token, wsUrl, receiptToken, demo_calls_remaining } =
        await demoPublicService.getCallToken(slug);
      if (!isCurrentAttempt()) return;
      receiptTokenRef.current = receiptToken;
      if (typeof demo_calls_remaining === "number") {
        setAgent((current) =>
          current ? { ...current, demo_calls_remaining } : current,
        );
      }
      const client = await connectPipecatVoiceCall(token, wsUrl, {
        onClientCreated: (createdClient) => {
          if (isCurrentAttempt()) {
            pipecatRef.current = createdClient;
          } else {
            void disconnectPipecatVoiceCall(createdClient);
          }
        },
        onConnected: () => {
          callConnectedRef.current = true;
        },
        onSpeakingChange: ({ isAgentSpeaking, isUserSpeaking }) => {
          if (!isCurrentAttempt()) return;
          setIsAgentSpeaking(isAgentSpeaking);
          setIsUserSpeaking(isUserSpeaking);
        },
        onBotAudioTrack: (track) => {
          if (!isCurrentAttempt()) return;
          setAgentTrack(track);
        },
        onLocalAudioTrack: (track) => {
          if (!isCurrentAttempt()) return;
          setLocalTrack(track);
        },
        onLevelManager: (mgr) => {
          if (!isCurrentAttempt()) return;
          levelManagerRef.current = mgr as unknown as LevelMediaManager;
        },
        onDisconnected: () => {
          if (!isCurrentAttempt()) return;
          callConnectedRef.current = false;
          setAgentTrack(null);
          setLocalTrack(null);
          showOutcome();
        },
        onError: (err) => {
          if (!isCurrentAttempt()) return;
          setAgentTrack(null);
          setLocalTrack(null);
          // Pipecat can report a server-enforced duration timeout or a
          // transport failure through onError without emitting a separate
          // onDisconnected event. Once the call connected, the visitor still
          // has a valid receipt token and should see the outcome page.
          if (callConnectedRef.current && receiptTokenRef.current) {
            callConnectedRef.current = false;
            setIsAgentSpeaking(false);
            setIsUserSpeaking(false);
            showOutcome();
            return;
          }
          setCallError(getPublicVoiceCallErrorMessage(err) || err.message);
          receiptTokenRef.current = null;
          setCallState("idle");
        },
      });
      if (!isCurrentAttempt()) return;
      pipecatRef.current = client;
      // Some transports resolve connect() without invoking the callback
      // synchronously. A resolved client is nevertheless an active call for
      // purposes of routing post-connect failures to its receipt.
      callConnectedRef.current = true;
      trackEvent("demo_played", { demo_slug: slug });
      setCallState("connected");
    } catch (e) {
      if (!isCurrentAttempt()) return;
      callConnectedRef.current = false;
      const msg = e instanceof Error ? e.message : "Failed to start call";
      setCallError(getPublicVoiceCallErrorMessage(e) || msg);
      setAgentTrack(null);
      setLocalTrack(null);
      setCallState("idle");
    }
  }, [agent, hasAcknowledgedDemoPolicy, showOutcome, slug]);

  const handleHangUp = React.useCallback(async () => {
    await disconnect();
    showOutcome();
    setIsAgentSpeaking(false);
    setIsUserSpeaking(false);
  }, [disconnect, showOutcome]);

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
  const description =
    agent.public_description?.trim() ||
    agent.mission?.trim() ||
    agent.persona?.trim() ||
    "Try a live voice conversation with this demo agent.";

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
    <div className={pt.page}>
      <div className={pt.glow} aria-hidden="true" />
      <PublicHeader />

      <div className="relative mx-auto flex min-h-dvh w-full max-w-6xl flex-col px-4 py-5 sm:px-6 lg:px-8 lg:py-7">
        <div className="flex items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <span
              className={pt.smallDetail}
              style={{ fontSize: 10, letterSpacing: "0.12em" }}
            >
              INTERACTIVE VOICE DEMO
            </span>
            {agent.organization_name && (
              <span className="inline-flex items-center gap-1.5 rounded-full border border-transparent px-2 py-1">
                <Building2 className="h-3.5 w-3.5" />
                {agent.organization_name}
              </span>
            )}
          </div>
          <Link
            href="/"
            className="hidden items-center gap-1 text-xs font-medium text-muted-foreground transition hover:text-foreground sm:inline-flex"
          >
            Back to home
            <ArrowLeft className="h-3.5 w-3.5" />
          </Link>
        </div>

        <main className="grid flex-1 items-start gap-7 py-7 lg:grid-cols-[minmax(0,1fr)_minmax(390px,460px)] lg:items-center lg:gap-16 lg:py-10">
          <section className="order-2 max-w-2xl lg:order-1">
            <div className="max-w-xl">
              <p className={pt.eyebrow}>INTERACTIVE VOICE DEMO</p>
              <h1
                className={pt.title}
                style={{ fontSize: "clamp(40px, 5vw, 64px)", marginTop: 20 }}
              >
                Try {agent.name} <span>live.</span>
              </h1>
              <p className="mt-5 hidden max-w-lg text-base leading-7 text-muted-foreground sm:text-lg lg:block">
                {description}
              </p>
              {agent.tone && (
                <p className="mt-3 text-xs font-medium text-muted-foreground">
                  Conversation style: {agent.tone}
                </p>
              )}
            </div>

            <div className="mt-8 grid max-w-xl gap-3 sm:grid-cols-2">
              <div className={`${pt.panel} p-4`}>
                <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-100 text-indigo-700 dark:bg-indigo-950/70 dark:text-indigo-300">
                  <Mic className="h-4 w-4" aria-hidden="true" />
                </div>
                <p className="mt-4 text-sm font-semibold">Talk naturally</p>
                <p className="mt-1 text-sm leading-6 text-muted-foreground">
                  Explain what you need in your own words and let the agent
                  guide the conversation.
                </p>
              </div>
              <div className={`${pt.panel} p-4`}>
                <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-cyan-100 text-cyan-700 dark:bg-cyan-950/70 dark:text-cyan-300">
                  <Database className="h-4 w-4" aria-hidden="true" />
                </div>
                <p className="mt-4 text-sm font-semibold">
                  See the handoff happen
                </p>
                <p className="mt-1 text-sm leading-6 text-muted-foreground">
                  The agent completes its configured follow-up so you can see
                  the outcome for yourself.
                </p>
              </div>
            </div>

            <div className={`${pt.panel} mt-3 max-w-xl p-4`}>
              <p
                className={pt.smallDetail}
                style={{ fontSize: 10, letterSpacing: "0.12em" }}
              >
                NOT SURE WHAT TO SAY? TRY ONE OF THESE LINES
              </p>
              <ul className="mt-3 space-y-2">
                {tryScriptForSlug(slug).lines.map((line) => (
                  <li
                    key={line}
                    className="rounded-xl border px-3 py-2.5 text-sm leading-6"
                    style={{
                      borderColor: "var(--line)",
                      color: "var(--ink)",
                    }}
                  >
                    &ldquo;{line}&rdquo;
                  </li>
                ))}
              </ul>
              <p className="mt-3 text-xs leading-5 text-muted-foreground">
                {tryScriptForSlug(slug).note}
              </p>
            </div>

            <div className="mt-7 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-muted-foreground">
              {callsRemainingLabel ? (
                <span className="inline-flex items-center gap-1.5">
                  <Sparkles className="h-3.5 w-3.5 text-primary" />
                  {callsRemainingLabel}
                </span>
              ) : null}
              {durationLabel ? (
                <span className="inline-flex items-center gap-1.5">
                  <Clock3 className="h-3.5 w-3.5 text-primary" />
                  {durationLabel}
                </span>
              ) : null}
              <span className="inline-flex items-center gap-1.5">
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
                No platform credits used
              </span>
            </div>
          </section>

          <aside className="order-1 w-full lg:order-2 lg:sticky lg:top-8">
            <Card
              className="gap-0 overflow-hidden py-0"
              data-demo-visualizer={visualizer}
            >
              <CardHeader className="border-b border-border px-5 pb-5 pt-5 sm:px-6">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-[0.68rem] font-semibold uppercase tracking-[0.2em] text-primary">
                    Start here
                  </span>
                  <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1 text-[0.68rem] font-semibold text-emerald-700 dark:text-emerald-300">
                    <span
                      className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500"
                      aria-hidden="true"
                    />
                    Live voice
                  </span>
                </div>
                <CardTitle
                  id="start-demo-title"
                  className="mt-4 text-2xl tracking-tight"
                >
                  Talk to {agent.name}
                </CardTitle>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">
                  <span className="hidden lg:inline">
                    Take the role of a prospective customer and let the agent
                    handle the next step.
                  </span>
                  <span className="lg:hidden">{description}</span>
                </p>
              </CardHeader>
              <CardContent className="space-y-4 px-5 py-5 sm:px-6">
                {demoCallLimitReached ? (
                  <div className="rounded-xl border border-destructive/40 bg-destructive/5 p-3.5 text-sm text-destructive">
                    <p className="font-semibold">
                      This demo is currently unavailable
                    </p>
                    <p className="mt-1 text-xs leading-5">
                      {DEMO_TRIAL_EXHAUSTED_MESSAGE}
                    </p>
                  </div>
                ) : null}

                <section
                  aria-labelledby="demo-data-notice-title"
                  className="rounded-2xl border border-amber-300/80 bg-amber-50/80 p-4 text-amber-950 shadow-sm dark:border-amber-900/70 dark:bg-amber-950/30 dark:text-amber-50"
                >
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-amber-200/70 text-amber-800 dark:bg-amber-900/70 dark:text-amber-200">
                      <ShieldAlert className="h-4 w-4" aria-hidden="true" />
                    </div>
                    <div className="min-w-0">
                      <h3
                        id="demo-data-notice-title"
                        className="text-sm font-semibold tracking-tight"
                      >
                        Public demo — use fictional details
                      </h3>
                      <p className="mt-1.5 text-xs leading-5 text-amber-900/80 dark:text-amber-100/80">
                        This agent writes the information you share to a public
                        demo data store that other visitors may see. Use dummy
                        details only—never real names, email addresses, phone
                        numbers, physical addresses, or confidential
                        information.
                      </p>
                      <p className="mt-2 text-xs leading-5 text-amber-900/80 dark:text-amber-100/80">
                        If you provide an email, we&apos;ll try to send a
                        confirmation. Use a secondary inbox or Gmail alias such
                        as{" "}
                        <code className="break-words rounded bg-amber-100 px-1 py-0.5 text-[0.8em] dark:bg-amber-900/70">
                          yourname+demo@gmail.com
                        </code>
                        .
                      </p>
                      <a
                        href={GMAIL_ALIAS_HELP_URL}
                        target="_blank"
                        rel="noreferrer"
                        className="mt-2 inline-flex items-center gap-1.5 text-xs font-semibold text-amber-800 underline decoration-amber-500/60 underline-offset-4 transition hover:text-amber-950 dark:text-amber-200 dark:hover:text-white"
                      >
                        Learn how Gmail aliases work
                        <ExternalLink
                          className="h-3.5 w-3.5"
                          aria-hidden="true"
                        />
                      </a>
                    </div>
                  </div>

                  <label
                    htmlFor="demo-data-policy"
                    className="mt-3 flex cursor-pointer items-start gap-2.5 border-t border-amber-300/60 pt-3 text-xs font-semibold leading-5 dark:border-amber-800/70"
                  >
                    <input
                      id="demo-data-policy"
                      type="checkbox"
                      checked={hasAcknowledgedDemoPolicy}
                      onChange={(event) =>
                        setHasAcknowledgedDemoPolicy(event.target.checked)
                      }
                      className="mt-0.5 h-4 w-4 shrink-0 rounded border-amber-400 text-amber-700 accent-amber-700 focus:ring-2 focus:ring-amber-500 focus:ring-offset-2 focus:ring-offset-amber-50 dark:focus:ring-offset-amber-950"
                    />
                    <span>
                      I understand this is a public demo and will use dummy
                      information.
                    </span>
                  </label>
                </section>

                {callError && (
                  <div className="rounded-xl border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
                    {callError}
                  </div>
                )}

                <Button
                  size="lg"
                  className="h-12 w-full text-base shadow-lg shadow-primary/15"
                  onClick={handleStartCall}
                  disabled={demoCallLimitReached || !hasAcknowledgedDemoPolicy}
                >
                  <Mic className="mr-2 h-5 w-5" />
                  {demoCallLimitReached
                    ? "Demo unavailable"
                    : `Talk to ${agent.name}`}
                </Button>
                {!demoCallLimitReached && !hasAcknowledgedDemoPolicy ? (
                  <p className="-mt-1 text-center text-xs text-muted-foreground">
                    Check the notice to enable the call.
                  </p>
                ) : null}
                <p className="text-center text-[0.7rem] leading-5 text-muted-foreground">
                  Free to try · No signup needed · Microphone access required
                </p>
              </CardContent>
            </Card>
          </aside>
        </main>

        <footer className="flex items-center justify-center gap-1.5 pt-2 text-center text-xs text-muted-foreground">
          <span>Demo agents are for showcasing only.</span>
          <Link href="/" className="underline underline-offset-4">
            Back to home
          </Link>
        </footer>
      </div>
    </div>
  );
}
