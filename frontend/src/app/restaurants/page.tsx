import {
  IndustryPage,
  type IndustryPageContent,
} from "@/components/seo/industry-page";
import { createMarketingMetadata } from "@/lib/marketing-seo";

export const metadata = createMarketingMetadata({
  path: "/restaurant-order-taking",
  title: "AI Voice Agent for Restaurant Orders and Inquiries",
  description:
    "AI voice agent for restaurants that answers phone orders and reservation calls, handles menu and hours questions, and captures catering or party inquiries.",
  keywords: [
    "AI voice agent for restaurants",
    "restaurant phone ordering",
    "restaurant reservation calls",
    "restaurant answering service",
    "restaurant inquiry handling",
  ],
});

const content: IndustryPageContent = {
  slug: "restaurants",
  label: "RESTAURANTS",
  headline: "Every call answered, every table filled",
  subhead:
    "24x7 AI picks up mid-rush, after close, and on your day off. It takes reservations, captures party and catering requests with full details, and answers the questions callers always ask.",
  pains: [
    "Saturday at 7pm your line is busy and the caller books the place down the street.",
    "Your host is glued to the phone instead of greeting the guests already in the room.",
    "Party bookings and catering inquiries die in voicemail because nobody calls back fast enough.",
  ],
  outcomes: [
    {
      title: "Reservations taken mid-rush",
      description:
        "Date, time, party size, and contact captured on the call and handed to your team exactly as spoken.",
    },
    {
      title: "Party and catering requests, captured whole",
      description:
        "Headcount, occasion, budget hints, and callback number collected so big tables stop slipping away.",
    },
    {
      title: "Repeat questions answered instantly",
      description:
        "Hours, location, parking, dress code, and daily specials, answered from your info, day or night.",
    },
    {
      title: "Callbacks, never dead ends",
      description:
        "When a caller needs a person, the AI offers a callback and alerts your team with the full context.",
    },
  ],
  demoSlug: "verdi-table-restaurant",
  demoBlurb:
    "Try a live order or ask a menu question. Your version is trained on your menu, hours, and tables.",
  proof: {
    eyebrow: "THE LOCAL CALL, BY THE NUMBERS",
    title: "Your busiest minutes are when the phone matters most.",
    description:
      "Restaurant-specific benchmarks are still worth validating, so this page uses cross-industry call data as a directional signal, then keeps the promise concrete: answer, resolve, reserve, or capture the request.",
    points: [
      {
        value: "Up to 85%",
        label: "of callers who reach voicemail may not call back.",
      },
      {
        value: "56%",
        label: "of business callers speak with a person.",
      },
      {
        value: "42%",
        label: "of phone leads convert on the call.",
      },
    ],
    sourceNote:
      "Cross-industry directional benchmarks; restaurant-specific results should be validated in a pilot.",
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
      question: "What happens during a Friday night rush?",
      answer:
        "The agent picks up every call at once, so nobody hears a busy signal. Routine reservations and questions are handled on the spot; anything needing a human becomes a callback with full context.",
    },
    {
      question: "How do menu or hours changes reach the agent?",
      answer:
        "Tell us during setup and any time after. We update your services, hours, and specials with you, then run test calls until you approve how it sounds.",
    },
    {
      question: "How long does setup take?",
      answer:
        "We configure your number, reservation flow, hours, and FAQs with you on a setup call, run test calls until you approve, and go live, usually within 48 hours.",
    },
    {
      question: "What does it cost?",
      answer:
        "Plans start at $49/month and include up to 250 call minutes. Book a demo to see how an AI front desk fits your restaurant.",
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
      name: "AI Voice Agent for Restaurant Orders and Inquiries",
      item: "https://www.247ai.live/restaurant-order-taking",
    },
  ],
};

/** Restaurant vertical landing page (SEO: AI receptionist for restaurants). */
export default function RestaurantsPage() {
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
