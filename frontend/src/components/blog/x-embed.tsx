"use client";

import { useEffect, useRef } from "react";

declare global {
  interface Window {
    twttr?: { widgets?: { load: (el?: HTMLElement) => void } };
  }
}

interface XEmbedProps {
  statusUrl: string;
  caption?: string;
}

/**
 * Reusable X (Twitter) post embed for blog posts. Loads
 * platform.twitter.com/widgets.js once and renders the post in place,
 * so readers can play an attached video without leaving the page.
 * No sign-in is involved: this is X's public embed, and the post URL
 * below the embed is a plain link for readers whose browser blocks
 * the script.
 *
 * Usage in MDX:
 *   import { XEmbed } from "@/components/blog/x-embed";
 *   <XEmbed statusUrl="https://x.com/blocks/status/2113721026324615173" caption="..." />
 */
export function XEmbed({ statusUrl, caption }: XEmbedProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const render = () => {
      if (window.twttr?.widgets && containerRef.current) {
        window.twttr.widgets.load(containerRef.current);
      }
    };
    if (window.twttr?.widgets) {
      render();
      return;
    }
    const scriptSrc = "https://platform.twitter.com/widgets.js";
    const existing = document.querySelector(`script[src="${scriptSrc}"]`);
    if (existing) {
      existing.addEventListener("load", render);
      return () => existing.removeEventListener("load", render);
    }
    const script = document.createElement("script");
    script.src = scriptSrc;
    script.async = true;
    script.onload = render;
    document.body.appendChild(script);
  }, []);

  // The embed blockquote uses the twitter.com form of the URL, which X
  // serves as the same post. The visible link keeps the x.com URL.
  const embedUrl = statusUrl.replace("x.com", "twitter.com");

  return (
    <figure className="not-prose my-10">
      <div ref={containerRef}>
        <blockquote className="twitter-tweet">
          <a href={embedUrl}>View this post on X</a>
        </blockquote>
      </div>
      {caption ? (
        <figcaption className="mt-3 text-center text-sm text-muted-foreground">
          {caption}
        </figcaption>
      ) : null}
      <p className="mt-2 text-center text-sm">
        <a
          href={statusUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="font-medium text-primary hover:underline"
        >
          Watch the demo on X
        </a>
      </p>
    </figure>
  );
}
