import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/providers";
import {
  ensureOpentelemetryIsInitialized,
  emitLog,
  emitMetric,
} from "@/lib/opentelemetry";
import {
  SITE_DESCRIPTION,
  SITE_NAME,
  SITE_SHARE_IMAGE,
  SITE_SHARE_IMAGE_ALT,
  SITE_TAGLINE,
  SITE_URL,
} from "@/lib/site-config";

// Initialize OpenTelemetry
ensureOpentelemetryIsInitialized();

// Emit a log and metric when the app starts
emitLog("Frontend application started", "INFO");
emitMetric("frontend.app.start", 1, { page: "layout" });

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const SITE_TITLE = `${SITE_NAME} - ${SITE_TAGLINE}`;

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  icons: {
    icon: [{ url: "/brand-mark.svg", type: "image/svg+xml", sizes: "any" }],
  },
  title: {
    default: SITE_TITLE,
    template: `%s - ${SITE_NAME}`,
  },
  description: SITE_DESCRIPTION,
  alternates: {
    canonical: SITE_URL,
  },
  openGraph: {
    type: "website",
    url: SITE_URL,
    siteName: SITE_NAME,
    title: SITE_TITLE,
    description: SITE_DESCRIPTION,
    locale: "en_US",
    images: [
      {
        url: SITE_SHARE_IMAGE,
        width: 1200,
        height: 630,
        alt: SITE_SHARE_IMAGE_ALT,
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: SITE_TITLE,
    description: SITE_DESCRIPTION,
    images: [SITE_SHARE_IMAGE],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
