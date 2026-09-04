"use client";

/**
 * Platform Interest page (platform admin only).
 *
 * The owner-visible home for every captured lead: request-demo form,
 * outcome-page form, demo calls, and manual entries. Advance rows
 * through new → contacted → invited → converted (or dropped).
 * Star ratings live in the PostHog demo funnel, not here, by design.
 */

import React, { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/contexts/auth-context";
import { AccessDenied } from "@/components/ui/access-denied";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Loader2 } from "lucide-react";
import {
  leadService,
  type InterestLead,
  type InterestLeadStatus,
} from "@/services/lead-service";

const STATUS_FILTERS: Array<{ value: string; label: string }> = [
  { value: "all", label: "All statuses" },
  { value: "new", label: "New" },
  { value: "contacted", label: "Contacted" },
  { value: "invited", label: "Invited" },
  { value: "converted", label: "Converted" },
  { value: "dropped", label: "Dropped" },
];

const NEXT_STATUS: Partial<Record<InterestLeadStatus, InterestLeadStatus>> = {
  new: "contacted",
  contacted: "invited",
  invited: "converted",
};

export default function PlatformInterestPage() {
  const { user } = useAuth();
  // Depend on the primitive, not the user object identity: context value
  // identities can change per render, which would refetch in a loop.
  const isPlatformAdmin = user?.hasRole("platform_admin") ?? false;
  const [statusFilter, setStatusFilter] = useState("all");
  const [leads, setLeads] = useState<InterestLead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  const loadLeads = useCallback(async (status: string) => {
    setLoading(true);
    setError(null);
    const result = await leadService.listInterestLeads(
      status === "all" ? undefined : (status as InterestLeadStatus),
    );
    if (result.success) {
      setLeads(result.data ?? []);
    } else {
      setError(result.error || "Could not load interest.");
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    if (isPlatformAdmin) {
      void loadLeads(statusFilter);
    }
  }, [isPlatformAdmin, statusFilter, loadLeads]);

  async function advanceLead(lead: InterestLead) {
    const next = NEXT_STATUS[lead.status];
    if (!next) return;
    setUpdatingId(lead.id);
    const result = await leadService.updateInterestLeadStatus(lead.id, next);
    if (result.success && result.data) {
      setLeads((current) =>
        current.map((row) => (row.id === lead.id ? result.data as InterestLead : row)),
      );
    } else {
      setError(result.error || "Could not update the lead.");
    }
    setUpdatingId(null);
  }

  // Frontend authz gate. Backend enforces platform_admin independently.
  if (!isPlatformAdmin) {
    return (
      <AccessDenied
        title="Access Denied"
        description="You do not have permission to access this page. Only platform administrators can review interest."
        redirectPath="/dashboard"
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Interest</h1>
          <p className="text-muted-foreground mt-1">
            Every captured lead, newest first. Work them new → contacted →
            invited → converted.
          </p>
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-48" aria-label="Filter by status">
            <SelectValue placeholder="All statuses" />
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

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {loading ? (
        <div className="flex items-center gap-2 text-muted-foreground">
          <Loader2 className="w-4 h-4 animate-spin" />
          Loading interest…
        </div>
      ) : leads.length === 0 ? (
        <Card>
          <CardContent className="py-10 text-center text-muted-foreground">
            No interest yet. Demo calls, outcome forms, and the request page
            land here.
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-0 overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Contact</TableHead>
                  <TableHead>Business</TableHead>
                  <TableHead>Source</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Received</TableHead>
                  <TableHead className="text-right">Next step</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {leads.map((lead) => (
                  <TableRow key={lead.id} data-testid={`interest-row-${lead.id}`}>
                    <TableCell>
                      <div className="font-medium">{lead.name}</div>
                      <div className="text-xs text-muted-foreground">
                        {lead.email}
                      </div>
                      {lead.message && (
                        <div
                          className="text-xs text-muted-foreground mt-1 max-w-xs truncate"
                          title={lead.message}
                        >
                          {lead.message}
                        </div>
                      )}
                    </TableCell>
                    <TableCell>
                      {lead.business_name || "—"}
                      {lead.vertical && (
                        <div className="text-xs text-muted-foreground">
                          {lead.vertical}
                        </div>
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{lead.source}</Badge>
                      {lead.demo_slug && (
                        <div className="text-xs text-muted-foreground mt-1">
                          {lead.demo_slug}
                        </div>
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge>{lead.status}</Badge>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {new Date(lead.created_at).toLocaleString()}
                    </TableCell>
                    <TableCell className="text-right">
                      {NEXT_STATUS[lead.status] ? (
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={updatingId === lead.id}
                          onClick={() => void advanceLead(lead)}
                        >
                          Mark {NEXT_STATUS[lead.status]}
                        </Button>
                      ) : (
                        <span className="text-xs text-muted-foreground">—</span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
