import * as React from "react";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { Code2, ChevronDown, ListChecks, Wrench } from "lucide-react";
import type { PlatformTool, PlatformToolFunction } from "@/types/agent";
import {
  filterMcpFunctions,
  McpFunctionSearch,
} from "@/components/tools/mcp-function-search";

/**
 * MCP function catalog drawer for platform administrators.
 *
 * The manage list intentionally stays compact. This drawer provides a
 * readable inspection surface for every discovered function, including its
 * description, required parameters, and parameter types, without making the
 * admin scan a truncated comma-separated string.
 */
export interface McpFunctionCatalogDrawerProps {
  /** Whether the catalog drawer is open. */
  open: boolean;
  /** Called when the drawer should be opened or closed. */
  onOpenChange: (open: boolean) => void;
  /** MCP platform tool whose public function catalog should be inspected. */
  tool: PlatformTool | null;
}

/**
 * Renders the discovered MCP function catalog in a right-side drawer.
 *
 * @param props - Drawer visibility, close handler, and selected MCP tool.
 * @returns A Sheet containing the function details, or an empty Sheet when no
 * tool is selected.
 */
export function McpFunctionCatalogDrawer({
  open,
  onOpenChange,
  tool,
}: McpFunctionCatalogDrawerProps) {
  const functions = tool?.tool_functions_schema?.functions || [];
  const [functionSearch, setFunctionSearch] = React.useState("");
  const [expandedFunctionName, setExpandedFunctionName] = React.useState<
    string | null
  >(null);

  const filteredFunctions = filterMcpFunctions(functions, functionSearch);

  React.useEffect(() => {
    setExpandedFunctionName(null);
    setFunctionSearch("");
  }, [open, tool?.id]);

  React.useEffect(() => {
    setExpandedFunctionName(null);
  }, [functionSearch]);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="flex w-full flex-col overflow-hidden sm:max-w-xl">
        <SheetHeader className="shrink-0 border-b px-6 pb-5 pt-6">
          <SheetTitle className="flex items-center gap-2">
            <Code2 className="h-5 w-5 text-primary" />
            {tool
              ? `${tool.name.replace(/_/g, " ")} functions`
              : "MCP functions"}
          </SheetTitle>
          <SheetDescription>
            {functions.length} discovered public function
            {functions.length === 1 ? "" : "s"} available to Org Admins.
          </SheetDescription>
        </SheetHeader>

        <div className="min-h-0 flex-1 overflow-y-auto px-6 py-5">
          <div className="space-y-4 pb-6">
            {functions.length > 0 && (
              <McpFunctionSearch
                value={functionSearch}
                onChange={setFunctionSearch}
                matchCount={filteredFunctions.length}
                totalCount={functions.length}
              />
            )}
            {filteredFunctions.length > 0 ? (
              filteredFunctions.map((func) => (
                <FunctionCard
                  key={func.name}
                  functionDefinition={func}
                  expanded={expandedFunctionName === func.name}
                  onToggle={() =>
                    setExpandedFunctionName((current) =>
                      current === func.name ? null : func.name,
                    )
                  }
                />
              ))
            ) : functions.length > 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-center dark:border-slate-700 dark:bg-slate-950/30">
                <p className="text-sm font-medium">No functions found</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Try a different name, description, or parameter.
                </p>
              </div>
            ) : null}
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}

interface FunctionCardProps {
  /** One discovered MCP function definition. */
  functionDefinition: PlatformToolFunction;
  /** Whether the full function details are visible. */
  expanded: boolean;
  /** Toggles this function's detail disclosure. */
  onToggle: () => void;
}

/**
 * Displays one MCP function and its input schema in a compact inspection card.
 *
 * @param props - Function definition returned by MCP tools/list.
 * @returns A function detail card.
 */
