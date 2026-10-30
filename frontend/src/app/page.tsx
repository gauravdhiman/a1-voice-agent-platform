import type { Metadata } from "next";

import { HomePage } from "@/components/home/home-page";
import { createMarketingMetadata } from "@/lib/marketing-seo";

export const metadata: Metadata = createMarketingMetadata({
  path: "",
  title: "AI Receptionist for Small Business | 24/7 AI Phone Answering - 24x7 AI",
  description:
    "24x7 AI answers every call on your business line 24/7: books appointments, answers questions, captures leads. Concierge setup, live in 48 hours. Plans from $79/mo.",
  keywords: [
    "AI voice agents for small business",
    "AI receptionist",
    "AI call answering",
    "business phone automation",
    "missed-call solution",
  ],
});

const softwareApplicationJsonLd = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: "24x7 AI",
  applicationCategory: "BusinessApplication",
  operatingSystem: "Web",
  url: "https://www.247ai.live",
  description:
    "24x7 AI answers every call on your business line 24/7: books appointments, answers questions, captures leads.",
  offers: {
    "@type": "Offer",
    price: "79",
    priceCurrency: "USD",
    description:
      "Monthly plans from $79/month, including up to 250 call minutes.",
  },
};

/** Public homepage: business-led particle storytelling and concierge demo entry. */
export default function LandingPage() {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify(softwareApplicationJsonLd),
        }}
      />
      <HomePage />
    </>
  );
}
