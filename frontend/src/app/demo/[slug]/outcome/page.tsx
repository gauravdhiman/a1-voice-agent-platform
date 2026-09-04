"use client";

import * as React from "react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import {
  AlertCircle,
  ArrowLeft,
  Building2,
  CalendarDays,
  CheckCircle2,
  ClipboardCheck,
  Clock3,
  ContactRound,
  ExternalLink,
  Loader2,
  MailCheck,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Wrench,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DemoFeedback } from "@/components/demo/demo-feedback";
import { OutcomeInterest } from "@/components/demo/outcome-interest";
import {
  demoPublicService,
  type DemoOutcome,
  type DemoOutcomeAction,
} from "@/services/demo-public-service";

const FIELD_LABELS: Record<string, string> = {
  caller_name: "Name",
  caller_email: "Email",
  caller_phone: "Phone",
  service_needed: "Service needed",
  issue_summary: "Issue summary",
  property_address: "Service address",
  urgency: "Urgency",
  preferred_callback_window: "Preferred callback",
  purpose: "Appointment type",
  start_time: "Start time",
  duration_minutes: "Duration",
  notes: "Notes",
};

function labelForField(name: string): string {
  return (
    FIELD_LABELS[name] ||
    name
      .split("_")
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(" ")
  );
}

function valueForField(name: string, value: string | number | boolean | null): string {
  if (value === null || value === "") return "—";
  if (name === "duration_minutes" && typeof value === "number") {
    return `${value} minutes`;
  }
  if (name === "start_time" && typeof value === "string") {
    const parsed = new Date(value);
    if (!Number.isNaN(parsed.getTime())) {
      return new Intl.DateTimeFormat("en-US", {
        dateStyle: "medium",
        timeStyle: "short",
      }).format(parsed);
    }
  }
  return String(value);
}

function providerLabel(action: DemoOutcomeAction): string {
  if (action.provider === "google_sheets") return "Google Sheets";
  if (action.provider === "hubspot") return "HubSpot CRM";
  if (action.provider === "gmail") return "Gmail";
  if (action.provider === "resend") return "Resend";
  return "Google Calendar";
}

function actionTitle(action: DemoOutcomeAction): string {
  if (action.action_type === "email_delivery") {
    if (action.status === "succeeded") return "Email confirmation sent";
    if (action.status === "pending") return "Email confirmation awaiting confirmation";
    return "Email confirmation not completed";
  }
  if (action.action_type === "lead_capture") {
    if (action.status === "succeeded") return "Service inquiry captured";
    if (action.status === "pending") return "Service inquiry awaiting confirmation";
    return "Service inquiry details captured";
  }
  if (action.status === "succeeded") return "Appointment booking confirmed";
  if (action.status === "pending") return "Appointment booking awaiting confirmation";
  return "Appointment details captured";
}

function outcomeHeading(outcome: DemoOutcome): string {
  if (outcome.status === "completed") {
    return `See what ${outcome.agent_name} completed.`;
  }
  if (outcome.status === "needs_attention") {
    return `Review what ${outcome.agent_name} captured.`;
  }
  return `Review the outcome from ${outcome.agent_name}.`;
}

function actionIcon(action: DemoOutcomeAction) {
  if (action.action_type === "lead_capture") return ContactRound;
  if (action.action_type === "email_delivery") return MailCheck;
  return CalendarDays;
}

function safeHttpsUrl(value: unknown): string | null {
  if (typeof value !== "string" || !value.trim()) return null;
  try {
    const parsed = new URL(value.trim());
    if (
      parsed.protocol !== "https:" ||
      !parsed.hostname ||
      parsed.username ||
      parsed.password
    ) {
      return null;
    }
    return parsed.toString();
  } catch {
    return null;
  }
}