function FunctionCard({
  functionDefinition,
  expanded,
  onToggle,
}: FunctionCardProps) {
  const [descriptionExpanded, setDescriptionExpanded] = React.useState(false);
  const properties = functionDefinition.parameters?.properties || {};
  const required = new Set(functionDefinition.parameters?.required || []);
  const propertyEntries = Object.entries(properties);
  const description =
    functionDefinition.description || "No description provided.";
  const hasLongDescription = description.length > 180;
  const descriptionPreview = hasLongDescription
    ? `${description.slice(0, 180).trimEnd()}…`
    : description;
  const detailsId = `mcp-function-details-${functionDefinition.name.replace(
    /[^a-zA-Z0-9_-]/g,
    "-",
  )}`;
  const descriptionId = `${detailsId}-description`;

  React.useEffect(() => {
    setDescriptionExpanded(false);
  }, [functionDefinition.name, functionDefinition.description]);

  return (
    <section
      className={cn(
        "overflow-hidden rounded-2xl border shadow-sm transition-colors",
        expanded
          ? "border-slate-300 bg-slate-50 dark:border-slate-700 dark:bg-slate-950/40"
          : "border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-950/20",
      )}
    >
      <button
        type="button"
        className="flex w-full items-start gap-3 p-4 text-left transition-colors hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset"
        aria-expanded={expanded}
        aria-controls={detailsId}
        onClick={onToggle}
      >
        <div className="rounded-xl bg-primary/10 p-2 text-primary">
          <Wrench className="h-4 w-4" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-sm font-semibold">
              {functionDefinition.name}
            </span>
            <Badge variant="outline" className="h-5 text-[10px]">
              function
            </Badge>
          </div>
          <p
            id={descriptionId}
            className={cn(
              "mt-1 text-sm leading-6 text-muted-foreground",
              !descriptionExpanded && "line-clamp-2",
            )}
          >
            {descriptionExpanded ? description : descriptionPreview}
          </p>
          <p className="mt-2 text-[11px] text-muted-foreground">
            {propertyEntries.length > 0
              ? `${propertyEntries.length} parameter${propertyEntries.length === 1 ? "" : "s"}`
              : "No input parameters"}
            <span className="mx-1.5 text-border">·</span>
            {expanded ? "Hide details" : "View details"}
          </p>
        </div>
        <ChevronDown
          className={cn(
            "mt-1 h-4 w-4 shrink-0 text-muted-foreground transition-transform",
            expanded && "rotate-180 text-primary",
          )}
        />
      </button>

      {hasLongDescription && (
        <div className="px-4 pb-3">
          <button
            type="button"
            className="text-xs font-medium text-primary underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            aria-controls={descriptionId}
            aria-expanded={descriptionExpanded}
            onClick={() => setDescriptionExpanded((current) => !current)}
          >
            {descriptionExpanded
              ? "Hide full description"
              : "Show full description"}
          </button>
        </div>
      )}

      {expanded && (
        <div
          id={detailsId}
          className="border-t border-slate-200/80 bg-slate-100/70 px-4 pb-4 pt-3 dark:border-slate-800/80 dark:bg-slate-900/60"
        >
          {propertyEntries.length > 0 ? (
            <>
              <div className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-[0.12em] text-muted-foreground">
                <ListChecks className="h-3.5 w-3.5" />
                Parameters
              </div>
              <div className="space-y-2">
                {propertyEntries.map(([name, property]) => (
                  <div
                    key={name}
                    className="rounded-xl border border-slate-200 bg-white px-3 py-2.5 shadow-sm dark:border-slate-700 dark:bg-slate-950/80"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-xs font-semibold">
                        {name}
                      </span>
                      <Badge variant="secondary" className="h-5 text-[10px]">
                        {property.type || "any"}
                      </Badge>
                      {required.has(name) && (
                        <Badge
                          variant="outline"
                          className="h-5 border-amber-300 bg-amber-50 text-[10px] text-amber-800 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-200"
                        >
                          required
                        </Badge>
                      )}
                    </div>
                    {property.description && (
                      <p className="mt-1 text-xs leading-5 text-muted-foreground">
                        {property.description}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </>
          ) : (
            <p className="text-xs text-muted-foreground">
              This function does not declare input parameters.
            </p>
          )}
        </div>
      )}
    </section>
  );
}
