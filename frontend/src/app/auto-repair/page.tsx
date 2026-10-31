import {
  IndustryPage,
  type IndustryPageContent,
} from "@/components/seo/industry-page";
import { createMarketingMetadata } from "@/lib/marketing-seo";
import { PLANS, formatMonthlyPrice } from "@/lib/pricing/plans";

export const metadata = createMarketingMetadata({
  path: "/auto-repair-service-booking",
  title: "AI Receptionist for Auto Repair Service Booking",
  description:
    "AI receptionist for auto repair shops that answers service calls, captures vehicle details, requests appointments, and organizes estimate callbacks while advisors are busy.",
  keywords: [
    "AI receptionist for auto repair shops",
    "auto repair service booking",
    "auto repair answering service",
    "auto repair estimate calls",
    "automotive lead capture",
  ],
});

const content: IndustryPageContent = {
  slug: "auto repair",
  label: "AUTO REPAIR SHOPS",
  headline: "Turn the service call into scheduled work.",
  subhead:
    "24x7 AI answers while technicians are under a hood, captures the vehicle and service details, and moves the caller to an appointment request, estimate callback, or human handoff.",
  pains: [
    "A check-engine or brake call arrives while the service advisor is helping the customer at the counter.",
    "Incomplete voicemails leave the team guessing about the vehicle, service needed, and best callback time.",
    "Routine service questions and urgent safety concerns need different next steps.",
  ],
  outcomes: [
    {
      title: "Vehicle details, captured once",
      description:
        "Collects year, make, model, mileage, service need, and contact details so the advisor starts with context.",
    },
    {
      title: "Service appointments requested",
      description:
        "Offers approved appointment windows or records a structured request for the shop's scheduling system.",
    },
    {
      title: "Estimate callbacks, organized",
      description:
        "Captures the work requested and preferred callback window without promising a diagnosis or final price.",
    },
    {
      title: "Safety-sensitive handoff",
      description:
        "Recognizes approved urgency language and routes it to a person instead of improvising mechanical advice.",
    },
  ],
  demoBlurb:
    "No public auto-repair demo yet. Request this workflow and we will shape it around your services, bays, hours, and advisor process.",
  proof: {
    eyebrow: "THE AUTOMOTIVE CALL, BY THE NUMBERS",
    title: "The service lead is already on the phone.",
    description:
      "Automotive calls show a strong lead signal, which makes service intake a better first workflow than trying to automate vehicle sales or mechanical diagnosis.",
    points: [
      {
        value: "58%",
        label: "of automotive callers speak with a person.",
      },
      {
        value: "53%",
        label: "of answered automotive calls are leads.",
      },
      {
        value: "45%",
        label: "of automotive leads convert on the call.",
      },
    ],
    sourceNote:
      "Directional averages from Invoca's 2026 automotive call dataset; the first workflow should stay focused on service intake.",
    sources: [
      {
        label: "Invoca automotive benchmarks",
        href: "https://www.invoca.com/reports/the-invoca-automotive-lead-conversion-benchmarks-report-2026",
      },
    ],
  },
  faqs: [
    {
      question: "Can it diagnose the car or give a final quote?",
      answer:
        "No. The safe first version captures the symptom and vehicle details, answers approved shop FAQs, and requests an appointment or advisor callback. Diagnosis and final quotes stay with your team.",
    },
    {
      question: "Can it handle service and estimate requests differently?",
      answer:
        "Yes. You define the intake questions and next step for routine service, estimate requests, status questions, and calls that need an advisor.",
    },
    {
      question: "How long does setup take?",
      answer:
        "We configure your services, hours, appointment windows, approved FAQs, and handoff rules with you, then run test calls before going live.",
    },
    {
      question: "What does it cost?",
      answer:
        `Plans start at ${formatMonthlyPrice(PLANS.STARTER.monthlyUSD)} and include up to ${PLANS.STARTER.approximateMinutes} call minutes. Book a demo to see how an AI front desk fits your shop.`,
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
      name: "AI Receptionist for Auto Repair Service Booking",
      item: "https://www.247ai.live/auto-repair-service-booking",
    },
  ],
};

/** Auto repair vertical landing page (SEO: AI receptionist for auto repair). */
export default function AutoRepairPage() {
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
