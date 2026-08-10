"use client";

import {
  Activity,
  ArrowDownRight,
  ArrowUpRight,
  Clock3,
  Coins,
  Database,
  Sparkles,
  Wallet,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type {
  CreditTransactionWithEvent,
  CreditUsageResponse,
} from "@/types/billing";

interface CreditUsagePanelProps {
  /** Dashboard payload for the selected organization. */
  usage: CreditUsageResponse;
  /** Controls whether the panel renders the summary, details, or both. */
  variant?: "full" | "summary" | "details";
}

function formatCredits(value: number): string {
  return new Intl.NumberFormat("en-US").format(value);
}

function formatDate(value: string): string {
  return new Date(value).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function transactionLabel(transaction: CreditTransactionWithEvent): string {
  return (
    transaction.credit_event?.description ||
    transaction.description ||
    transaction.source.replaceAll("_", " ")
  );
}

/**
 * Credit observatory for organization administrators and platform admins.
 *
 * Shows the live two-pool balance, current-period burn, category breakdown,
 * and the transaction-level explanation behind every movement.
 */
export function CreditUsagePanel({
  usage,
  variant = "full",
}: CreditUsagePanelProps) {
  const { balance } = usage;
  const usagePercent = usage.period_credits_granted
    ? Math.min(
        100,
        Math.round(
          (usage.period_credits_used / usage.period_credits_granted) * 100,
        ),
      )
    : 0;

  const statCards = [
    {
      label: "Available now",
      value: balance.total_credits,
      detail: "combined balance",
      icon: Wallet,
      tone: "text-emerald-600 dark:text-emerald-400",
    },
    {
      label: "Plan pool",
      value: balance.subscription_credits,
      detail: balance.expires_at
        ? `expires ${new Date(balance.expires_at).toLocaleDateString()}`
        : "period credits",
      icon: Sparkles,
      tone: "text-sky-600 dark:text-sky-400",
    },
    {
      label: "Purchased pool",
      value: balance.purchased_credits,
      detail: "does not expire",
      icon: Coins,
      tone: "text-amber-600 dark:text-amber-400",
    },
    {
      label: "Used this period",
      value: usage.period_credits_used,
      detail: `${usagePercent}% of recorded grants`,
      icon: Activity,
      tone: "text-violet-600 dark:text-violet-400",
    },
  ];

  return (
    <div className="space-y-5" data-testid={`credit-usage-panel-${variant}`}>
      {variant !== "details" ? (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {statCards.map(({ label, value, detail, icon: Icon, tone }) => (
            <Card key={label} className="overflow-hidden border-border/70">
              <CardContent className="relative p-4">
                <div className="absolute -right-5 -top-5 h-20 w-20 rounded-full bg-muted/50" />
                <Icon className={`relative h-4 w-4 ${tone}`} />
                <div className="relative mt-3 text-2xl font-semibold tracking-tight">
                  {formatCredits(value)}
                </div>
                <div className="relative mt-1 text-xs font-medium text-muted-foreground">
                  {label}
                </div>
                <div className="relative mt-2 text-[11px] text-muted-foreground/80">
                  {detail}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : null}

      {variant !== "summary" ? (
        <>
          <div className="grid gap-5 lg:grid-cols-[1.1fr_0.9fr]">
            <Card className="border-border/70">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <CardTitle className="text-base">Period burn</CardTitle>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {usage.period_start
                        ? `Since ${new Date(usage.period_start).toLocaleDateString()}`
                        : "Recorded credit movements"}
                    </p>
                  </div>
                  <Badge variant="secondary" className="font-mono text-[11px]">
                    {formatCredits(usage.period_credits_remaining)} remaining
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="h-3 overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-sky-500 via-violet-500 to-fuchsia-500 transition-all"
                    style={{ width: `${usagePercent}%` }}
                  />
                </div>
                <div className="mt-3 flex items-center justify-between text-xs">
                  <span className="font-medium text-foreground">
                    {formatCredits(usage.period_credits_used)} used
                  </span>
                  <span className="text-muted-foreground">
                    {formatCredits(usage.period_credits_granted)} granted
                  </span>
                </div>
                <div className="mt-5 grid gap-3 sm:grid-cols-2">
                  <div className="rounded-lg border border-border/60 bg-muted/20 p-3">
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <Database className="h-3.5 w-3.5" />
                      Expiring soon
                    </div>
                    <div className="mt-2 text-lg font-semibold">
                      {formatCredits(balance.expiring_soon)}
                    </div>
                  </div>
                  <div className="rounded-lg border border-border/60 bg-muted/20 p-3">
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <Clock3 className="h-3.5 w-3.5" />
                      Categories tracked
                    </div>
                    <div className="mt-2 text-lg font-semibold">
                      {usage.usage_by_category.length}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-border/70">
              <CardHeader className="pb-3">
                <CardTitle className="text-base">Where credits went</CardTitle>
                <p className="text-xs text-muted-foreground">
                  Grouped by metered event category
                </p>
              </CardHeader>
              <CardContent>
                {usage.usage_by_category.length === 0 ? (
                  <p className="py-8 text-center text-sm text-muted-foreground">
                    No consumption recorded for this period.
                  </p>
                ) : (
                  <div className="space-y-4">
                    {usage.usage_by_category.map((category) => {
                      const share = usage.period_credits_used
                        ? Math.round(
                            (category.credits_consumed /
                              usage.period_credits_used) *
                              100,
                          )
                        : 0;
                      return (
                        <div key={category.category}>
                          <div className="flex items-center justify-between gap-3 text-sm">
                            <span className="font-medium capitalize">
                              {category.category.replaceAll("_", " ")}
                            </span>
                            <span className="font-mono text-xs text-muted-foreground">
                              {formatCredits(category.credits_consumed)} ·{" "}
                              {share}%
                            </span>
                          </div>
                          <div className="mt-2 h-1.5 rounded-full bg-muted">
                            <div
                              className="h-full rounded-full bg-foreground/70"
                              style={{ width: `${share}%` }}
                            />
                          </div>
                          <div className="mt-1 text-[11px] text-muted-foreground">
                            {category.transaction_count} transaction
                            {category.transaction_count === 1 ? "" : "s"}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          <Card className="border-border/70">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Credit ledger</CardTitle>
              <p className="text-xs text-muted-foreground">
                Every grant, purchase, expiry, and consumption event is
                auditable.
              </p>
            </CardHeader>
            <CardContent className="p-0">
              {usage.transactions.length === 0 ? (
                <div className="px-5 py-10 text-center text-sm text-muted-foreground">
                  No ledger entries yet.
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Date</TableHead>
                      <TableHead>Activity</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead className="text-right">Amount</TableHead>
                      <TableHead className="text-right">Balance</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {usage.transactions.map((transaction) => {
                      const isCredit = transaction.amount >= 0;
                      return (
                        <TableRow key={transaction.id}>
                          <TableCell className="whitespace-nowrap text-xs text-muted-foreground">
                            {formatDate(transaction.created_at)}
                          </TableCell>
                          <TableCell className="max-w-[260px] font-medium">
                            <span className="block truncate">
                              {transactionLabel(transaction)}
                            </span>
                            {transaction.credit_event?.name && (
                              <span className="block truncate font-mono text-[10px] text-muted-foreground">
                                {transaction.credit_event.name}
                              </span>
                            )}
                          </TableCell>
                          <TableCell>
                            <Badge
                              variant="outline"
                              className="capitalize text-[10px]"
                            >
                              {transaction.transaction_type}
                            </Badge>
                          </TableCell>
                          <TableCell
                            className={`text-right font-mono text-xs ${isCredit ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400"}`}
                          >
                            <span className="inline-flex items-center gap-1">
                              {isCredit ? (
                                <ArrowUpRight className="h-3 w-3" />
                              ) : (
                                <ArrowDownRight className="h-3 w-3" />
                              )}
                              {isCredit ? "+" : ""}
                              {formatCredits(transaction.amount)}
                            </span>
                          </TableCell>
                          <TableCell className="text-right font-mono text-xs">
                            {formatCredits(transaction.balance_after)}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </>
      ) : null}
    </div>
  );
}
