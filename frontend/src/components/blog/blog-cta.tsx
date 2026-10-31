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
 * The button uses the public theme's --button / --button-ink CSS variables
 * (the same ones the homepage CTA button uses) so it renders correctly in
 * both day and night modes. These variables are provided by PublicThemeRoot.
 *
 * Usage in MDX:
 *   import { BlogCTA } from "@/components/blog/blog-cta";
 *   <BlogCTA />
 *   <BlogCTA title="..." description="..." buttonText="..." href="/request-demo" />
 */
export function BlogCTA({
  title = "Ready to never miss another call?",
  description = "24x7 AI answers every call on your business line, books appointments, and captures leads around the clock. Concierge setup, live in 48 hours, plans from $79/month.",
  buttonText = "See 24x7 AI in action",
  href = "/request-demo",
}: BlogCTAProps) {
  return (
    <div
      className="not-prose my-10 overflow-hidden rounded-2xl border p-8 text-center md:p-10"
      style={{
        borderColor: "color-mix(in srgb, var(--button) 25%, transparent)",
        background:
          "linear-gradient(to bottom right, color-mix(in srgb, var(--button) 10%, transparent), color-mix(in srgb, var(--button) 5%, transparent), transparent)",
      }}
    >
      <h3 className="text-2xl font-bold tracking-tight text-foreground md:text-3xl">
        {title}
      </h3>
      <p className="mx-auto mt-3 max-w-xl text-muted-foreground">{description}</p>
      <Link
        href={href}
        style={{ backgroundColor: "var(--button)", color: "var(--button-ink)" }}
        className="mt-6 inline-flex items-center justify-center rounded-full px-7 py-3 text-sm font-semibold shadow-sm transition hover:opacity-90"
      >
        {buttonText}
      </Link>
    </div>
  );
}
