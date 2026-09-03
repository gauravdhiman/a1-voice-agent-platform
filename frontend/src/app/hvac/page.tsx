import type { Metadata } from "next";
import {
  IndustryPage,
  type IndustryPageContent,
} from "@/components/seo/industry-page";
import { SITE_URL } from "@/lib/site-config";

export const metadata: Metadata = {
  title: "AI Receptionist for HVAC & Home Services",
  description:
    "Stop losing after-hours jobs to voicemail. 24x7 AI triages service calls, books jobs to your calendar, and flags emergencies — live in 48 hours.",
  alternates: { canonical: `${SITE_URL}/hvac` },
};

const content: IndustryPageContent = {
  slug: "hvac",
  headline: "Every service call answered, every job captured",
  subhead:
    "24x7 AI picks up when your techs are on roofs and your office is closed — triages the issue, books the job, and flags true emergencies to your on-call line.",
  pains: [
    "Emergency calls at 9pm go to voicemail while the customer calls your competitor.",
    "Your dispatcher spends the day re-typing requests instead of routing techs.",
    "Routine tune-up requests and true no-heat emergencies all sound the same on a message slip.",
  ],
  outcomes: [
    {
      title: "Service requests, captured completely",
      description:
        "Collects name, address, unit symptoms, and availability — then records it all in Google Sheets for dispatch.",
    },
    {
      title: "Urgent vs routine, triaged on the call",
      description:
        "Follows your escalation rules: routine tune-ups get booked, no-heat/no-cool calls get flagged to your team immediately.",
    },
    {
      title: "Jobs booked to your calendar",
      description:
        "Offers real windows, confirms the visit, and sends the customer a confirmation text.",
    },
    {
      title: "Callbacks, never dead ends",
      description:
        "When a caller needs a person, the AI offers a callback and alerts your team with the full context.",
    },
  ],
  demoSlug: "copper-ridge-service-request",
  demoName: "Jordan",
  demoBlurb:
    "Try the live demo: request HVAC service with Jordan and watch the request land in Sheets.",
  faqs: [
    {
      question: "Can it tell an emergency from a routine call?",
      answer:
        "Yes — you define the triage rules during setup (no-heat, gas smell, water leaks), and the agent follows them on every call, escalating emergencies to your on-call number.",
    },
    {
      question: "What happens when a caller needs a real person?",
      answer:
        "The agent offers to have your team call back, captures the number and reason, and alerts you instantly with the full context. Nothing falls into voicemail.",
    },
    {
      question: "How long does setup take?",
      answer:
        "We configure your number, service area, triage rules, and calendar with you on a setup call, run test calls until you approve, and go live — usually within 48 hours.",
    },
    {
      question: "What does it cost?",
      answer:
        "Pilot plans start at $79/mo with concierge setup included. You only move to a monthly plan once the pilot proves itself on your real calls.",
    },
  ],
};

/** HVAC vertical landing page (SEO: AI receptionist for contractors). */
export default function HvacPage() {
  return <IndustryPage content={content} />;
}
