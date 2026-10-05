"use client";

import React, { useState } from "react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { billingService } from "@/services/billing-service";
import type { OrgEntitlements } from "@/types/billing";
import { friendlyPlanLabel } from "@/components/billing/plan-card";
import { differenceInCalendarDays, format, parseISO } from "date-fns";
import { ArrowUpCircle, Clock, Loader2 } from "lucide-react";
import { toast } from "sonner";

interface PlanMigrationBannerProps {
  organizationId: string;
  entitlements: OrgEntitlements;
  onMigrated?: () => void;
}

/**
 * Displays legacy plan version badge, grace countdown, and self-service migrate CTA.
 */
export function PlanMigrationBanner({
  organizationId,
  entitlements,
  onMigrated,
}: PlanMigrationBannerProps) {
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [migrating, setMigrating] = useState(false);

  const migration = entitlements.migration;
  const currentPlanLabel = friendlyPlanLabel(
    entitlements.plan_version_label,
    entitlements.plan_product_slug,
  );
  const targetPlanLabel = friendlyPlanLabel(
    migration?.target_plan_version_label,
    migration?.target_plan_product_slug,
  );
  const showLegacyBadge =
    entitlements.is_legacy_version && !migration && entitlements.plan_version_label;

  if (!migration && !showLegacyBadge) {
    return null;
  }

  const graceDaysRemaining = migration?.grace_period_ends_at
    ? Math.max(
        0,
        differenceInCalendarDays(
          parseISO(migration.grace_period_ends_at),
          new Date(),
        ),
      )
    : null;

  const handleMigrate = async () => {
    try {
      setMigrating(true);
      await billingService.migrateSubscriptionPlan(organizationId);
      toast.success("Your plan has been upgraded successfully");
      setConfirmOpen(false);
      onMigrated?.();
    } catch (error) {
      console.error("Plan migration failed:", error);
      toast.error("Failed to upgrade plan. Please try again or contact support.");
    } finally {
      setMigrating(false);
    }
  };

  return (
    <>
      <Alert className="border-amber-200 bg-amber-50">
        <Clock className="h-4 w-4 text-amber-700" />
        <AlertDescription className="text-amber-900 space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            {entitlements.plan_version_label ? (
              <Badge variant="outline" className="border-amber-300 bg-white">
                {currentPlanLabel}
                {entitlements.is_legacy_version ? " — legacy" : ""}
              </Badge>
            ) : null}
            {showLegacyBadge && !migration ? (
              <span className="text-sm">
                You are on a legacy plan version. New signups receive updated
                pricing and limits.
              </span>
            ) : null}
          </div>

          {migration ? (
            <div className="space-y-2 text-sm">
              <p>
                A newer plan version
                {migration.target_plan_version_label
                  ? ` (${targetPlanLabel})`
                  : ""}{" "}
                is available.
                {graceDaysRemaining !== null ? (
                  <>
                    {" "}
                    Grace period ends in{" "}
                    <strong>
                      {graceDaysRemaining}{" "}
                      {graceDaysRemaining === 1 ? "day" : "days"}
                    </strong>
                    {migration.grace_period_ends_at
                      ? ` (${format(parseISO(migration.grace_period_ends_at), "MMM d, yyyy")})`
                      : ""}
                    .
                  </>
                ) : null}
              </p>
              {migration.can_self_migrate ? (
                <Button
                  size="sm"
                  onClick={() => setConfirmOpen(true)}
                  className="bg-amber-700 hover:bg-amber-800"
                >
                  <ArrowUpCircle className="w-4 h-4 mr-2" />
                  Upgrade to{" "}
                  {migration.target_plan_version_label
                    ? targetPlanLabel
                    : "latest version"}
                </Button>
              ) : null}
            </div>
          ) : null}
        </AlertDescription>
      </Alert>

      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Upgrade plan version</DialogTitle>
            <DialogDescription>
              You will move to{" "}
              {migration?.target_plan_version_label
                ? targetPlanLabel
                : "the latest plan version"}.
              Your billing may change according to the new plan price.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              variant="outline"
              onClick={() => setConfirmOpen(false)}
              disabled={migrating}
            >
              Not now
            </Button>
            <Button onClick={handleMigrate} disabled={migrating}>
              {migrating ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Upgrading...
                </>
              ) : (
                "Confirm upgrade"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
