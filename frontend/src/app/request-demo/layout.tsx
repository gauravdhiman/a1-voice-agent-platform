import type { Metadata } from "next";

import { createMarketingMetadata } from "@/lib/marketing-seo";

export const metadata: Metadata = createMarketingMetadata({
  path: "/request-demo",
  title: "Request an AI Voice Agent Demo",
  description:
    "Tell us how your business handles calls. We will shape an AI voice agent around your services, scheduling system, CRM, and customer workflow.",
  keywords: [
    "AI voice agent demo",
    "AI receptionist demo",
    "business phone automation demo",
    "custom AI call answering",
  ],
});

export default function RequestDemoLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return children;
}
