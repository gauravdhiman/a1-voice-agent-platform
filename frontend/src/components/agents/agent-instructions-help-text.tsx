import { cn } from "@/lib/utils";

/**
 * Shared guidance for the Markdown instructions field on create and edit
 * screens.
 */
interface AgentInstructionsHelpTextProps
{
  /** Optional styling override for the inline guidance text. */
  className?: string;
}

/**
 * Explains what belongs in agent instructions and which runtime variables are
 * available to users.
 */
export function AgentInstructionsHelpText({
  className,
}: AgentInstructionsHelpTextProps) {
  return (
    <span className={cn("inline", className)}>
      Use{" "}
      <a
        href="https://www.markdownguide.org/basic-syntax/"
        target="_blank"
        rel="noopener noreferrer"
        className="text-primary underline underline-offset-2 hover:text-primary/80"
      >
        markdown format
      </a>{" "}
      for the mission, procedures, and business-specific guidance. The agent
      role and communication style are managed above. Use{" "}
      <code className="text-xs bg-muted px-1 py-0.5 rounded">
        {"{{org.name}}"}
      </code>
      ,{" "}
      <code className="text-xs bg-muted px-1 py-0.5 rounded">
        {"{{org.industry}}"}
      </code>
      ,{" "}
      <code className="text-xs bg-muted px-1 py-0.5 rounded">
        {"{{agent.name}}"}
      </code>{" "}
      for dynamic context.
    </span>
  );
}
