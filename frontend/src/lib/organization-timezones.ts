/**
 * Common IANA timezone options for organization settings.
 *
 * Not exhaustive — admins can pick from this curated list covering major US
 * and international business zones. Backend validates against the full IANA
 * database on save.
 */

export const ORGANIZATION_TIMEZONE_UNSET = "__platform_default__";

export const ORGANIZATION_TIMEZONE_OPTIONS = [
  { value: ORGANIZATION_TIMEZONE_UNSET, label: "Platform default" },
  { value: "America/Los_Angeles", label: "Pacific Time (America/Los_Angeles)" },
  { value: "America/Denver", label: "Mountain Time (America/Denver)" },
  { value: "America/Phoenix", label: "Arizona (America/Phoenix)" },
  { value: "America/Chicago", label: "Central Time (America/Chicago)" },
  { value: "America/New_York", label: "Eastern Time (America/New_York)" },
  { value: "America/Anchorage", label: "Alaska (America/Anchorage)" },
  { value: "Pacific/Honolulu", label: "Hawaii (Pacific/Honolulu)" },
  { value: "Europe/London", label: "UK (Europe/London)" },
  { value: "Europe/Paris", label: "Central Europe (Europe/Paris)" },
  { value: "Asia/Kolkata", label: "India (Asia/Kolkata)" },
  { value: "Asia/Singapore", label: "Singapore (Asia/Singapore)" },
  { value: "Australia/Sydney", label: "Australia Eastern (Australia/Sydney)" },
  { value: "UTC", label: "UTC" },
] as const;
