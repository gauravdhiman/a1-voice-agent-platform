import {
  IndustryPage,
  type IndustryPageContent,
} from "@/components/seo/industry-page";
import { createMarketingMetadata } from "@/lib/marketing-seo";

export const metadata = createMarketingMetadata({
  path: "/dental-appointment-booking",
  title: "AI Receptionist for Dental Appointment Booking",
  description:
    "AI receptionist for dental practices that answers patient calls, books cleanings and exams, captures new-patient details, and handles after-hours requests. Live in 48 hours.",
  keywords: [
    "AI receptionist for dentists",
    "dental appointment booking",
    "dental answering service",
    "new patient phone intake",
    "after-hours dental calls",
  ],
});

const content: IndustryPageContent = {
  slug: "dental",
  label: "DENTAL PRACTICES",
  headline: "Your dental practice, always answering",
  subhead:
    "24x7 AI picks up every patient call after hours, on weekends, and during busy Mondays. It books cleanings and exams to the calendar or scheduling system your practice uses, then confirms so fewer patients no-show.",
  pains: [
    "After-hours callers hear voicemail and book with the practice down the street.",
    "Your front desk spends mornings playing phone tag instead of caring for patients in chairs.",
    "A caller who cannot reach the front desk has no reason to wait for a callback before trying the next practice.",
  ],
  outcomes: [
    {
      title: "New-patient intake, handled",
      description:
        "Greets first-time callers, captures their details and reason for visit, and books them into the right chair time.",
    },
    {
      title: "Cleanings and exams, booked to your calendar",
      description:
        "Checks real availability, confirms the slot with the caller, and writes the event to the scheduling system your practice uses, such as Google Calendar or Microsoft Outlook.",
    },
    {
      title: "Questions answered instantly",
      description:
        "Hours, location, services, and insurance basics, answered from your business info, day or night.",
    },
    {
      title: "Callbacks, never dead ends",
      description:
        "When a caller needs a person, the AI offers a callback and alerts your team with the full context.",
    },
  ],
  demoSlug: "pleasant-pediatric-appointments",
  demoBlurb:
    "Try the live demo: book a dental visit and watch the example calendar update. In a real setup, we connect the workflow to the scheduling tools your practice already uses.",
  proof: {
    eyebrow: "THE HEALTHCARE CALL, BY THE NUMBERS",
    title: "The patient is already asking for the next step.",
    description:
      "Healthcare callers are often closer to booking than a simple call count suggests. Answering matters, but guiding the conversation to a safe appointment or callback matters more.",
    points: [
      {
        value: "54%",
        label: "of healthcare callers speak with a person.",
      },
      {
        value: "43%",
        label: "of answered healthcare calls are leads.",
      },
      {
        value: "45%",
        label: "of healthcare leads convert on the call.",
      },
    ],
    sourceNote:
      "Directional averages from Invoca's 2026 healthcare call dataset, not a promise of your results.",
    sources: [
      {
        label: "Invoca healthcare benchmarks",
        href: "https://www.invoca.com/reports/the-invoca-healthcare-lead-conversion-benchmarks-report-2026",
      },
    ],
  },
  faqs: [
    {
      question: "Do patients know they are talking to an AI?",
      answer:
        "The agent introduces itself as your practice's AI receptionist, answers within the scope you approve, and offers a human callback when the request needs your team.",
    },
    {
      question: "What happens when a caller needs a real person?",
      answer:
        "The agent offers to have your team call back, captures the number and reason, and sends your team the full context. Nothing falls into voicemail.",
    },
    {
      question: "How long does setup take?",
      answer:
        "We configure your number, calendar or scheduling system, hours, and services with you on a setup call, run test bookings until you approve, and go live, usually within 48 hours.",
    },
    {
      question: "What does it cost?",
      answer:
        "Plans start at $79/month and include up to 250 call minutes. Book a demo to see how an AI front desk fits your practice.",
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
      name: "AI Receptionist for Dental Appointment Booking",
      item: "https://www.247ai.live/dental-appointment-booking",
    },
  ],
};

/** Dental vertical landing page (SEO: AI receptionist for dentists). */
export default function DentalPage() {
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
