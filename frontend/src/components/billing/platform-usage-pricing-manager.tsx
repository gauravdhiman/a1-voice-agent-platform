"use client";

import * as React from "react";
import { Clock3, Info, Loader2, Save } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { adminPlanService } from "@/services/admin-plan-service";
import type { CreditEvent } from "@/types/admin-plans";

interface CreditEventDraft {
  description: string;
  credit_cost: number;
}

interface SystemPricingCopy {
  category: string;
  label: string;
  rule: string;
}

const SYSTEM_PRICING_COPY: Record<string, SystemPricingCopy> = {
  voice_call_minute: {
    category: "Voice",
    label: "Voice calls",
    rule: "Per connected minute",
  },
  phone_number_local_month: {
    category: "Phone number",
    label: "Local phone numbers",
    rule: "Per active number / month",
  },
  phone_number_mobile_month: {
    category: "Phone number",
    label: "Mobile phone numbers",
    rule: "Per active number / month",
  },
  phone_number_toll_free_month: {
    category: "Phone number",
    label: "Toll-free phone numbers",
    rule: "Per active number / month",
  },
};

/** Return the fixed user-facing label for a system activity. */
function eventLabel(event: CreditEvent): string {
  return (
    SYSTEM_PRICING_COPY[event.name]?.label ??
    event.name
      .split("_")
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(" ")
  );
}

/** Return the runtime-owned pricing rule shown beside an editable rate. */
function pricingRule(event: CreditEvent): string {
  return SYSTEM_PRICING_COPY[event.name]?.rule ?? "System-defined activity";
}

/** Return the fixed category used to group a system pricing activity. */
function pricingCategory(event: CreditEvent): string {
  return SYSTEM_PRICING_COPY[event.name]?.category ?? "System";
}

/**
 * Platform-admin editor for the finite system usage-pricing catalog.
 *
 * The editor sits inside Plan Catalog. It exposes only the credit rate because
 * the platform owns the measurement and interval for each supported activity.
 */
export function PlatformUsagePricingManager() {
  const [events, setEvents] = React.useState<CreditEvent[]>([]);
  const [drafts, setDrafts] = React.useState<Record<string, CreditEventDraft>>({});
  const [loading, setLoading] = React.useState(true);
  const [savingName, setSavingName] = React.useState<string | null>(null);

  const loadEvents = React.useCallback(async () => {
    try {
      setLoading(true);
      const rows = await adminPlanService.listCreditEvents();
      setEvents(rows);
      setDrafts(
        Object.fromEntries(
          rows.map((event) => [
            event.name,
            {
              description: event.description ?? "",
              credit_cost: event.credit_cost,
            },
          ]),
        ),
      );
    } catch (error) {
      console.error("Failed to load usage pricing:", error);
      toast.error("Failed to load usage pricing");
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void loadEvents();
  }, [loadEvents]);

  const updateDraft = (name: string, patch: Partial<CreditEventDraft>) => {
    setDrafts((current) => ({
      ...current,
      [name]: { ...current[name], ...patch },
    }));
  };

  const handleSave = async (event: CreditEvent) => {
    const draft = drafts[event.name];
    if (!draft) return;
    try {
      setSavingName(event.name);
      const updated = await adminPlanService.updateCreditEvent(event.name, draft);
      setEvents((current) =>
        current.map((item) => (item.name === updated.name ? updated : item)),
      );
      toast.success(`${eventLabel(event)} pricing saved`);
    } catch (error) {
      console.error("Failed to save usage pricing:", error);
      toast.error(
        error instanceof Error ? error.message : "Failed to save usage pricing",
      );
    } finally {
      setSavingName(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading usage pricing…
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="rounded-lg border bg-muted/20 p-4">
        <div className="flex items-start gap-3">
          <div className="rounded-md bg-primary/10 p-2 text-primary">
            <Clock3 className="h-5 w-5" />
          </div>
          <div>
            <h2 className="font-semibold">System usage pricing</h2>
            <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
              These are the only activities currently charged from credits. Rates
              apply across the platform and can be set to zero when an activity
              is included. The platform owns the measurement rule for each one.
            </p>
          </div>
        </div>
      </div>

      {events.length === 0 ? (
        <Card>
          <CardContent className="py-8 text-center text-sm text-muted-foreground">
            No system usage prices are configured yet.
          </CardContent>
        </Card>
      ) : (
        <Card className="overflow-hidden">
          <CardHeader className="border-b bg-muted/10">
            <div className="flex items-start justify-between gap-3">
              <div>
                <CardTitle>Pricing rates</CardTitle>
                <CardDescription className="mt-1">
                  Compare and update every system-wide credit charge in one place.
                </CardDescription>
              </div>
              <Badge variant="secondary">System-wide</Badge>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            <TooltipProvider>
              <Table
                aria-label="System usage pricing"
                className="min-w-[760px]"
              >
                <TableHeader>
                  <TableRow className="hover:bg-transparent">
                    <TableHead className="w-[140px]">Category</TableHead>
                    <TableHead>Activity</TableHead>
                    <TableHead>Billing basis</TableHead>
                    <TableHead className="w-[180px]">Credit cost</TableHead>
                    <TableHead className="w-[120px] text-right">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {events.map((event) => {
                    const draft = drafts[event.name];
                    if (!draft) return null;
                    const label = eventLabel(event);
                    const description =
                      draft.description || "No description has been provided.";

                    return (
                      <TableRow key={event.name}>
                        <TableCell>
                          <Badge variant="outline">{pricingCategory(event)}</Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <span className="font-medium">{label}</span>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <button
                                  type="button"
                                  className="inline-flex h-7 w-7 items-center justify-center rounded-full text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                                  aria-label={`More information about ${label}`}
                                >
                                  <Info className="h-4 w-4" aria-hidden="true" />
                                </button>
                              </TooltipTrigger>
                              <TooltipContent side="top" className="max-w-xs">
                                {description}
                              </TooltipContent>
                            </Tooltip>
                          </div>
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {pricingRule(event)}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Label className="sr-only" htmlFor={`cost-${event.name}`}>
                              Credit cost for {label}
                            </Label>
                            <Input
                              id={`cost-${event.name}`}
                              aria-label={`Credit cost for ${label}`}
                              className="w-28"
                              type="number"
                              min={0}
                              step={1}
                              value={draft.credit_cost}
                              onChange={(e) =>
                                updateDraft(event.name, {
                                  credit_cost: Math.max(
                                    0,
                                    Number(e.target.value) || 0,
                                  ),
                                })
                              }
                            />
                            <span className="text-xs text-muted-foreground">
                              credits
                            </span>
                          </div>
                        </TableCell>
                        <TableCell className="text-right">
                          <Button
                            size="sm"
                            onClick={() => void handleSave(event)}
                            disabled={savingName === event.name}
                          >
                            {savingName === event.name ? (
                              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            ) : (
                              <Save className="mr-2 h-4 w-4" />
                            )}
                            Save
                          </Button>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </TooltipProvider>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
