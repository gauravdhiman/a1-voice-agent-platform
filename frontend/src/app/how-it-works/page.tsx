import type { Metadata } from "next";

import { PlatformTourPage } from "@/components/tour/platform-tour-page";
import { createMarketingMetadata } from "@/lib/marketing-seo";

export const metadata: Metadata = createMarketingMetadata({
  path: "/how-it-works",
  title: "How it works: your AI front desk in five steps",
  description:
    "See how a 24x7 AI phone assistant answers your number and website, handles questions, bookings and orders, and records callback requests. No phone menus or hold music.",
  keywords: [
    "how AI phone assistant works",
    "AI front desk setup",
    "AI call answering for small business",
    "voice agent integrations",
    "call recordings and logs",
  ],
});

/** Public guided tour: what the 24x7 AI platform does, in business terms. */
export default function HowItWorksPage() {
  return <PlatformTourPage />;
}
