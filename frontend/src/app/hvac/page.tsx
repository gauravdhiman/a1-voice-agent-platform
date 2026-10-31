import {
  IndustryPage,
  type IndustryPageContent,
} from "@/components/seo/industry-page";
import { createMarketingMetadata } from "@/lib/marketing-seo";

export const metadata = createMarketingMetadata({
  path: "/hvac-service-call-answering",
  title: "AI Receptionist for HVAC Service Calls",
  description:
    "AI receptionist for HVAC and home-service businesses that answers service calls, captures job details, follows emergency triage rules, and books or routes the next step.",
  keywords: [
    "AI receptionist for HVAC",
    "HVAC answering service",
    "HVAC service call booking",
    "home-services call answering",
    "HVAC lead capture",
  ],
});

const content: IndustryPageContent = {
  slug: "hvac",
  label: "HVAC AND HOME SERVICES",
  headline: "Every service call answered, every job captured",
  subhead:
    "24x7 AI picks up when your techs are on roofs and your office is closed. It triages the issue, books the job, and flags true emergencies to your team.",
  pains: [
    "Emergency calls at 9pm go to voicemail while the customer calls your competitor.",
    "Your dispatcher spends the day re-typing requests instead of routing techs.",
    "Routine tune-up requests and true no-heat emergencies all sound the same on a message slip.",
  ],
  outcomes: [
    {
      title: "Service requests, captured completely",
      description:
        "Collects name, address, unit symptoms, and availability, then sends the request to the system your team uses, such as a CRM, dispatch platform, or spreadsheet.",
    },
    {
      title: "Urgent vs routine, triaged on the call",
      description:
        "Follows your escalation rules: routine tune-ups get booked, no-heat/no-cool calls get flagged to your team immediately.",
    },
    {
      title: "Jobs booked to your calendar",
      description:
        "Offers real windows, confirms the visit with the caller, and records the booking in your calendar.",
    },
    {
      title: "Callbacks, never dead ends",
      description:
        "When a caller needs a person, the AI offers a callback and alerts your team with the full context.",
    },
  ],
  demoSlug: "copper-ridge-service-request",
  demoBlurb:
    "Try the live demo: request HVAC service and watch the example request land in a spreadsheet. In a real setup, we connect it to the tools your dispatch team already uses.",
  proof: {
    eyebrow: "THE HOME-SERVICE CALL, BY THE NUMBERS",
    title: "Speed is part of the service.",
    description:
      "When the office is closed or the crew is out, the first response can decide who gets the job. The agent handles the first safe step, then escalates what needs a person.",
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
        value: "55%",
        label: "of home-services businesses do not ask leads to book the job.",
      },
    ],
    sourceNote:
      "Directional averages from Invoca's 2026 home-services call dataset, not a promise of your results.",
    sources: [
      {
        label: "Invoca home-services benchmarks",
        href: "https://www.invoca.com/reports/the-invoca-home-services-lead-conversion-benchmarks-report-2026",
      },
    ],
  },
  faqs: [
    {
      question: "Can it tell an emergency from a routine call?",
      answer:
        "Yes. You define the triage rules during setup, such as no-heat, gas smell, or water leaks, and the agent follows them on every call, flagging emergencies for your team.",
    },
    {
      question: "What happens when a caller needs a real person?",
      answer:
        "The agent offers to have your team call back, captures the number and reason, and sends your team the full context. Nothing falls into voicemail.",
    },
    {
      question: "How long does setup take?",
      answer:
        "We configure your number, service area, triage rules, and calendar or dispatch system with you on a setup call, run test calls until you approve, and go live, usually within 48 hours.",
    },
    {
      question: "What does it cost?",
      answer:
        "Plans start at $79/month and include up to 250 call minutes. Book a demo to see how an AI front desk fits your business.",
    },
  ],
};

const breadcrumbJsonLd = {
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  itemListElement: [
    {
      "@type": "ListItem",
      position: 1,
      name: "Home",
      item: "https://www.247ai.live",
    },
    {
      "@type": "ListItem",
      position: 2,
      name: "AI Receptionist for HVAC Service Calls",
      item: "https://www.247ai.live/hvac-service-call-answering",
    },
  ],
};

/** HVAC vertical landing page (SEO: AI receptionist for contractors). */
export default function HvacPage() {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify(breadcrumbJsonLd),
        }}
      />
      <IndustryPage content={content} />
    </>
  );
}
