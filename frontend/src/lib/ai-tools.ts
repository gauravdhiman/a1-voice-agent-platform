import {
  TOOLS,
  TOOL_CATEGORIES,
  type Tool,
  type ToolCategory,
} from "@/content/ai-tools/tools";

/** All directory categories in display order. */
export function getCategories(): ToolCategory[] {
  return TOOL_CATEGORIES;
}

/** One category by slug, or undefined. */
export function getCategory(slug: string): ToolCategory | undefined {
  return TOOL_CATEGORIES.find((category) => category.slug === slug);
}

/** Every tool in the directory, in display order. */
export function getAllTools(): Tool[] {
  return TOOLS;
}

/** Tools in a category, featured entries first. */
export function getToolsByCategory(categorySlug: string): Tool[] {
  return TOOLS.filter((tool) => tool.category === categorySlug).sort(
    (a, b) => Number(b.featured ?? false) - Number(a.featured ?? false),
  );
}

/** One tool by category + slug, or undefined. */
export function getTool(
  categorySlug: string,
  toolSlug: string,
): Tool | undefined {
  return TOOLS.find(
    (tool) => tool.category === categorySlug && tool.slug === toolSlug,
  );
}

export type { Tool, ToolCategory };
