import type { Metadata } from "next";
import Link from "next/link";
import { getAllPostMetas } from "@/lib/blog";
import { PublicThemeRoot } from "@/components/public-theme/public-theme-root";
import { PublicHeader } from "@/components/public-theme/public-header";
import { SiteFooter } from "@/components/public-theme/site-footer";

export const metadata: Metadata = {
  title: "24x7 AI Blog: AI Receptionist Tips for Small Business",
  description:
    "Practical tips on AI receptionists, missed calls, and phone automation for small businesses, from the 24x7 AI team.",
};

export default async function BlogIndexPage() {
  const posts = await getAllPostMetas();

  return (
    <PublicThemeRoot>
      <PublicHeader />
      <main className="mx-auto w-full max-w-3xl px-4 py-16 md:py-24">
        <p className="text-sm font-medium uppercase tracking-widest text-muted-foreground">
          24x7 AI blog
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-foreground md:text-4xl">
          Never miss a customer again
        </h1>
        <p className="mt-4 text-lg text-muted-foreground">
          Practical tips on AI receptionists, missed calls, and getting more
          business from the phone you already have.
        </p>

        <div className="mt-12 space-y-12 divide-y divide-border">
          {posts.map((post) => (
            <article key={post.slug}>
              {post.image ? (
                <Link
                  href={`/blog/${post.slug}`}
                  className="block overflow-hidden rounded-xl"
                >
                  <img
                    src={post.image}
                    alt={post.title}
                    loading="lazy"
                    className="aspect-video w-full object-cover transition-transform duration-300 hover:scale-[1.02]"
                  />
                </Link>
              ) : null}
              <p className="mt-4 text-sm text-muted-foreground">{post.date}</p>
              <Link href={`/blog/${post.slug}`}>
                <h2 className="mt-1 text-2xl font-semibold text-foreground hover:underline">
                  {post.title}
                </h2>
              </Link>
              <p className="mt-2 text-muted-foreground">{post.description}</p>
              <Link
                href={`/blog/${post.slug}`}
                className="mt-3 inline-block font-medium text-primary hover:underline"
              >
                Read more
              </Link>
            </article>
          ))}
        </div>
      </main>
      <SiteFooter />
    </PublicThemeRoot>
  );
}
