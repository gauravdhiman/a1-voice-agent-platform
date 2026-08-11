import * as React from "react";
import { Search, X } from "lucide-react";
import { Input } from "@/components/ui/input";
import type { PlatformToolFunction } from "@/types/agent";

/**
 * Props for the compact client-side search control used by MCP function drawers.
 */
export interface McpFunctionSearchProps {
  /** Current search query. */
  value: string;
  /** Updates the current search query. */
  onChange: (value: string) => void;
  /** Number of functions matching the current query. */
  matchCount: number;
  /** Total number of discovered functions. */
  totalCount: number;
}

/**
 * Filters MCP functions by their names so descriptions and parameter metadata
 * cannot produce surprising matches for a name-oriented search.
 *
 * @param functions - Discovered MCP function definitions.
 * @param query - User-entered search text.
 * @returns Functions matching the normalized query, or every function when
 * the query is empty.
 */
export function filterMcpFunctions(
  functions: PlatformToolFunction[],
  query: string,
): PlatformToolFunction[] {
  const normalizedQuery = query.trim().toLowerCase();
  if (!normalizedQuery) return functions;

  return functions.filter((func) =>
    func.name.toLowerCase().includes(normalizedQuery),
  );
}

/**
 * Renders the consistent search affordance shared by platform and org admin
 * MCP function drawers.
 *
 * @param props - Search value, change handler, and result counts.
 * @returns A labeled search field with match feedback and a clear action.
 */
export function McpFunctionSearch({
  value,
  onChange,
  matchCount,
  totalCount,
}: McpFunctionSearchProps) {
  const functionLabel = totalCount === 1 ? "function" : "functions";

  return (
    <div className="space-y-2">
      <div className="relative">
        <Search
          aria-hidden="true"
          className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
        />
        <Input
          type="search"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder="Search functions by name or description"
          aria-label="Search functions"
          className="form-control h-9 pl-9 pr-9 text-sm"
        />
        {value && (
          <button
            type="button"
            aria-label="Clear function search"
            className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-1 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            onClick={() => onChange("")}
          >
            <X aria-hidden="true" className="h-3.5 w-3.5" />
          </button>
        )}
      </div>
      <p className="text-[11px] text-muted-foreground" aria-live="polite">
        {matchCount} of {totalCount} {functionLabel}
      </p>
    </div>
  );
}
