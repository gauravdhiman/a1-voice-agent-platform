import type { ComponentType, ReactNode } from "react";

interface MDXComponentsMap {
  [key: string]: ComponentType<{ children?: ReactNode }>;
}

// Minimal MDX component mapping for the marketing blog.
// Blog post pages provide their own article layout around the MDX content.
export function useMDXComponents(
  components: MDXComponentsMap
): MDXComponentsMap {
  return {
    ...components,
  };
}
