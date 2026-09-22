import * as React from "react";
import {
  AlertCircle,
  CheckCircle2,
  Check,
  ChevronDown,
  CircleHelp,
  Database,
  Loader2,
  RefreshCw,
  Sparkles,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type {
  GoogleSheetsDiscoveredSheet,
  GoogleSheetsDiscovery,
} from "@/types/agent";

const NONE_VALUE = "__none__";
const MANAGED_FIELDS = [
  {
    key: "idempotency_column",
    label: "Duplicate check",
    description: "Stops the same call from creating a second row.",
  },
  {
    key: "timestamp_column",
    label: "Captured at",
    description: "Stores when the row was created.",
  },
  {
    key: "source_column",
    label: "Source",
    description: "Labels where this row came from.",
  },
  {
    key: "status_column",
    label: "Status",
    description: "Sets the initial status for a new row.",
  },
] as const;

function RequirementBadge({ required }: { required: boolean }) {
  return (
    <span
      className={cn(
        "rounded-full px-1.5 py-0.5 text-[9px] font-medium uppercase tracking-wide",
        required
          ? "bg-primary/10 text-primary"
          : "bg-muted text-muted-foreground",
      )}
    >
      {required ? "Required" : "Optional"}
    </span>
  );
}

interface HelpTooltipProps {
  label: string;
  children: React.ReactNode;
}

function HelpTooltip({ label, children }: HelpTooltipProps) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          className="inline-flex shrink-0 text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1"
          aria-label={`Help for ${label}`}
        >
          <CircleHelp className="h-3.5 w-3.5" aria-hidden="true" />
        </button>
      </TooltipTrigger>
      <TooltipContent
        side="top"
        align="start"
        className="max-w-xs text-xs leading-relaxed"
      >
        {children}
      </TooltipContent>
    </Tooltip>
  );
}

interface HeaderMultiSelectProps {
  headers: string[];
  selected: string[];
  onChange: (headers: string[]) => void;
  disabled?: boolean;
  label: string;
  placeholder: string;
}

/** Compact searchable multi-select for potentially large header lists. */
function HeaderMultiSelect({
  headers,
  selected,
  onChange,
  disabled = false,
  label,
  placeholder,
}: HeaderMultiSelectProps) {
  const [open, setOpen] = React.useState(false);
  const selectedKeys = new Set(selected.map(canonical));
  const allSelected = headers.length > 0 && selected.length === headers.length;

  const toggleHeader = (header: string) => {
    const key = canonical(header);
    const next = selectedKeys.has(key)
      ? selected.filter((value) => canonical(value) !== key)
      : [...selected, header];
    onChange(next);
  };

  const selectionLabel =
    selected.length === 0
      ? placeholder
      : allSelected
        ? `All ${headers.length} columns selected`
        : `${selected.length} of ${headers.length} columns selected`;

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="outline"
          role="combobox"
          aria-expanded={open}
          aria-label={label}
          disabled={disabled || headers.length === 0}
          className="h-10 w-full justify-between gap-3 px-3 text-left font-normal text-foreground"
        >
          <span
            className={cn(
              "min-w-0 truncate",
              selected.length === 0 && "text-muted-foreground",
            )}
          >
            {selectionLabel}
          </span>
          <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" />
        </Button>
      </PopoverTrigger>
      <PopoverContent
        align="start"
        className="w-[min(22rem,calc(100vw-3rem))] p-0"
      >
        <Command>
          <CommandInput placeholder="Search columns..." />
          <div className="flex items-center justify-between border-b px-3 py-2 text-[11px] text-muted-foreground">
            <span>
              {selected.length} of {headers.length} selected
            </span>
            <div className="flex items-center gap-1">
              <button
                type="button"
                className="rounded px-1.5 py-1 font-medium text-primary transition-colors hover:bg-primary/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                onClick={() => onChange([...headers])}
                disabled={allSelected}
              >
                Select all
              </button>
              <button
                type="button"
                className="rounded px-1.5 py-1 font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                onClick={() => onChange([])}
                disabled={selected.length === 0}
              >
                Clear
              </button>
            </div>
          </div>
          <CommandList className="max-h-64">
            <CommandEmpty>No matching columns.</CommandEmpty>
            {headers.map((header, index) => {
              const isSelected = selectedKeys.has(canonical(header));
              return (
                <CommandItem
                  key={`${header}-${index}`}
                  value={header}
                  onSelect={() => toggleHeader(header)}
                  className="gap-2"
                >
                  <span
                    className={cn(
                      "flex h-4 w-4 shrink-0 items-center justify-center rounded border",
                      isSelected
                        ? "border-primary bg-primary text-primary-foreground"
                        : "border-input bg-background",
                    )}
                    aria-hidden="true"
                  >
                    {isSelected && <Check className="h-3 w-3" />}
                  </span>
                  <span className="min-w-0 truncate">{header}</span>
                </CommandItem>
              );
            })}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}

