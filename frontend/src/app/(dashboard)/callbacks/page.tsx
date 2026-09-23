"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useOrganization } from "@/contexts/organization-context";
import {
  useEscalations,
  useMarkEscalationStatus,
} from "@/hooks/use-escalations";
import type { EscalationStatus } from "@/services/callback-service";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Info, Loader2, PhoneCall } from "lucide-react";
import { useUserPermissions } from "@/hooks/use-user-permissions";
import { cn } from "@/lib/utils";

const STATUS_FILTERS: Array<{ value: string; label: string }> = [
  { value: "all", label: "All callbacks" },
  { value: "new", label: "New" },
  { value: "acknowledged", label: "Acknowledged" },
  { value: "resolved", label: "Resolved" },
];

const STATUS_STYLES: Record<EscalationStatus, string> = {
  new: "bg-blue-100 text-blue-700 dark:bg-blue-950/50 dark:text-blue-300",
  acknowledged:
    "bg-amber-100 text-amber-700 dark:bg-amber-950/50 dark:text-amber-300",
  resolved:
    "bg-green-100 text-green-700 dark:bg-green-950/50 dark:text-green-300",
};

/**
 * Owner callback queue (soft escalation follow-up).
 *
 * Lists every callback the agents requested, newest first. Organization
 * admins acknowledge and resolve rows; members read. Rows marked urgent
 * surface first within the newest-first order.
 */
export default function CallbacksPage() {
  const { currentOrganization } = useOrganization();
  const orgId = currentOrganization?.id ?? "";
  const { isOrgAdmin, isPlatformAdmin } = useUserPermissions();
  const canManage = isOrgAdmin || isPlatformAdmin;

  const [statusFilter, setStatusFilter] = useState("all");
  const status = (statusFilter === "all" ? undefined : statusFilter) as
    | EscalationStatus
    | undefined;
  const { data, isLoading, isError, error, refetch } = useEscalations(
    orgId,
    status,
  );
  const markStatus = useMarkEscalationStatus(orgId);

  const items = [...(data ?? [])].sort((left, right) => {
    if (left.urgency !== right.urgency) {
      return left.urgency === "urgent" ? -1 : 1;
    }
    return right.created_at.localeCompare(left.created_at);
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="min-w-0">
          <h1 className="flex items-center gap-2 text-xl font-bold tracking-tight sm:text-2xl">
            <PhoneCall className="h-6 w-6 shrink-0 text-blue-600" />
            Callback requests
          </h1>
          <p className="text-muted-foreground mt-1">
            Callers who asked for a person. Call them back, then mark each
            row resolved.
          </p>
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-full sm:w-48" aria-label="Filter by status">
            <SelectValue placeholder="All callbacks" />
          </SelectTrigger>
            <SelectContent>
              {STATUS_FILTERS.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
        </Select>
      </div>

      {isPlatformAdmin && (
        <Alert>
          <Info className="h-4 w-4" />
          <AlertDescription>
            Demo and request-form submissions are tracked in{" "}
            <Link
              href="/platform/interest"
              className="font-medium underline underline-offset-4"
            >
              Platform Interest
            </Link>
            . This page only shows callback requests recorded when a caller
            asks an agent for a person.
          </AlertDescription>
        </Alert>
      )}

      {isError && (
        <Alert variant="destructive">
          <AlertDescription>
            {error instanceof Error
              ? error.message
              : "Could not load callbacks."}{" "}
            <Button variant="link" onClick={() => void refetch()}>
              Retry
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {isLoading ? (
        <div className="flex items-center gap-2 text-muted-foreground">
          <Loader2 className="w-4 h-4 animate-spin" />
          Loading callbacks…
        </div>
      ) : items.length === 0 ? (
        <Card>
          <CardContent className="py-10 text-center text-muted-foreground">
            No callback requests yet. When a caller asks for a person, the
            request lands here with the number and reason.
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3" data-testid="callbacks-list">
          {items.map((item) => (
            <Card key={item.id} data-testid={`callback-row-${item.id}`}>
              <CardHeader className="pb-2">
                <div className="flex flex-col items-start gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <CardTitle className="min-w-0 text-base font-semibold">
                    {item.caller_phone}
                    {item.caller_name ? ` · ${item.caller_name}` : ""}
                  </CardTitle>
                  <div className="flex flex-wrap items-center gap-2">
                    {item.urgency === "urgent" && (
                      <Badge variant="destructive">Urgent</Badge>
                    )}
                    <Badge className={cn(STATUS_STYLES[item.status])}>
                      {item.status}
                    </Badge>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {item.reason}
                </p>
                <div className="flex flex-col items-start gap-3 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
                  <span>
                    {new Date(item.created_at).toLocaleString()}
                    {item.notified ? " · owner alerted" : " · logged manually"}
                  </span>
                  {canManage && item.status !== "resolved" && (
                    <div className="flex w-full flex-wrap gap-2 sm:w-auto">
                      {item.status === "new" && (
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={markStatus.isPending}
                          onClick={() =>
                            markStatus.mutate({
                              escalationId: item.id,
                              status: "acknowledged",
                            })
                          }
                        >
                          Acknowledge
                        </Button>
                      )}
                      <Button
                        size="sm"
                        disabled={markStatus.isPending}
                        onClick={() =>
                          markStatus.mutate({
                            escalationId: item.id,
                            status: "resolved",
                          })
                        }
                      >
                        Mark resolved
                      </Button>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
