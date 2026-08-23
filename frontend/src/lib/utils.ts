import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Converts an underscore-delimited tool identifier into title case for display.
 *
 * @param name - Tool identifier such as `google_calendar`.
 * @returns Human-readable tool name such as `Google Calendar`.
 */
export function formatToolName(name: string): string {
  if (!name) return ""
  return name
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ")
}
