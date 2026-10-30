"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

export interface BlogFaqItem {
  q: string;
  a: string;
}

interface BlogFaqProps {
  items: BlogFaqItem[];
}

/**
 * Accessible FAQ accordion for blog posts. Renders one open-at-a-time
 * accordion styled to the site theme, plus FAQPage JSON-LD for SEO
 * rich results. Content stays in the DOM so AI answer engines can read it.
 *
 * Usage in MDX:
 *   import { BlogFaq } from "@/components/blog/blog-faq";
 *   <BlogFaq
 *     items={[
 *       { q: "How fast does it answer?", a: "In about four seconds." },
 *       { q: "What does it cost?", a: "Plans start at $79/month." },
 *     ]}
 *   />
 */
export function BlogFaq({ items }: BlogFaqProps) {
  const [openIndex, setOpenIndex] = useState<number | null>(0);

  const faqJsonLd = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: items.map((item) => ({
      "@type": "Question",
      name: item.q,
      acceptedAnswer: {
        "@type": "Answer",
        text: item.a,
      },
    })),
  };

  return (
    <div className="not-prose my-8">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqJsonLd) }}
      />
      <div className="divide-y divide-border overflow-hidden rounded-xl border border-border">
        {items.map((item, i) => {
          const open = openIndex === i;
          const buttonId = `blog-faq-button-${i}`;
          const panelId = `blog-faq-panel-${i}`;
          return (
            <div key={i} className={open ? "bg-muted/25" : undefined}>
              <button
                type="button"
                id={buttonId}
                aria-expanded={open}
                aria-controls={panelId}
                onClick={() => setOpenIndex(open ? null : i)}
                className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left"
              >
                <span className="font-medium text-foreground">{item.q}</span>
                <ChevronDown
                  aria-hidden="true"
                  className={cn(
                    "h-5 w-5 shrink-0 text-muted-foreground transition-transform duration-200",
                    open && "rotate-180",
                  )}
                />
              </button>
              {open ? (
                <div
                  id={panelId}
                  role="region"
                  aria-labelledby={buttonId}
                  className="px-5 pb-5 text-muted-foreground"
                >
                  {item.a}
                </div>
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}
