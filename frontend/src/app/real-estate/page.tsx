import {
  IndustryPage,
  type IndustryPageContent,
} from "@/components/seo/industry-page";
import { createMarketingMetadata } from "@/lib/marketing-seo";

export const metadata = createMarketingMetadata({
  path: "/real-estate-lead-capture",
  title: "AI Voice Agent for Real Estate Lead Capture",
  description:
    "AI voice agent for real estate teams that answers buyer and seller calls, captures lead details, answers approved listing questions, and requests or books viewings.",
  keywords: [
    "AI voice agent for real estate",
    "real estate lead capture",
    "real estate answering service",
    "real estate viewing booking",
    "buyer and seller lead qualification",
  ],
});

const content: IndustryPageContent = {
  slug: "real-estate",
  label: "REAL ESTATE",
  headline: "Every enquiry answered, every viewing booked",
  subhead:
    "24x7 AI picks up when you are at a closing, on a viewing, or off for the day. It answers listing questions, requests viewings through your scheduling system, and captures every buyer and seller detail for follow-up.",
  pains: [
    "A hot buyer calls during your viewing and reaches voicemail. By callback time they have another agent.",
    "Weekend enquiries pile up as texts you answer late on Sunday night.",
    "New listings generate calls faster than any one person can qualify them.",
  ],
  outcomes: [
    {
      title: "Viewings booked where your team works",
      description:
        "Offers real windows, confirms the visit with the caller, and records the booking in the calendar or scheduling system your team uses.",
    },
    {
      title: "Buyer and seller details, captured whole",
      description:
        "Name, number, timeline, area, and budget range collected on the call, ready for your follow-up.",
    },
    {
      title: "Listing questions answered instantly",
      description:
        "Price, beds and baths, location, open-home times, answered from your listing info, day or night.",
    },
    {
      title: "Callbacks, never dead ends",
      description:
        "When a caller needs a person, the AI offers a callback and alerts you with the full context.",
    },
  ],
  demoSlug: "copper-ridge-service-request",
  demoName: "Jordan",
  demoBlurb:
    "No public real-estate demo yet. Request the workflow and we will shape it around your listings, viewing calendar, and qualification questions.",
  proof: {
    eyebrow: "THE LOCAL ENQUIRY, BY THE NUMBERS",
    title: "A missed enquiry is a lead with nowhere to go.",
    description:
      "Real estate is a fast-response business. The first version should focus on one safe outcome: capture intent, answer approved listing questions, and book or request the next human step.",
    points: [
      {
        value: "Up to 85%",
        label: "of unanswered callers may not call back.",
      },
      {
        value: "42%",
        label: "of phone leads convert on the call across industries.",
      },
      {
        value: "9%",
        label:
          "was CallRail's missed-call rate for real estate in its SMB dataset.",
      },
    ],
    sourceNote:
      "Directional benchmarks from a broad call dataset. Validate the response-time story with local agents before building a dedicated demo.",
    sources: [
      {
        label: "CallRail SMB benchmark",
        href: "https://www.callrail.com/blog/callrail-releases-benchmark-report",
      },
      {
        label: "Invoca 2026 benchmarks",
        href: "https://www.invoca.com/reports/the-invoca-lead-conversion-benchmarks-report-2026",
      },
    ],
  },
  faqs: [
    {
      question: "Can it tell a hot buyer from a casual browser?",
      answer:
        "Yes. You define what counts during setup, such as timeline and budget range, and the agent captures those details on every call so you can prioritize follow-up.",
    },
    {
      question: "How do new listings reach the agent?",
      answer:
        "Share your listing details or source of truth any time. We update prices, open-home times, and availability with you, then run test calls until you approve how it sounds.",
    },
    {
      question: "How long does setup take?",
      answer:
        "We configure your number, calendar, qualification questions, and after-hours rules with you on a setup call, run test calls until you approve, and go live, usually within 48 hours.",
    },
    {
      question: "What does it cost?",
      answer:
        "Pilot plans start at $79/mo with concierge setup included. You only move to a monthly plan once the pilot proves itself on your real calls.",
    },
  ],
};

/** Real estate vertical landing page (SEO: AI receptionist for realtors). */
export default function RealEstatePage() {
  return <IndustryPage content={content} />;
}
