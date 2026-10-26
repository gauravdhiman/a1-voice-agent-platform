import fs from "fs";
import path from "path";

export interface BlogPostMeta {
  title: string;
  description: string;
  date: string;
  slug: string;
  image?: string;
}

// Note: process.cwd() is the frontend/ directory at build time.
const POSTS_DIR = path.join(process.cwd(), "src", "content", "blog");

/** Slugs derived from MDX filenames in src/content/blog. */
export function getPostSlugs(): string[] {
  if (!fs.existsSync(POSTS_DIR)) return [];
  return fs
    .readdirSync(POSTS_DIR)
    .filter((file) => file.endsWith(".mdx"))
    .map((file) => file.replace(/\.mdx$/, ""))
    .sort();
}

/** Per-post metadata exported from the MDX module. */
export async function getPostMeta(slug: string): Promise<BlogPostMeta> {
  const mod = await import(`@/content/blog/${slug}.mdx`);
  return mod.metadata as BlogPostMeta;
}

/** All posts, newest first. */
export async function getAllPostMetas(): Promise<BlogPostMeta[]> {
  const slugs = getPostSlugs();
  const metas = await Promise.all(
    slugs.map(async (slug) => ({ ...(await getPostMeta(slug)), slug }))
  );
  return metas.sort((a, b) => (a.date < b.date ? 1 : -1));
}
