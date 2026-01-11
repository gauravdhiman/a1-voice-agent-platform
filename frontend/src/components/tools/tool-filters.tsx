import * as React from "react";
import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { Search, Filter } from "lucide-react";

export type ToolFilterType = "all" | "connected" | "not_configured";

export interface ToolFiltersProps {
  searchQuery: string;
  onSearchChange: (query: string) => void;
  filterType: ToolFilterType;
  onFilterChange: (filter: ToolFilterType) => void;
  totalCount: number;
  filteredCount: number;
  className?: string;
}

export function ToolFilters({
  searchQuery,
  onSearchChange,
  filterType,
  onFilterChange,
  totalCount,
  filteredCount,
  className,
}: ToolFiltersProps) {
  const filterOptions: { value: ToolFilterType; label: string }[] = [
    { value: "all", label: "All" },
    { value: "connected", label: "Connected" },
    { value: "not_configured", label: "Not configured" },
  ];

  return (
    <div className={cn("space-y-4", className)}>
      <div className="flex items-center gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search tools..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="pl-9"
          />
        </div>
        <div className="hidden sm:flex items-center gap-1.5 text-sm text-muted-foreground px-2">
          <Filter className="h-4 w-4" />
          <span>
            {filteredCount} of {totalCount}
          </span>
        </div>
      </div>

      <div className="flex gap-1.5 overflow-x-auto pb-1 sm:pb-0">
        {filterOptions.map((option) => (
          <button
            key={option.value}
            onClick={() => onFilterChange(option.value)}
            className={cn(
              "px-3 py-1.5 text-sm font-medium rounded-full whitespace-nowrap transition-colors",
              filterType === option.value
                ? "bg-primary text-primary-foreground"
                : "bg-muted text-muted-foreground hover:bg-muted/80",
            )}
          >
            {option.label}
          </button>
        ))}
      </div>
    </div>
  );
}
