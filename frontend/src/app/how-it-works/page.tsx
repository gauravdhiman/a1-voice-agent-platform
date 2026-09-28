import type { Metadata } from "next";

import { PlatformTourPage } from "@/components/tour/platform-tour-page";
import { createMarketingMetadata } from "@/lib/marketing-seo";

export const metadata: Metadata = createMarketingMetadata({
  path: "/how-it-works",
  title: "How it works: your AI front desk in five steps",
  description:
    "Create your voice agent in plain words, answer on your number and website, connect the tools you already use, and review every call. No coding required.",
  keywords: [
    "how AI voice agent works",
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
