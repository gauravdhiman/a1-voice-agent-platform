import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getPostSlugs, getPostMeta } from "@/lib/blog";
import { PublicThemeRoot } from "@/components/public-theme/public-theme-root";
import { PublicHeader } from "@/components/public-theme/public-header";
import { PublicFooter } from "@/components/public-theme/public-footer";

export async function generateStaticParams() {
  return getPostSlugs().map((slug) => ({ slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  try {
    const meta = await getPostMeta(slug);
    return {
      title: `${meta.title} - 24x7 AI`,
      description: meta.description,
    };
  } catch {
    return { title: "Post not found - 24x7 AI" };
  }
}

export default async function BlogPostPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  if (!getPostSlugs().includes(slug)) {
    notFound();
  }
  const meta = await getPostMeta(slug);
  const { default: Post } = await import(`@/content/blog/${slug}.mdx`);

  return (
    <PublicThemeRoot>
      <PublicHeader />
      <main className="mx-auto w-full max-w-3xl px-4 py-16 md:py-24">
        <Link
          href="/blog"
          className="text-sm font-medium text-primary hover:underline"
        >
          Back to blog
        </Link>
        <h1 className="mt-4 text-3xl font-bold tracking-tight text-foreground md:text-4xl">
          {meta.title}
        </h1>
        <p className="mt-3 text-sm text-muted-foreground">{meta.date}</p>
        <article className="prose dark:prose-invert mt-8 max-w-none">
          <Post />
        </article>
      </main>
      <PublicFooter />
    </PublicThemeRoot>
  );
}
