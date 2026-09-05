"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export interface BasicMarkdownRendererProps {
  /** Markdown source to render without the heavyweight Mermaid integration. */
  content: string;
  className?: string;
}

/**
 * Renders ordinary Markdown/GFM without importing Mermaid.
 *
 * Agent skill content is primarily prose and tables. Keeping this renderer
 * separate prevents the large Mermaid dependency from entering the Skills
 * route's initial development compilation; the full renderer remains available
 * for surfaces that explicitly need Mermaid diagrams.
 */
export function BasicMarkdownRenderer({
  content,
  className,
}: BasicMarkdownRendererProps) {
  return (
    <div className={className}>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  );
}