function statusCopy(outcome: DemoOutcome): {
  title: string;
  description: string;
  tone: string;
} {
  if (outcome.status === "completed") {
    return {
      title: "The handoff is complete",
      description:
        "Here is the exact information the agent captured and the provider it updated.",
      tone: "border-emerald-200 bg-emerald-50/90 text-emerald-950",
    };
  }
  if (outcome.status === "needs_attention") {
    return {
      title: "The conversation needs attention",
      description:
        "The receipt shows what was captured and where the workflow stopped. Nothing is presented as complete unless the provider confirmed it.",
      tone: "border-amber-200 bg-amber-50/90 text-amber-950",
    };
  }
  return {
    title: "No provider action was completed",
    description:
      "The call ended before the agent confirmed a lead or appointment mutation. Try the demo again and let the agent finish the handoff.",
      tone: "border-slate-200 bg-white/85 text-slate-800",
  };
}

function OutcomeActionCard({ action }: { action: DemoOutcomeAction }) {
  const Icon = actionIcon(action);
  const isSuccess = action.status === "succeeded";
  const isPending = action.status === "pending";
  const configuredResultUrl = isSuccess
    ? action.action_type === "email_delivery"
      ? null
      : safeHttpsUrl(action.public_result_url)
    : null;
  const resultUrl = configuredResultUrl;
  const resultLinkLabel = `Open ${providerLabel(action)} result`;
  const capturedFieldEntries = Object.entries(action.captured_fields);
  return (
    <Card className="overflow-hidden border-slate-200/90 bg-white/95 shadow-xl shadow-slate-900/5 backdrop-blur">
      <CardHeader className="border-b border-slate-200/80 bg-slate-50/70 pb-4">
        <div className="flex items-start gap-3">
          <div
            className={`mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${
              isSuccess
                ? "bg-emerald-100 text-emerald-700"
                : isPending
                  ? "bg-amber-100 text-amber-700"
                  : "bg-rose-100 text-rose-700"
            }`}
          >
            <Icon className="h-5 w-5" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <CardTitle className="text-lg text-slate-950">{actionTitle(action)}</CardTitle>
              <span
                className={`rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] ${
                  isSuccess
                    ? "bg-emerald-100 text-emerald-700"
                    : isPending
                      ? "bg-amber-100 text-amber-700"
                      : "bg-rose-100 text-rose-700"
                }`}
              >
                {isSuccess ? "Confirmed" : isPending ? "Needs confirmation" : "Not completed"}
              </span>
            </div>
            <p className="mt-1 text-sm text-slate-600">
              Destination: <span className="font-medium text-slate-950">{providerLabel(action)}</span>
            </p>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-5 p-5 text-slate-900">
        {capturedFieldEntries.length > 0 ? (
          <div>
            <p className="mb-3 text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
              Captured details
            </p>
            <dl className="grid gap-3 sm:grid-cols-2">
              {capturedFieldEntries.map(([name, value]) => (
                <div key={name} className="rounded-xl border border-slate-200/80 bg-slate-50/55 px-3 py-2.5">
                  <dt className="text-xs text-slate-500">{labelForField(name)}</dt>
                  <dd className="mt-1 whitespace-pre-wrap break-words text-sm font-medium text-slate-900">
                    {valueForField(name, value)}
                  </dd>
                </div>
              ))}
            </dl>
          </div>
        ) : null}

        <div className="border-t pt-4">
          <div className="flex items-start gap-2 text-sm">
            {isSuccess ? (
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
            ) : (
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
            )}
            <div>
              <p className="font-medium">Provider result</p>
              <p className="mt-0.5 text-slate-600">
                {String(action.provider_result.message ||
                  (isSuccess ? "The provider confirmed the mutation." : "The provider did not confirm the mutation."))}
              </p>
              {resultUrl && (
                <Button
                  asChild
                  size="sm"
                  variant="outline"
                  className="mt-3 border-slate-300 bg-white text-slate-700 hover:bg-slate-50 hover:text-slate-950"
                >
                  <a
                    href={resultUrl}
                    target="_blank"
                    rel="noreferrer"
                  >
                    <ExternalLink className="mr-1.5 h-3.5 w-3.5" />
                    {resultLinkLabel}
                  </a>
                </Button>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function DemoOutcomePage() {
  const params = useParams<{ slug: string }>();
  const slug = params.slug;
  const searchParams = useSearchParams();
  const receiptToken = searchParams.get("token");
  const [outcome, setOutcome] = React.useState<DemoOutcome | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [attempt, setAttempt] = React.useState(0);

  const loadOutcome = React.useCallback(async () => {
    if (!receiptToken) {
      setError("This receipt link is missing its secure session token.");
      setLoading(false);
      return;
    }
    try {
      const next = await demoPublicService.getDemoOutcome(slug, receiptToken);
      setOutcome(next);
      setError(null);
      if (next.status === "no_action" && attempt < 4) {
        setAttempt((current) => current + 1);
      }
    } catch (nextError) {
      setError(
        nextError instanceof Error
          ? nextError.message
          : "Demo outcome is unavailable",
      );
    } finally {
      setLoading(false);
    }
  }, [attempt, receiptToken, slug]);

  React.useEffect(() => {
    void loadOutcome();
  }, [loadOutcome]);

  React.useEffect(() => {
    if (!outcome || outcome.status !== "no_action" || attempt === 0 || attempt > 4) {
      return;
    }
    const timer = window.setTimeout(() => void loadOutcome(), 1200);
    return () => window.clearTimeout(timer);
  }, [attempt, loadOutcome, outcome]);

  if (loading && !outcome) {
    return (
      <div className="relative flex min-h-dvh items-center justify-center overflow-hidden bg-gradient-to-br from-slate-50 via-white to-sky-50/70 p-6 text-slate-950">
        <div aria-hidden="true" className="pointer-events-none absolute -left-24 -top-32 h-80 w-80 rounded-full bg-sky-200/50 blur-3xl" />
        <div aria-hidden="true" className="pointer-events-none absolute -bottom-40 -right-32 h-96 w-96 rounded-full bg-indigo-200/40 blur-3xl" />
        <div className="relative flex items-center gap-3 rounded-full border border-slate-200/80 bg-white/80 px-4 py-3 text-sm text-slate-600 shadow-sm backdrop-blur">
          <Loader2 className="h-5 w-5 animate-spin text-primary" />
          Preparing your private demo receipt…
        </div>
      </div>
    );
  }

  if (error && !outcome) {
    return (
      <div className="relative flex min-h-dvh items-center justify-center overflow-hidden bg-gradient-to-br from-slate-50 via-white to-sky-50/70 p-6 text-center text-slate-950">
        <div aria-hidden="true" className="pointer-events-none absolute -left-24 -top-32 h-80 w-80 rounded-full bg-sky-200/50 blur-3xl" />
        <div aria-hidden="true" className="pointer-events-none absolute -bottom-40 -right-32 h-96 w-96 rounded-full bg-indigo-200/40 blur-3xl" />
        <div className="relative flex max-w-md flex-col items-center gap-5">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-rose-100 text-rose-700 shadow-sm">
            <AlertCircle className="h-7 w-7" />
          </div>
          <div>
            <h1 className="text-xl font-semibold">Receipt unavailable</h1>
            <p className="mt-2 text-sm text-slate-600">{error}</p>
          </div>
          <Button asChild variant="outline" className="border-slate-300 bg-white text-slate-700 hover:bg-slate-50 hover:text-slate-950">
            <Link href={`/demo/${encodeURIComponent(slug)}`}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to demo
            </Link>
          </Button>
        </div>
      </div>
    );
  }

  if (!outcome) return null;
  const copy = statusCopy(outcome);
  return (
    <main className="relative min-h-dvh overflow-hidden bg-gradient-to-br from-slate-50 via-white to-sky-50/70 text-slate-950">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -left-24 -top-32 h-80 w-80 rounded-full bg-sky-200/50 blur-3xl"
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -right-32 top-24 h-96 w-96 rounded-full bg-indigo-200/40 blur-3xl"
      />

      <div className="relative mx-auto max-w-5xl px-4 py-5 sm:px-6 lg:px-8 lg:py-7">
        <header className="flex items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-2 text-xs text-slate-600">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-slate-200/80 bg-white/80 px-3 py-1.5 font-medium shadow-sm backdrop-blur">
              <Sparkles className="h-3.5 w-3.5 text-primary" />
              24x7 AI <span className="font-normal text-slate-500">/ Demo</span>
            </span>
            {outcome.organization_name && (
              <span className="inline-flex items-center gap-1.5 rounded-full px-2 py-1 text-slate-600">
                <Building2 className="h-3.5 w-3.5" />
                {outcome.organization_name}
              </span>
            )}
          </div>
          <Link
            href={`/demo/${encodeURIComponent(slug)}`}
            className="hidden items-center gap-1 text-xs font-medium text-slate-600 transition hover:text-slate-950 sm:inline-flex"
          >
            Back to demo
            <ArrowLeft className="h-3.5 w-3.5" />
          </Link>
        </header>

        <div className="mt-8 flex items-center justify-between gap-4 sm:mt-12">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-primary">Demo outcome</p>
            <h1 className="mt-4 max-w-3xl text-3xl font-semibold tracking-[-0.045em] text-slate-950 sm:text-5xl">
              {outcomeHeading(outcome)}
            </h1>
            <p className="mt-4 max-w-2xl text-base leading-7 text-slate-600 sm:text-lg">
              {copy.description}
            </p>
          </div>
          <div className="hidden shrink-0 items-center gap-2 rounded-full border border-slate-200 bg-white/70 px-3 py-1.5 text-xs text-slate-600 shadow-sm backdrop-blur sm:inline-flex">
            <ShieldCheck className="h-3.5 w-3.5 text-primary" />
            Private session receipt
          </div>
        </div>

        <div className={`mt-8 rounded-2xl border p-5 shadow-sm ${copy.tone}`}>
          <div className="flex items-start gap-3">
            {outcome.status === "completed" ? (
              <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0" />
            ) : outcome.status === "needs_attention" ? (
              <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" />
            ) : (
              <ClipboardCheck className="mt-0.5 h-5 w-5 shrink-0" />
            )}
            <div>
              <p className="font-semibold">{copy.title}</p>
              <p className="mt-1 text-sm opacity-80">
                {outcome.organization_name || "Demo business"}
                {outcome.actions.length ? ` · ${outcome.actions.length} workflow result${outcome.actions.length === 1 ? "" : "s"}` : ""}
              </p>
            </div>
          </div>
        </div>

        <div className="mt-5 grid gap-5 md:grid-cols-2">
          <div className="rounded-2xl border border-slate-200/90 bg-white/95 p-5 shadow-sm">
            <DemoFeedback demoSlug={slug} />
          </div>
          <div className="rounded-2xl border border-slate-200/90 bg-white/95 p-5 shadow-sm">
            <OutcomeInterest demoSlug={slug} />
          </div>
        </div>

        {outcome.actions.length ? (
          <details className="mt-5 rounded-2xl border border-slate-200/90 bg-white/95 shadow-sm">
            <summary className="cursor-pointer p-5 text-sm font-medium text-slate-700">
              Call details — what the agent saved and where
            </summary>
            <div className="space-y-5 px-5 pb-5">
              {outcome.actions.map((action) => (
                <OutcomeActionCard key={action.id} action={action} />
              ))}
            </div>
          </details>
        ) : (
          <Card className="mt-5 border-slate-200/90 bg-white/95 text-slate-950 shadow-xl shadow-slate-900/5">
            <CardContent className="flex flex-col items-center px-6 py-12 text-center">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-sky-100 text-sky-700">
                <Wrench className="h-7 w-7" />
              </div>
              <h2 className="mt-5 text-lg font-semibold">The agent did not save a workflow yet</h2>
              <p className="mt-2 max-w-md text-sm leading-6 text-slate-600">
                Let the agent confirm the final details before ending the call. This page updates only from a provider-backed action.
              </p>
              <Button asChild className="mt-6 shadow-lg shadow-primary/15">
                <Link href={`/demo/${encodeURIComponent(slug)}`}>
                  <RefreshCw className="mr-2 h-4 w-4" />
                  Try the conversation again
                </Link>
              </Button>
            </CardContent>
          </Card>
        )}

        <div className="mt-8 flex flex-col gap-3 text-xs text-slate-500 sm:flex-row sm:items-center sm:justify-between">
          <span className="inline-flex items-center gap-1.5"><Clock3 className="h-3.5 w-3.5" /> Receipt expires after 24 hours</span>
          <span>Provider-backed result · No login required</span>
        </div>
      </div>
    </main>
  );
}
