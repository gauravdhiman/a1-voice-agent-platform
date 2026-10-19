import Link from "next/link";

interface BlogCTAProps {
  title?: string;
  description?: string;
  buttonText?: string;
  href?: string;
}

/**
 * Reusable blog call-to-action card. Drop it at the end of a blog post
 * (or anywhere on the marketing site) to convert readers into demo requests.
 *
 * Usage in MDX:
 *   import { BlogCTA } from "@/components/blog/blog-cta";
 *   <BlogCTA />
 *   <BlogCTA title="..." description="..." buttonText="..." href="/request-demo" />
 */
export function BlogCTA({
  title = "Ready to never miss another call?",
  description = "24x7 AI answers every call on your business line, books appointments, and captures leads around the clock. Concierge setup, live in 48 hours, plans from $49/month.",
  buttonText = "See 24x7 AI in action",
  href = "/request-demo",
}: BlogCTAProps) {
  return (
    <div className="not-prose my-10 overflow-hidden rounded-2xl border border-primary/20 bg-gradient-to-br from-primary/10 via-primary/5 to-transparent p-8 text-center md:p-10">
      <h3 className="text-2xl font-bold tracking-tight text-foreground md:text-3xl">
        {title}
      </h3>
      <p className="mx-auto mt-3 max-w-xl text-muted-foreground">{description}</p>
      <Link
        href={href}
        className="mt-6 inline-flex items-center justify-center rounded-full bg-primary px-7 py-3 text-sm font-semibold text-primary-foreground shadow-sm transition hover:opacity-90"
      >
        {buttonText}
      </Link>
    </div>
  );
}
