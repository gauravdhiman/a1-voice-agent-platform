"use client";

/**
 * Shared markdown renderer for skill content, skill files, and agent system
 * prompt previews.
 *
 * Wraps react-markdown + remark-gfm and adds first-class Mermaid rendering:
 *
 *   - fenced code blocks tagged `mermaid` are intercepted at the `code`
 *     component level and rendered as inline SVG via the Mermaid library.
 *   - theme (light/dark) is read from the resolved theme on `<html>` and
 *     re-applied to Mermaid when it flips, so diagrams stay legible in both
 *     modes.
 *   - if Mermaid throws (bad syntax, library not loaded, SSR attempt), the
 *     source is rendered as a fenced `<pre><code>` block so the rest of the
 *     SKILL.md is still readable instead of crashing the whole page.
 *   - the component is a Next.js Client Component because Mermaid needs
 *     `window`; Mermaid is dynamically imported inside an effect so the SSR
 *     pass never tries to evaluate it.
 *
 * Why a custom code component (vs. `remark-mermaid`):
 *   - `remark-mermaid` is unmaintained and pulls Mermaid into the SSR pass
 *     in some setups, which crashes on `window is not defined`.
 *   - intercepting at the `code` component keeps Mermaid entirely client
 *     side, matches how our app already runs react-markdown, and avoids one
 *     extra dependency.
 *
 * @example
 * ```tsx
 * <MarkdownRenderer content={skill.content} className="prose prose-sm" />
 * ```
 */

import React, { useEffect, useRef, useState } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

/**
 * Detect the resolved theme by looking at the class on `<html>`. The theme
 * context writes either `light` or `dark` here, so this works regardless
 * of whether the user picked a theme explicitly or set "system".
 */
function readResolvedTheme(): "light" | "dark" {
  if (typeof document === "undefined") return "light";
  const cls = document.documentElement.classList;
  if (cls.contains("dark")) return "dark";
  return "light";
}

interface MermaidBlockProps {
  /** Raw mermaid source (the contents of the fenced block, no language tag). */
  code: string;
}

/**
 * Renders a single Mermaid diagram to SVG.
 *
 * Mermaid is lazy-loaded on first render so the bundle hit only happens when a
 * SKILL.md actually contains a diagram. The Mermaid library is configured
 * with `startOnLoad: false` (we drive rendering manually) and a security
 * level of "strict" so untrusted skill authors can't inject clickable script
 * tags via diagram labels.
 *
 * On any error we fall back to the raw source inside a fenced code block,
 * prefixed with a small caption explaining what failed. This keeps the rest
 * of the SKILL.md useful when one diagram is broken.
 */
function MermaidBlock({ code }: MermaidBlockProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [renderError, setRenderError] = useState<string | null>(null);
  const [svg, setSvg] = useState<string | null>(null);
  const [renderKey, setRenderKey] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function render() {
      try {
        // Dynamic import keeps mermaid out of the SSR bundle and the initial
        // client payload until a diagram is actually requested.
        const mermaidMod = await import("mermaid");
        const mermaid = mermaidMod.default;

        mermaid.initialize({
          startOnLoad: false,
          theme: readResolvedTheme() === "dark" ? "dark" : "default",
          securityLevel: "strict",
          fontFamily: "inherit",
        });

        // Mermaid requires an id on the source element; randomize to keep
        // re-renders (e.g. theme switch) from colliding on Mermaid's cache.
        const id = `mmd-${Math.random().toString(36).slice(2, 10)}`;
        const { svg: rendered } = await mermaid.render(id, code);

        if (!cancelled) {
          setSvg(rendered);
          setRenderError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setRenderError(
            err instanceof Error ? err.message : "Failed to render diagram",
          );
          setSvg(null);
        }
      }
    }

    render();
    return () => {
      cancelled = true;
    };
  }, [code, renderKey]);

  // Re-render whenever the resolved theme flips so colors stay in sync.
  useEffect(() => {
    if (typeof document === "undefined") return;
    const target = document.documentElement;
    const observer = new MutationObserver(() => {
      // Bumping the key forces the render effect to re-run with the new theme.
      setRenderKey((k) => k + 1);
    });
    observer.observe(target, {
      attributes: true,
      attributeFilter: ["class"],
    });
    return () => observer.disconnect();
  }, []);

  if (renderError) {
    return (
      <div className="my-3 rounded-md border border-destructive/40 bg-destructive/5 p-3">
        <p className="mb-2 text-xs font-medium text-destructive">
          Mermaid diagram failed to render ({renderError}). Showing source:
        </p>
        <pre className="overflow-x-auto rounded bg-muted/50 p-3 text-xs">
          <code>{code}</code>
        </pre>
      </div>
    );
  }

  if (!svg) {
    return (
      <div
        ref={containerRef}
        className="my-3 flex items-center justify-center rounded-md border bg-muted/30 p-6 text-xs text-muted-foreground"
      >
        Rendering diagram…
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="my-3 overflow-x-auto rounded-md border bg-background p-3 [&_svg]:mx-auto [&_svg]:max-w-full"
      // Mermaid's render() returns sanitized SVG (securityLevel: strict).
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}

export interface MarkdownRendererProps {
  /** Raw markdown source. */
  content: string;
  /** Extra classes appended to the outer container. */
  className?: string;
  /**
   * Optional override for the `code` component. Receives the same props
   * react-markdown passes and the resolved element tree.
   */
  components?: Components;
}

/**
 * The shared renderer. Use this anywhere skill/file/system-prompt markdown is
 * shown so a ```mermaid``` block is rendered as a diagram everywhere
 * instead of as raw text.
 */
export function MarkdownRenderer({
  content,
  className,
  components,
}: MarkdownRendererProps) {
  const mergedComponents: Components = {
    // Override the inline + block `code` element. react-markdown passes a
    // string `className` like "language-mermaid" for fenced blocks whose
    // info string was "mermaid".
    code({ className: cls, children, ...rest }) {
      const text = String(children ?? "");
      const isMermaid = /language-mermaid/.test(cls ?? "");

      if (!isMermaid) {
        // Fall through to default rendering for non-mermaid code blocks.
        return (
          <code className={cls} {...rest}>
            {children}
          </code>
        );
      }

      // For fenced mermaid blocks, react-markdown collapses trailing
      // whitespace into the children; trim so the diagram source is clean.
      return <MermaidBlock code={text.replace(/\n$/, "")} />;
    },
    ...components,
  };

  return (
    <div className={className}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={mergedComponents}>
        {content}
      </ReactMarkdown>
    </div>
  );
}

export default MarkdownRenderer;
