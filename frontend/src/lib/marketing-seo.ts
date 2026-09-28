import type { Metadata } from "next";

import {
  SITE_NAME,
  SITE_SHARE_IMAGE,
  SITE_SHARE_IMAGE_ALT,
  SITE_URL,
} from "@/lib/site-config";

interface MarketingMetadataOptions {
  /** Canonical public path, including the leading slash. */
  path: string;
  /** Search result title before the site-wide brand suffix is applied. */
  title: string;
  /** Search result description written for the page's primary intent. */
  description: string;
  /** Search-intent phrases covered by the page content. */
  keywords: string[];
}

/** Build consistent metadata for public marketing and industry pages. */
export function createMarketingMetadata({
  path,
  title,
  description,
  keywords,
}: MarketingMetadataOptions): Metadata {
  const url = `${SITE_URL}${path}`;
  const brandedTitle = `${title} - ${SITE_NAME}`;

  return {
    title,
    description,
    keywords,
    alternates: { canonical: url },
    openGraph: {
      type: "website",
      url,
      siteName: SITE_NAME,
      title: brandedTitle,
      description,
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
      title: brandedTitle,
      description,
      images: [SITE_SHARE_IMAGE],
    },
  };
}
