/**
 * Component tests for the shared <MarkdownRenderer>.
 *
 * Covers:
 *   - plain markdown (headings, paragraphs, lists) renders correctly
 *   - a fenced ```mermaid block triggers Mermaid.render and injects SVG
 *   - a non-mermaid fenced code block stays as <pre><code>
 *   - when Mermaid throws, the renderer falls back to a fenced code view
 *     containing the original source plus an error caption
 *   - inline `code` (not fenced) is unaffected
 *
 * Mermaid is mocked at the module level so we don't depend on jsdom being
 * able to lay out real SVG. The mock records the calls and returns a small
 * canned SVG so the component's contract is what we test, not Mermaid's.
 */
import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";

// Mermaid is dynamically imported by MarkdownRenderer, so the mock has to
// survive both static and dynamic import shapes.
const renderMock = vi.fn(async (..._args: unknown[]) => ({
  svg: "<svg data-testid=\"mmd-svg\"><g>fake</g></svg>",
}));
const initializeMock = vi.fn((..._args: unknown[]) => undefined);

vi.mock("mermaid", () => {
  return {
    default: {
      initialize: (...args: unknown[]) => initializeMock(...args),
      render: (...args: unknown[]) => renderMock(...args),
    },
  };
});

import { MarkdownRenderer } from "@/components/markdown/markdown-renderer";

afterEach(() => {
  cleanup();
  renderMock.mockClear();
  initializeMock.mockClear();
  renderMock.mockResolvedValue({
    svg: "<svg data-testid=\"mmd-svg\"><g>fake</g></svg>",
  });
});

describe("MarkdownRenderer", () => {
  beforeEach(() => {
    // Default: resolve body has no `dark` class so theme = "default".
    document.documentElement.classList.remove("dark");
  });

  it("renders plain markdown (headings, paragraphs, lists)", async () => {
    const md = `# Title\n\nA paragraph with **bold** text.\n\n- one\n- two\n`;
    const { container } = render(<MarkdownRenderer content={md} />);

    expect(screen.getByRole("heading", { level: 1, name: "Title" })).toBeInTheDocument();
    // react-markdown renders strong as <strong>
    expect(container.querySelector("strong")?.textContent).toBe("bold");
    expect(screen.getByText("one")).toBeInTheDocument();
    expect(screen.getByText("two")).toBeInTheDocument();
    // Mermaid must NOT have been called for non-mermaid content.
    expect(renderMock).not.toHaveBeenCalled();
  });

  it("renders a fenced mermaid block as SVG via mermaid.render", async () => {
    const md = [
      "Here is a flowchart:",
      "",
      "```mermaid",
      "flowchart LR",
      "  A[Start] --> B{Decision}",
      "  B -->|yes| C[End]",
      "  B -->|no| B",
      "```",
      "",
      "And some prose after.",
    ].join("\n");

    render(<MarkdownRenderer content={md} />);

    // The first child renders synchronously; Mermaid resolves asynchronously.
    await waitFor(() => expect(renderMock).toHaveBeenCalledTimes(1));
    const [id, src] = renderMock.mock.calls[0] as [string, string];
    expect(typeof id).toBe("string");
    expect(id.startsWith("mmd-")).toBe(true);
    expect(src).toContain("flowchart LR");
    expect(src).toContain("A[Start]");

    // The SVG we mocked should now be in the document.
    await waitFor(() =>
      expect(screen.getByTestId("mmd-svg")).toBeInTheDocument(),
    );
    // The "Rendering diagram…" placeholder is gone once SVG lands.
    expect(screen.queryByText(/Rendering diagram/i)).not.toBeInTheDocument();
    // Surrounding markdown still renders.
    expect(screen.getByText(/Here is a flowchart/i)).toBeInTheDocument();
    expect(screen.getByText(/some prose after/i)).toBeInTheDocument();
  });

  it("initializes mermaid with a theme derived from the <html> class", async () => {
    document.documentElement.classList.add("dark");
    const md = "```mermaid\nflowchart TD\n  A --> B\n```";
    render(<MarkdownRenderer content={md} />);

    await waitFor(() => expect(initializeMock).toHaveBeenCalled());
    expect(initializeMock).toHaveBeenLastCalledWith(
      expect.objectContaining({ theme: "dark", securityLevel: "strict" }),
    );
  });

  it("initializes mermaid with the default (light) theme outside dark mode", async () => {
    const md = "```mermaid\nflowchart TD\n  A --> B\n```";
    render(<MarkdownRenderer content={md} />);

    await waitFor(() => expect(initializeMock).toHaveBeenCalled());
    expect(initializeMock).toHaveBeenLastCalledWith(
      expect.objectContaining({ theme: "default", securityLevel: "strict" }),
    );
  });

  it("falls back to a fenced code view when mermaid.render throws", async () => {
    renderMock.mockRejectedValueOnce(new Error("syntax error in diagram"));
    const md = [
      "```mermaid",
      "this is not valid mermaid",
      "```",
    ].join("\n");
    render(<MarkdownRenderer content={md} />);

    await waitFor(() =>
      expect(screen.getByText(/Mermaid diagram failed to render/i)).toBeInTheDocument(),
    );
    expect(screen.getByText(/syntax error in diagram/i)).toBeInTheDocument();
    // Original source is still visible in the fallback block.
    expect(screen.getByText(/this is not valid mermaid/i)).toBeInTheDocument();
  });

  it("does not treat a non-mermaid fenced code block as a diagram", () => {
    const md = [
      "```ts",
      "const x: number = 1;",
      "```",
    ].join("\n");
    const { container } = render(<MarkdownRenderer content={md} />);

    // Mermaid is never invoked.
    expect(renderMock).not.toHaveBeenCalled();
    // The TypeScript code stays inside a <pre><code> block.
    const code = container.querySelector("pre code");
    expect(code?.textContent).toContain("const x: number = 1;");
  });

  it("does not treat inline `code` as a mermaid block", () => {
    const { container } = render(
      <MarkdownRenderer content={"Use `language-mermaid` in a fenced block."} />,
    );
    expect(renderMock).not.toHaveBeenCalled();
    // Inline code renders as <code>, not wrapped in a diagram container.
    expect(container.querySelector("p code")?.textContent).toBe("language-mermaid");
  });
});
