import {
  IndustryPage,
  type IndustryPageContent,
} from "@/components/seo/industry-page";
import { createMarketingMetadata } from "@/lib/marketing-seo";

export const metadata = createMarketingMetadata({
  path: "/plumbing-service-requests",
  title: "AI Voice Agent for Plumbing Service Requests",
  description:
    "AI voice agent for plumbing businesses that answers emergency and routine service calls, captures address and urgency, checks service area, and routes the next step.",
  keywords: [
    "AI voice agent for plumbers",
    "plumbing service request calls",
    "plumbing answering service",
    "emergency plumbing call answering",
    "plumber lead capture",
  ],
});

const content: IndustryPageContent = {
  slug: "plumbing",
  label: "PLUMBING SERVICES",
  headline: "The crew is on a job. The next job still gets captured.",
  subhead:
    "24x7 AI answers burst-pipe, no-hot-water, and routine service calls, checks the service area, captures the details your dispatcher needs, and routes true urgency to a person.",
  pains: [
    "A homeowner with a leak reaches voicemail and calls the next plumber in the search results.",
    "Your dispatcher has to turn incomplete messages into a usable address, symptom, and time window.",
    "Urgent calls and routine requests arrive together, making it hard to know what needs attention first.",
  ],
  outcomes: [
    {
      title: "Emergency details, captured first",
      description:
        "Collects the address, problem, access details, and callback number before a human takes over.",
    },
    {
      title: "Service area checked on the call",
      description:
        "Uses your approved coverage rules so the team spends less time sorting out-of-area requests later.",
    },
    {
      title: "Routine work, ready for dispatch",
      description:
        "Captures fixture details, preferred timing, and the work requested so your team can book or follow up with context.",
    },
    {
      title: "Human escalation when it matters",
      description:
        "Follows your rules for gas smell, flooding, no water, and other urgent language without pretending to diagnose the problem.",
    },
  ],
  demoBlurb:
    "No public plumbing demo yet. Request this workflow and we will shape it from your service area, triage rules, and dispatch process.",
  proof: {
    eyebrow: "THE HOME-SERVICE CALL, BY THE NUMBERS",
    title: "The faster responder often gets the job.",
    description:
      "Plumbing shares the same high-intent call pattern as HVAC: a caller needs a clear next step quickly, and the safe first step is structured intake plus human escalation when needed.",
    points: [
      {
        value: "52%",
        label: "of home-services callers speak with a person.",
      },
      {
        value: "45%",
        label: "of home-services leads convert on the call.",
      },
      {
        value: "79%",
        label:
          "of home-services consumers say they will switch to a faster responder.",
      },
    ],
    sourceNote:
      "Directional averages from Invoca's 2026 home-services datasets, not a promise of your results.",
    sources: [
      {
        label: "Invoca home-services benchmarks",
        href: "https://www.invoca.com/reports/the-invoca-home-services-lead-conversion-benchmarks-report-2026",
      },
      {
        label: "Invoca buyer experience survey",
        href: "https://www.invoca.com/uk/reports/home-services-buyer-experience-report-2026",
      },
    ],
  },
  faqs: [
    {
      question: "Can it diagnose a plumbing emergency?",
      answer:
        "No. The first workflow should collect the facts you approve, follow your urgency rules, and escalate to a person or approved safety guidance. It should not pretend to diagnose or quote a final repair.",
    },
    {
      question: "What happens when the crew is already busy?",
      answer:
        "The agent captures the caller's details and offers the next approved step: a dispatch window, a callback, or immediate escalation for the rules you define.",
    },
    {
      question: "How long does setup take?",
      answer:
        "We configure your service area, intake questions, hours, escalation rules, and calendar or request log with you, then run test calls before going live.",
    },
    {
      question: "What does it cost?",
      answer:
        "Pilot plans start at $79/mo with concierge setup included. You only move to a monthly plan once the workflow proves itself on your real calls.",
    },
  ],
};

/** Plumbing vertical landing page (SEO: AI receptionist for plumbers). */
export default function PlumbingPage() {
  return <IndustryPage content={content} />;
}
