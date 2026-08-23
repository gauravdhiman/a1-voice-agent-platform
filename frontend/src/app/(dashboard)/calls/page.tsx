"use client";

import React, { useState, useCallback, useMemo, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { useOrganization } from "@/contexts/organization-context";
import { useMyAgents } from "@/hooks/use-agent-queries";
import { useCallLogs } from "@/hooks/use-call-logs";
import { useOrganizationById } from "@/hooks/use-organization-by-id";
import type { CallLogListParams } from "@/services/call-log-service";
import { CallLogList } from "@/components/calls/call-log-list";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Phone,
  Loader2,
  AlertTriangle,
  ShieldCheck,
} from "lucide-react";
import { useUserPermissions } from "@/hooks/use-user-permissions";

const STATUS_OPTIONS = [
  { value: "", label: "All Statuses" },
  { value: "initiated", label: "Initiated" },
  { value: "ringing", label: "Ringing" },
  { value: "answered", label: "Answered" },
  { value: "completed", label: "Completed" },
  { value: "missed", label: "Missed" },
  { value: "failed", label: "Failed" },
  { value: "busy", label: "Busy" },
  { value: "no-answer", label: "No Answer" },
];

export default function CallsPage() {
  const { currentOrganization, setCurrentOrganization } = useOrganization();
  const searchParams = useSearchParams();
  const requestedOrgId = searchParams.get("org_id");
  const orgId = requestedOrgId ?? currentOrganization?.id ?? "";
  const {
    isValid: isOrgValid,
    loading: organizationLoading,
    organization: validatedOrganization,
  } = useOrganizationById(orgId || null);
  const { data: agents = [] } = useMyAgents();
  const { isOrgAdmin, isPlatformAdmin, canDeleteRecordings } =
    useUserPermissions();

  const [agentFilter, setAgentFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [page, setPage] = useState(1);

  const params: CallLogListParams = useMemo(
    () => ({
      agent_id: agentFilter || undefined,
      status: statusFilter || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
      page,
      page_size: 25,
    }),
    [agentFilter, statusFilter, dateFrom, dateTo, page],
  );

  useEffect(() => {
    if (
      validatedOrganization &&
      validatedOrganization.id !== currentOrganization?.id
    ) {
      setCurrentOrganization(validatedOrganization);
    }
  }, [validatedOrganization, currentOrganization, setCurrentOrganization]);

  const { data, isLoading, isFetching, error, refetch } = useCallLogs(
    orgId,
    params,
  );

  const handleFilterChange = useCallback(() => {
    setPage(1);
  }, []);

  // Agent name lookup map
  const agentNameMap = useMemo(
    () => Object.fromEntries(agents.map((a) => [a.id, a.name])),
    [agents],
  );

  if (!orgId) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-muted-foreground">No organization selected.</p>
      </div>
    );
  }

  if (organizationLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        <p className="ml-2 text-muted-foreground">Loading organization…</p>
      </div>
    );
  }

  if (!isOrgValid) {
    return (
      <Alert variant="destructive">
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription>
          You do not have access to this organization&apos;s call reports.
        </AlertDescription>
      </Alert>
    );
  }

  const organizationName =
    validatedOrganization?.name ??
    currentOrganization?.name ??
    "the organization";

  return (
    <div className="space-y-6" data-tour="calls-page">
      {/* Header */}
      <div className="flex items-center space-x-4">
        <div className="bg-primary/10 p-3 rounded-lg">
          <Phone className="h-6 w-6 text-primary" />
        </div>
        <div>
          <h1 className="text-2xl font-bold">Call Log</h1>
          <p className="text-sm text-muted-foreground">
            History of all incoming calls for {organizationName}
          </p>
        </div>
      </div>

      {isOrgAdmin || isPlatformAdmin ? (
        <Alert className="border-primary/20 bg-primary/5">
          <ShieldCheck className="h-4 w-4 text-primary" />
          <AlertDescription>
            <p className="font-medium text-foreground">
              Recording privacy, security, and retention
            </p>
            <p className="mt-1">
              Recordings are private and available only to organization and
              platform admins through authenticated access. Staging and
              production recordings use private, provider-encrypted storage;
              local development recordings stay in the ignored local data
              directory. Recordings are retained according to the configured
              policy, which defaults to 90 days, and may be removed earlier.
              Ensure callers are notified and consent requirements are met
              before using recordings, including any applicable regulatory
              requirements for your jurisdiction.
            </p>
          </AlertDescription>
        </Alert>
      ) : null}

      {/* Filters */}
      <Card data-tour="calls-filters">
        <CardHeader>
          <CardTitle className="text-base">Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Agent filter */}
            <div>
              <label className="block text-sm font-medium text-muted-foreground mb-1">
                Agent
              </label>
              <select
                value={agentFilter}
                onChange={(e) => {
                  setAgentFilter(e.target.value);
                  handleFilterChange();
                }}
                className="w-full px-3 py-2 border border-input bg-background rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="">All Agents</option>
                {agents.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Status filter */}
            <div>
              <label className="block text-sm font-medium text-muted-foreground mb-1">
                Status
              </label>
              <select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  handleFilterChange();
                }}
                className="w-full px-3 py-2 border border-input bg-background rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              >
                {STATUS_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Date from */}
            <div>
              <label
                htmlFor="call-date-from"
                className="block text-sm font-medium text-muted-foreground mb-1"
              >
                From
              </label>
              <input
                id="call-date-from"
                type="date"
                value={dateFrom}
                onChange={(e) => {
                  const nextFrom = e.target.value;
                  setDateFrom(nextFrom);
                  if (nextFrom && dateTo && dateTo < nextFrom) {
                    setDateTo("");
                  }
                  handleFilterChange();
                }}
                className="w-full px-3 py-2 border border-input bg-background rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            {/* Date to */}
            <div>
              <label
                htmlFor="call-date-to"
                className="block text-sm font-medium text-muted-foreground mb-1"
              >
                To
              </label>
              <input
                id="call-date-to"
                type="date"
                value={dateTo}
                min={dateFrom || undefined}
                onChange={(e) => {
                  setDateTo(e.target.value);
                  handleFilterChange();
                }}
                className="w-full px-3 py-2 border border-input bg-background rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      <CallLogList
        data={data}
        isLoading={isLoading}
        isFetching={isFetching}
        error={error}
        onRefresh={() => refetch()}
        onPageChange={setPage}
        agentNameMap={agentNameMap}
        showAgentColumn
        canViewRecordings={isOrgAdmin || isPlatformAdmin}
        canDeleteRecordings={canDeleteRecordings}
        organizationId={orgId || undefined}
        title="Recent Calls"
        dataTour="calls-results"
      />
    </div>
  );
}
