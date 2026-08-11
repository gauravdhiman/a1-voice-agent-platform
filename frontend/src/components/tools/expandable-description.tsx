import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * Props for a two-line description that can be expanded without leaving the
 * current card or drawer.
 */
export interface ExpandableDescriptionProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Description text to render. Empty descriptions are omitted. */
  description: string | null | undefined;
  /** Optional id used by the accessible expand/collapse control. */
  descriptionId?: string;
  /** Text styling applied to the description paragraph. */
  textClassName?: string;
  /** Number of characters kept in the compact preview. */
  previewLength?: number;
}

/**
 * Renders a compact description with an explicit full-text affordance when
 * the content is longer than the two-line preview.
 *
 * @param props - Description content, styling, and optional accessibility id.
 * @returns A description paragraph and, when needed, a See-more control.
 */
export function ExpandableDescription({
  description,
  descriptionId,
  textClassName,
  previewLength = 180,
  className,
  ...props
}: ExpandableDescriptionProps) {
  const normalizedDescription = description?.trim() || "";
  const [expanded, setExpanded] = React.useState(false);
  const hasLongDescription = normalizedDescription.length > previewLength;
  const preview = hasLongDescription
    ? `${normalizedDescription.slice(0, previewLength).trimEnd()}…`
    : normalizedDescription;

  React.useEffect(() => {
    setExpanded(false);
  }, [normalizedDescription, previewLength]);

  if (!normalizedDescription) return null;

  return (
    <div className={cn("space-y-1", className)} {...props}>
      <p
        id={descriptionId}
        className={cn(
          textClassName,
          hasLongDescription && !expanded && "line-clamp-2",
        )}
      >
        {expanded || !hasLongDescription ? normalizedDescription : preview}
      </p>
      {hasLongDescription && (
        <button
          type="button"
          className="text-xs font-medium text-primary underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          aria-controls={descriptionId}
          aria-expanded={expanded}
          onClick={() => setExpanded((current) => !current)}
        >
          {expanded ? "Hide full description" : "Show full description"}
        </button>
      )}
    </div>
  );
}
