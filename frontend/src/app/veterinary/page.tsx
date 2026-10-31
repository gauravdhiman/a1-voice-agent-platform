import {
  IndustryPage,
  type IndustryPageContent,
} from "@/components/seo/industry-page";
import { createMarketingMetadata } from "@/lib/marketing-seo";

export const metadata = createMarketingMetadata({
  path: "/veterinary-appointment-booking",
  title: "AI Receptionist for Veterinary Appointment Booking",
  description:
    "AI receptionist for veterinary clinics that answers routine calls, captures pet and visit details, books appointment requests, and escalates urgent language safely.",
  keywords: [
    "AI receptionist for veterinary clinics",
    "veterinary appointment booking",
    "vet answering service",
    "veterinary call handling",
    "veterinary client intake",
  ],
});

const content: IndustryPageContent = {
  slug: "veterinary clinics",
  label: "VETERINARY CLINICS",
  headline: "Keep the front desk present for every pet parent.",
  subhead:
    "24x7 AI handles routine appointment and clinic questions, captures the pet and visit details, and gets urgent language to your team without pretending to diagnose.",
  pains: [
    "The phone rings while the team is helping a pet in the exam room or checking in another family.",
    "Routine appointment requests and urgent concerns compete for the same front-desk attention.",
    "Incomplete messages make callbacks harder when the clinic finally has a quiet minute.",
  ],
  outcomes: [
    {
      title: "Routine visits, requested clearly",
      description:
        "Captures pet name, visit type, preferred timing, and contact details for a booking or callback.",
    },
    {
      title: "Clinic information, always available",
      description:
        "Answers approved questions about hours, location, services, preparation, and refill-request process.",
    },
    {
      title: "New-client intake, organized",
      description:
        "Collects the basic details your team needs before a first visit without asking for unnecessary clinical information.",
    },
    {
      title: "Urgent language, escalated safely",
      description:
        "Uses your approved escalation rules and directs callers to a human or emergency guidance instead of diagnosing.",
    },
  ],
  demoBlurb:
    "No public veterinary demo yet. Request this workflow and we will shape it around your appointment types, clinic FAQs, and escalation rules.",
  proof: {
    eyebrow: "THE CONSUMER-SERVICE CALL, BY THE NUMBERS",
    title: "Routine care should not wait for a quiet front desk.",
    description:
      "Veterinary clinics sit inside a broader consumer-services benchmark that includes vet services. It is directional evidence for a bounded intake and booking workflow, not a claim about every clinic.",
    points: [
      {
        value: "60%",
        label: "of consumer-services callers speak with a person.",
      },
      {
        value: "34%",
        label: "of answered consumer-services calls are leads.",
      },
      {
        value: "40%",
        label: "of consumer-services leads convert on the call.",
      },
    ],
    sourceNote:
      "Directional consumer-services averages; Invoca's category includes veterinary services alongside other local services.",
    sources: [
      {
        label: "Invoca consumer-services benchmarks",
        href: "https://www.invoca.com/reports/the-invoca-consumer-services-lead-conversion-benchmarks-report-2026",
      },
    ],
  },
  faqs: [
    {
      question: "Can it give medical advice or diagnose an animal?",
      answer:
        "No. The safe first version handles approved clinic information, routine intake, appointment requests, and human or emergency escalation. Clinical advice stays with your veterinary team.",
    },
    {
      question: "Can urgent calls reach a human?",
      answer:
        "Yes. You define the language and hours that require a person, and the agent captures the caller's number and context before following your approved handoff.",
    },
    {
      question: "How long does setup take?",
      answer:
        "We configure your appointment types, clinic information, hours, and escalation rules with you, then run test calls before going live.",
    },
    {
      question: "What does it cost?",
      answer:
        "Plans start at $79/month and include up to 250 call minutes. Book a demo to see how an AI front desk fits your clinic.",
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
      name: "AI Receptionist for Veterinary Appointment Booking",
      item: "https://www.247ai.live/veterinary-appointment-booking",
    },
  ],
};

/** Veterinary vertical landing page (SEO: AI receptionist for vet clinics). */
export default function VeterinaryPage() {
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