export interface GoogleSheetsConfigEditorProps {
  agentToolId: string;
  config: Record<string, unknown>;
  initialDefaultRange: string;
  isOpen: boolean;
  hasUnsavedChanges: boolean;
  authenticated: boolean;
  canEdit: boolean;
  onConfigChange: (key: string, value: string) => void;
  onReadinessChange: (isReady: boolean) => void;
  onDiscover: (
    agentToolId: string,
    spreadsheetId: string,
  ) => Promise<GoogleSheetsDiscovery>;
}

function textValue(config: Record<string, unknown>, key: string): string {
  const value = config[key];
  return typeof value === "string" ? value : "";
}

function csvValues(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function canonical(value: string): string {
  return value.trim().replace(/\s+/g, " ").toLowerCase();
}

function columnLetters(columnCount: number): string {
  let count = Math.max(columnCount, 1);
  let result = "";
  while (count > 0) {
    const remainder = (count - 1) % 26;
    result = String.fromCharCode(65 + remainder) + result;
    count = Math.floor((count - 1) / 26);
  }
  return result;
}

function sheetReference(title: string): string {
  if (/^[A-Za-z0-9_-]+$/.test(title)) return title;
  return `'${title.replace(/'/g, "''")}'`;
}

function sheetFromRange(range: string): string {
  const separator = range.indexOf("!");
  if (separator < 0) return "";
  const sheet = range.slice(0, separator);
  return sheet.replace(/^'(.*)'$/, (_, body: string) =>
    body.replace(/''/g, "'"),
  );
}

function selectedByConfiguredValues(
  configured: string[],
  headers: string[],
  fallbackToAll: boolean,
): string[] {
  const available = new Map(
    headers.map((header) => [canonical(header), header]),
  );
  const configuredValues = configured.filter((value) => value.trim());
  const selected = configured
    .map((value) => available.get(canonical(value)))
    .filter((value): value is string => Boolean(value));
  const hasStaleSelection = configuredValues.some(
    (value) => !available.has(canonical(value)),
  );
  return fallbackToAll &&
    (configuredValues.length === 0 || hasStaleSelection)
    ? [...headers]
    : selected;
}

/** Guided, header-aware setup for a native Google Sheets attachment. */
export function GoogleSheetsConfigEditor({
  agentToolId,
  config,
  initialDefaultRange,
  isOpen,
  hasUnsavedChanges,
  authenticated,
  canEdit,
  onConfigChange,
  onReadinessChange,
  onDiscover,
}: GoogleSheetsConfigEditorProps) {
  const [sheets, setSheets] = React.useState<GoogleSheetsDiscoveredSheet[]>([]);
  const [selectedTitle, setSelectedTitle] = React.useState(() =>
    sheetFromRange(initialDefaultRange),
  );
  const [selectedHeaders, setSelectedHeaders] = React.useState<string[]>([]);
  const [agentFields, setAgentFields] = React.useState<string[]>([]);
  const [requiredFields, setRequiredFields] = React.useState<string[]>([]);
  const [isDiscovering, setIsDiscovering] = React.useState(false);
  const [hasCurrentDiscovery, setHasCurrentDiscovery] = React.useState(false);
  const [discoveryError, setDiscoveryError] = React.useState<string | null>(
    null,
  );
  const discoveryRequestId = React.useRef(0);
  const autoDiscoveryAttempted = React.useRef(false);

  React.useEffect(
    () => () => {
      discoveryRequestId.current += 1;
    },
    [],
  );

  const clearDiscoveredState = React.useCallback(() => {
    setSheets([]);
    setSelectedTitle("");
    setSelectedHeaders([]);
    setAgentFields([]);
    setRequiredFields([]);
    setHasCurrentDiscovery(false);
    setIsDiscovering(false);
    setDiscoveryError(null);
  }, []);

  const selectedSheet = React.useMemo(
    () => sheets.find((sheet) => sheet.title === selectedTitle) ?? null,
    [selectedTitle, sheets],
  );

  const updateConfig = React.useCallback(
    (key: string, value: string) => {
      onReadinessChange(false);
      onConfigChange(key, value);
    },
    [onConfigChange, onReadinessChange],
  );

  const applySheet = React.useCallback(
    (sheet: GoogleSheetsDiscoveredSheet) => {
      const usableHeaders = sheet.headers.filter((header) => header.trim());
      const configuredManagedKeys = new Set(
        MANAGED_FIELDS.map((field) => canonical(textValue(config, field.key))).filter(
          Boolean,
        ),
      );
      const businessHeaders = usableHeaders.filter(
        (header) => !configuredManagedKeys.has(canonical(header)),
      );
      setSelectedTitle(sheet.title);
      setSelectedHeaders(usableHeaders);
      const configuredAgentFields = selectedByConfiguredValues(
        csvValues(textValue(config, "agent_columns")).filter(
          (field) => !configuredManagedKeys.has(canonical(field)),
        ),
        businessHeaders,
        true,
      );
      const configuredRequiredFields = selectedByConfiguredValues(
        csvValues(textValue(config, "required_columns")),
        configuredAgentFields,
        false,
      );
      setAgentFields(configuredAgentFields);
      setRequiredFields(configuredRequiredFields);

      const reference = sheetReference(sheet.title);
      const endColumn = columnLetters(sheet.headers.length);
      updateConfig("default_range", `${reference}!A1:${endColumn}1000`);
      updateConfig("header_range", `${reference}!A1:${endColumn}1`);
      updateConfig("agent_columns", configuredAgentFields.join(", "));
      updateConfig("required_columns", configuredRequiredFields.join(", "));
      for (const field of MANAGED_FIELDS) {
        const configuredValue = textValue(config, field.key);
        if (
          configuredValue &&
          !usableHeaders.some(
            (header) => canonical(header) === canonical(configuredValue),
          )
        ) {
          updateConfig(field.key, "");
          if (field.key === "source_column") {
            updateConfig("source_value", "");
          }
          if (field.key === "status_column") {
            updateConfig("status_value", "");
          }
        }
      }
    },
    [config, updateConfig],
  );

  const handleDiscover = React.useCallback(async () => {
    const spreadsheetId = textValue(config, "spreadsheet_id").trim();
    if (!spreadsheetId) {
      clearDiscoveredState();
      setDiscoveryError("Enter a Google Sheets URL or spreadsheet ID first.");
      return;
    }
    const requestId = discoveryRequestId.current + 1;
    discoveryRequestId.current = requestId;
    onReadinessChange(false);
    setSheets([]);
    setSelectedHeaders([]);
    setAgentFields([]);
    setRequiredFields([]);
    setHasCurrentDiscovery(false);
    setIsDiscovering(true);
    setDiscoveryError(null);
    try {
      const result = await onDiscover(agentToolId, spreadsheetId);
      if (discoveryRequestId.current !== requestId) return;
      setSheets(result.sheets);
      const configuredTitle = sheetFromRange(
        textValue(config, "default_range"),
      );
      const preferredTitle = configuredTitle || selectedTitle;
      const preferred =
        result.sheets.find((sheet) => sheet.title === preferredTitle) ??
        result.sheets.find((sheet) => sheet.headers.length > 0) ??
        result.sheets[0];
      if (preferred) {
        applySheet(preferred);
        setHasCurrentDiscovery(true);
      }
      if (!preferred) {
        setDiscoveryError("No tabs were found in this spreadsheet.");
      }
    } catch (error) {
      if (discoveryRequestId.current !== requestId) return;
      setDiscoveryError(
        error instanceof Error
          ? error.message
          : "Google Sheets could not be inspected. Check the URL and connection.",
      );
    } finally {
      if (discoveryRequestId.current === requestId) {
        setIsDiscovering(false);
      }
    }
  }, [
    agentToolId,
    applySheet,
    clearDiscoveredState,
    config,
    onDiscover,
    onReadinessChange,
    selectedTitle,
  ]);

  React.useEffect(() => {
    if (!isOpen) {
      autoDiscoveryAttempted.current = false;
      return;
    }
    if (!authenticated || autoDiscoveryAttempted.current) return;

    // Attempt once per drawer-open cycle. Do not send a request for each
    // keystroke while a user is entering a new spreadsheet URL.
    autoDiscoveryAttempted.current = true;
    const hasSavedColumnSettings = Boolean(
      textValue(config, "default_range").trim() ||
        textValue(config, "header_range").trim() ||
        textValue(config, "agent_columns").trim(),
    );
    if (
      textValue(config, "spreadsheet_id").trim() &&
      hasSavedColumnSettings
    ) {
      void handleDiscover();
    }
  }, [authenticated, config, handleDiscover, isOpen]);

  const handleSpreadsheetIdChange = (value: string) => {
    discoveryRequestId.current += 1;
    clearDiscoveredState();
    updateConfig("spreadsheet_id", value);
    for (const key of [
      "default_range",
      "header_range",
      "agent_columns",
      "required_columns",
      "idempotency_column",
      "timestamp_column",
      "source_column",
      "source_value",
      "status_column",
      "status_value",
    ]) {
      updateConfig(key, "");
    }
  };

  const updateAgentFields = (next: string[]) => {
    const nextRequired = requiredFields.filter((field) =>
      next.some((candidate) => canonical(candidate) === canonical(field)),
    );
    setAgentFields(next);
    setRequiredFields(nextRequired);
    updateConfig("agent_columns", next.join(", "));
    updateConfig("required_columns", nextRequired.join(", "));
  };

  const updateRequiredFields = (next: string[]) => {
    setRequiredFields(next);
    updateConfig("required_columns", next.join(", "));
  };

  const updateManagedField = (key: string, value: string) => {
    const nextValue = value === NONE_VALUE ? "" : value;
    updateConfig(key, nextValue);
    if (!nextValue) return;

    const nextAgentFields = agentFields.filter(
      (field) => canonical(field) !== canonical(nextValue),
    );
    const nextRequiredFields = requiredFields.filter(
      (field) => canonical(field) !== canonical(nextValue),
    );
    if (nextAgentFields.length !== agentFields.length) {
      setAgentFields(nextAgentFields);
      updateConfig("agent_columns", nextAgentFields.join(", "));
    }
    if (nextRequiredFields.length !== requiredFields.length) {
      setRequiredFields(nextRequiredFields);
      updateConfig("required_columns", nextRequiredFields.join(", "));
    }
  };

  const currentManagedValue = (key: string) =>
    textValue(config, key) || NONE_VALUE;
  const configuredManagedKeys = new Set(
    MANAGED_FIELDS.map((field) => canonical(textValue(config, field.key))).filter(
      Boolean,
    ),
  );
  const agentSelectableHeaders = selectedHeaders.filter(
    (header) => !configuredManagedKeys.has(canonical(header)),
  );
  const configuredAgentFields = csvValues(textValue(config, "agent_columns"));
  const configuredRequiredFields = csvValues(
    textValue(config, "required_columns"),
  );
  const availableHeaderKeys = new Set(selectedHeaders.map(canonical));
  const configuredAgentKeys = configuredAgentFields.map(canonical);
  const configuredRequiredKeys = configuredRequiredFields.map(canonical);
  const managedColumns = MANAGED_FIELDS.map((field) =>
    textValue(config, field.key).trim(),
  ).filter(Boolean);
  const managedColumnKeys = managedColumns.map(canonical);
  const configuredRangeTab = sheetFromRange(
    textValue(config, "default_range"),
  );
  const configuredHeaderTab = sheetFromRange(
    textValue(config, "header_range"),
  );
  const mappingsAreValid = Boolean(
    selectedSheet &&
      selectedHeaders.length > 0 &&
      selectedSheet.issues.length === 0 &&
      configuredRangeTab === selectedSheet.title &&
      configuredHeaderTab === selectedSheet.title &&
      configuredAgentFields.length > 0 &&
      new Set(configuredAgentKeys).size === configuredAgentKeys.length &&
      configuredAgentKeys.every(
        (key) =>
          availableHeaderKeys.has(key) && !managedColumnKeys.includes(key),
      ) &&
      configuredRequiredKeys.every((key) => configuredAgentKeys.includes(key)) &&
      new Set(managedColumnKeys).size === managedColumnKeys.length &&
      managedColumnKeys.every((key) => availableHeaderKeys.has(key)) &&
      !(
        textValue(config, "source_value").trim() &&
        !textValue(config, "source_column").trim()
      ) &&
      !(
        textValue(config, "status_value").trim() &&
        !textValue(config, "status_column").trim()
      ),
  );
  const isConfigurationReady = Boolean(
    isOpen &&
      authenticated &&
      textValue(config, "spreadsheet_id").trim() &&
      hasCurrentDiscovery &&
      !isDiscovering &&
      !discoveryError &&
      mappingsAreValid,
  );

  React.useEffect(() => {
    onReadinessChange(isConfigurationReady);
  }, [isConfigurationReady, onReadinessChange]);

  const configurationMessage = !authenticated
    ? "Connect Google Sheets to verify the setup."
    : !textValue(config, "spreadsheet_id").trim()
      ? "Add a spreadsheet URL, then discover its columns."
      : isDiscovering
        ? "Checking the saved setup against the current sheet…"
        : discoveryError
          ? "Not configured: the sheet could not be verified."
          : !hasCurrentDiscovery
            ? "Not configured: discover the sheet columns to verify this setup."
            : isConfigurationReady
              ? hasUnsavedChanges
                ? "Setup verified. Save changes to apply this configuration."
                : "Configured: the selected fields match the current sheet."
              : "Not configured: check the tab, headers, and selected agent fields.";

  return (
    <TooltipProvider delayDuration={250}>
      <div className="space-y-5">
      <div
        role="status"
        aria-live="polite"
        className={cn(
          "flex items-start gap-2 rounded-md border px-3 py-2.5 text-xs",
          isConfigurationReady
            ? "border-emerald-300/70 bg-emerald-50 text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950/30 dark:text-emerald-200"
            : isDiscovering
              ? "border-primary/25 bg-primary/[0.04] text-foreground"
              : "border-amber-300/70 bg-amber-50 text-amber-900 dark:border-amber-700 dark:bg-amber-950/30 dark:text-amber-100",
        )}
      >
        {isConfigurationReady ? (
          <CheckCircle2
            className="mt-0.5 h-4 w-4 shrink-0"
            aria-hidden="true"
          />
        ) : isDiscovering ? (
          <Loader2
            className="mt-0.5 h-4 w-4 shrink-0 animate-spin"
            aria-hidden="true"
          />
        ) : (
          <AlertCircle
            className="mt-0.5 h-4 w-4 shrink-0"
            aria-hidden="true"
          />
        )}
        <span className="font-medium">{configurationMessage}</span>
      </div>
      <div className="rounded-xl border border-primary/20 bg-primary/[0.04] p-4 dark:bg-primary/[0.08]">
        <div className="flex items-start gap-3">
          <div className="rounded-lg bg-primary/10 p-2 text-primary">
            <Database className="h-5 w-5" aria-hidden="true" />
          </div>
          <div className="min-w-0 space-y-1">
            <p className="text-sm font-semibold">Connect a spreadsheet</p>
            <p className="text-xs leading-relaxed text-muted-foreground">
              Paste the URL once. We&apos;ll read tab names and the first row so
              you can choose fields instead of typing ranges or headers.
            </p>
          </div>
        </div>
        <div className="mt-4 space-y-3">
          <div className="min-w-0 space-y-1.5">
            <div className="flex items-center gap-2">
              <Label htmlFor="google-sheets-spreadsheet-id" className="text-xs">
                Spreadsheet URL or ID
              </Label>
              <RequirementBadge required />
            </div>
            <Input
              id="google-sheets-spreadsheet-id"
              aria-label="Google Sheets URL or spreadsheet ID"
              value={textValue(config, "spreadsheet_id")}
              onChange={(event) => handleSpreadsheetIdChange(event.target.value)}
              placeholder="https://docs.google.com/spreadsheets/d/..."
              disabled={!canEdit}
              className="h-10 bg-background text-foreground"
            />
          </div>
          <Button
            type="button"
            className="h-10 w-full justify-center"
            onClick={() => void handleDiscover()}
            disabled={!canEdit || !authenticated || isDiscovering}
          >
            {isDiscovering ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="mr-2 h-4 w-4" />
            )}
            {isDiscovering ? "Reading columns" : "Discover columns"}
          </Button>
          {textValue(config, "spreadsheet_id").trim() &&
            (!textValue(config, "default_range").trim() ||
              !textValue(config, "agent_columns").trim()) && (
              <p className="text-xs text-muted-foreground" role="status">
                Discover the current columns and select agent fields before
                saving this spreadsheet.
              </p>
            )}
        </div>
        {!authenticated && (
          <p className="mt-2 text-xs text-amber-700 dark:text-amber-300">
            Connect Google Sheets above before discovering columns.
          </p>
        )}
        {discoveryError && (
          <div className="mt-3 flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 p-3 text-xs text-destructive">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{discoveryError}</span>
          </div>
        )}
      </div>

      {sheets.length > 0 && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <p className="text-sm font-semibold">Choose the data tab</p>
                <RequirementBadge required />
              </div>
              <p className="text-xs text-muted-foreground">
                We use only the selected tab and its first row.
              </p>
            </div>
            <Select
              value={selectedTitle || undefined}
              onValueChange={(value) => {
                const sheet = sheets.find(
                  (candidate) => candidate.title === value,
                );
                if (sheet) applySheet(sheet);
              }}
              disabled={!canEdit}
            >
              <SelectTrigger
                className="w-full text-foreground sm:w-56"
                aria-label="Spreadsheet tab"
              >
                <SelectValue placeholder="Select a tab" />
              </SelectTrigger>
              <SelectContent>
                {sheets.map((sheet) => (
                  <SelectItem
                    key={`${sheet.title}-${sheet.sheet_id ?? "tab"}`}
                    value={sheet.title}
                  >
                    {sheet.title}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {selectedSheet &&
          !selectedSheet.headers.some((header) => header.trim()) ? (
            <div className="flex items-start gap-2 rounded-md border border-amber-300/70 bg-amber-50 p-3 text-xs text-amber-900 dark:border-amber-700 dark:bg-amber-950/30 dark:text-amber-100">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <div>
                <p className="font-medium">This tab has no header row yet.</p>
                <p className="mt-1">
                  Add column names in row 1, then discover columns again.
                </p>
              </div>
            </div>
          ) : selectedSheet ? (
            <>
              {selectedSheet.issues.length > 0 && (
                <div className="flex items-start gap-2 rounded-md border border-amber-300/70 bg-amber-50 p-3 text-xs text-amber-900 dark:border-amber-700 dark:bg-amber-950/30 dark:text-amber-100">
                  <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                  <span>{selectedSheet.issues.join(" ")}</span>
                </div>
              )}

              <div className="rounded-xl border bg-card p-4">
                <div className="flex items-start gap-3">
                  <div className="rounded-lg bg-emerald-500/10 p-2 text-emerald-600 dark:text-emerald-400">
                    <Sparkles className="h-5 w-5" aria-hidden="true" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-semibold">Choose agent fields</p>
                      <RequirementBadge required />
                      <HelpTooltip label="Agent fields">
                        Select the columns the voice agent may populate from the
                        call. Every discovered column starts selected; remove
                        columns that are managed by the platform or not part of
                        this workflow. Managed columns are kept out of this list
                        automatically.
                      </HelpTooltip>
                    </div>
                    <p className="text-xs leading-relaxed text-muted-foreground">
                      These are the columns the agent may fill from the call.
                      All discovered business columns start selected. Managed
                      columns stay available in the section below.
                    </p>
                  </div>
                </div>
                <div className="mt-4">
                  <HeaderMultiSelect
                    headers={agentSelectableHeaders}
                    selected={agentFields}
                    onChange={updateAgentFields}
                    disabled={!canEdit}
                    label="Agent fields"
                    placeholder="Select agent fields"
                  />
                </div>
              </div>

              <div className="rounded-xl border bg-card p-4">
                <div className="flex items-start gap-3">
                  <div className="rounded-lg bg-amber-500/10 p-2 text-amber-600 dark:text-amber-400">
                    <CheckCircle2 className="h-5 w-5" aria-hidden="true" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-semibold">Mark required fields</p>
                      <RequirementBadge required={false} />
                      <HelpTooltip label="Required fields">
                        Choose a subset of the agent fields that must be
                        collected before the tool can create a row. Leave this
                        empty when every field is optional.
                      </HelpTooltip>
                    </div>
                    <p className="text-xs leading-relaxed text-muted-foreground">
                      The agent must collect these before it can save a row.
                    </p>
                  </div>
                </div>
                <div className="mt-4">
                  <HeaderMultiSelect
                    headers={agentFields}
                    selected={requiredFields}
                    onChange={updateRequiredFields}
                    disabled={!canEdit}
                    label="Required fields"
                    placeholder="No required fields"
                  />
                </div>
                {agentFields.length === 0 && (
                  <p className="mt-3 text-xs text-muted-foreground">
                    Select at least one agent field to define the row payload.
                  </p>
                )}
              </div>

              <div className="rounded-xl border bg-card p-4">
                <div>
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-semibold">Managed columns</p>
                    <RequirementBadge required={false} />
                    <HelpTooltip label="Managed columns">
                      These optional columns are filled by the platform. Use
                      Duplicate check to prevent retries, Captured at for the
                      creation time, Source for a label, and Status for the
                      initial workflow state.
                    </HelpTooltip>
                  </div>
                  <p className="text-xs leading-relaxed text-muted-foreground">
                    Let the platform fill useful metadata automatically. Leave
                    any selector as &quot;Not used&quot; if the tab does not have
                    that column.
                  </p>
                </div>
                <div className="mt-4 grid gap-4 sm:grid-cols-2">
                  {MANAGED_FIELDS.map((field) => (
                    <div key={field.key} className="space-y-1.5">
                      <div className="flex items-center gap-1.5">
                        <Label className="text-xs">{field.label}</Label>
                        <HelpTooltip label={field.label}>
                          {field.description}
                        </HelpTooltip>
                      </div>
                      <Select
                        value={currentManagedValue(field.key)}
                        onValueChange={(value) =>
                          updateManagedField(field.key, value)
                        }
                        disabled={!canEdit}
                      >
                        <SelectTrigger
                          className="w-full text-foreground"
                          aria-label={field.label}
                        >
                          <SelectValue placeholder="Not used" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value={NONE_VALUE}>Not used</SelectItem>
                          {selectedHeaders.map((header, index) => (
                            <SelectItem
                              key={`${field.key}-${header}-${index}`}
                              value={header}
                            >
                              {header}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <p className="text-[11px] text-muted-foreground">
                        {field.description}
                      </p>
                    </div>
                  ))}
                </div>
                {(textValue(config, "source_column") ||
                  textValue(config, "status_column")) && (
                  <div className="mt-4 grid gap-4 sm:grid-cols-2">
                    {textValue(config, "source_column") && (
                      <div className="space-y-1.5">
                        <Label
                          htmlFor="google-sheets-source-value"
                          className="text-xs"
                        >
                          Source value
                        </Label>
                        <Input
                          id="google-sheets-source-value"
                          value={textValue(config, "source_value")}
                          onChange={(event) =>
                            onConfigChange("source_value", event.target.value)
                          }
                          placeholder="Website inquiry"
                          disabled={!canEdit}
                          className="text-foreground"
                        />
                      </div>
                    )}
                    {textValue(config, "status_column") && (
                      <div className="space-y-1.5">
                        <Label
                          htmlFor="google-sheets-status-value"
                          className="text-xs"
                        >
                          Initial status
                        </Label>
                        <Input
                          id="google-sheets-status-value"
                          value={textValue(config, "status_value")}
                          onChange={(event) =>
                            onConfigChange("status_value", event.target.value)
                          }
                          placeholder="New"
                          disabled={!canEdit}
                          className="text-foreground"
                        />
                      </div>
                    )}
                  </div>
                )}
              </div>

              <p className="text-[11px] text-muted-foreground">
                Working area: {textValue(config, "default_range") ||
                  "Choose a tab to generate this"}
              </p>
            </>
          ) : null}
        </div>
      )}
      </div>
    </TooltipProvider>
  );
}
