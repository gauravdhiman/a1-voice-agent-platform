"use client";

import * as React from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { adminPlanService } from "@/services/admin-plan-service";
import type {
  MigrationMode,
  PlanVersionDetail,
  PlanVersionPublishRequest,
  StripeMigrationTiming,
} from "@/types/admin-plans";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";

interface PlanPublishDialogProps {
  version: PlanVersionDetail | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onPublished?: () => void;
}

const MIGRATION_MODES: { value: MigrationMode; label: string }[] = [
  { value: "new_signups_only", label: "New signups only (grandfather existing)" },
  {
    value: "grace_then_optional",
    label: "Grace period, then optional migration",
  },
  {
    value: "grace_then_required",
    label: "Grace period, then required migration",
  },
  { value: "immediate_required", label: "Migrate all subscribers immediately" },
];

const STRIPE_TIMINGS: { value: StripeMigrationTiming; label: string }[] = [
  { value: "at_period_end", label: "At billing period end" },
  { value: "at_grace_end", label: "When grace period ends" },
  { value: "immediate", label: "Immediately" },
];

export const PUBLISH_CONFIRMATION_PHRASE = "PUBLISH PLAN";

/**
 * Dialog for publishing a draft plan version with migration policy controls.
 */
export function PlanPublishDialog({
  version,
  open,
  onOpenChange,
  onPublished,
}: PlanPublishDialogProps) {
  const [migrationMode, setMigrationMode] =
    React.useState<MigrationMode>("new_signups_only");
  const [gracePeriodDays, setGracePeriodDays] = React.useState("30");
  const [autoMigrateOnExpiry, setAutoMigrateOnExpiry] = React.useState(false);
  const [allowIndefiniteLegacy, setAllowIndefiniteLegacy] = React.useState(true);
  const [stripeTiming, setStripeTiming] =
    React.useState<StripeMigrationTiming>("at_period_end");
  const [confirmationText, setConfirmationText] = React.useState("");
  const [publishing, setPublishing] = React.useState(false);

  React.useEffect(() => {
    if (open) {
      setMigrationMode("new_signups_only");
      setGracePeriodDays("30");
      setAutoMigrateOnExpiry(false);
      setAllowIndefiniteLegacy(true);
      setStripeTiming("at_period_end");
      setConfirmationText("");
    }
  }, [open, version?.id]);

  const needsGrace =
    migrationMode === "grace_then_optional" ||
    migrationMode === "grace_then_required";
  const isPaidPlan = version?.billing_mode !== "free";
  const confirmationMatches = confirmationText === PUBLISH_CONFIRMATION_PHRASE;

  const handlePublish = async () => {
    if (!version || !confirmationMatches) return;
    const body: PlanVersionPublishRequest = {
      migration_mode: migrationMode,
      grace_period_days: needsGrace ? Number(gracePeriodDays) || 0 : null,
      auto_migrate_on_expiry: autoMigrateOnExpiry,
      allow_indefinite_legacy: allowIndefiniteLegacy,
      stripe_migration_timing: isPaidPlan ? stripeTiming : "at_period_end",
      compliance_policy: "soft_block",
    };

    try {
      setPublishing(true);
      await adminPlanService.publishPlanVersion(version.id, body);
      toast.success("Plan version published");
      onOpenChange(false);
      onPublished?.();
    } catch (error) {
      console.error("Publish failed:", error);
      const message =
        (error as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ??
        (error instanceof Error ? error.message : "Failed to publish plan version");
      toast.error("Failed to publish plan version", { description: String(message) });
    } finally {
      setPublishing(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Publish plan version</DialogTitle>
          <DialogDescription>
            {version
              ? version.billing_mode === "free"
                ? `Publish v${version.version_number}${
                    version.display_label ? ` (${version.display_label})` : ""
                  }. Free plans activate in the application without payment processing. Existing subscribers keep their current version unless migration policy requires a change.`
                : `Publish v${version.version_number}${
                    version.display_label ? ` (${version.display_label})` : ""
                  }. A Stripe Price is created automatically unless you saved price_… on the draft. Existing subscribers keep their current version unless migration policy requires a change.`
              : "Select a draft version to publish."}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm">
            <p className="font-medium text-destructive">Publishing is irreversible.</p>
            <p className="mt-1 text-muted-foreground">
              Type <code className="rounded bg-muted px-1 py-0.5 font-mono text-xs">{PUBLISH_CONFIRMATION_PHRASE}</code> to confirm you are ready to publish this version.
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="publish-confirmation">
              Type {PUBLISH_CONFIRMATION_PHRASE} to confirm
            </Label>
            <Input
              id="publish-confirmation"
              value={confirmationText}
              onChange={(event) => setConfirmationText(event.target.value)}
              placeholder={PUBLISH_CONFIRMATION_PHRASE}
              autoComplete="off"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="migration-mode">Migration policy</Label>
            <Select
              value={migrationMode}
              onValueChange={(v) => setMigrationMode(v as MigrationMode)}
            >
              <SelectTrigger id="migration-mode">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {MIGRATION_MODES.map((mode) => (
                  <SelectItem key={mode.value} value={mode.value}>
                    {mode.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {needsGrace ? (
            <div className="space-y-2">
              <Label htmlFor="grace-days">Grace period (days)</Label>
              <Input
                id="grace-days"
                type="number"
                min={0}
                value={gracePeriodDays}
                onChange={(e) => setGracePeriodDays(e.target.value)}
              />
            </div>
          ) : null}

          {isPaidPlan ? (
            <div className="space-y-2">
              <Label htmlFor="stripe-timing">Stripe price change timing</Label>
              <Select
                value={stripeTiming}
                onValueChange={(v) => setStripeTiming(v as StripeMigrationTiming)}
              >
                <SelectTrigger id="stripe-timing">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {STRIPE_TIMINGS.map((timing) => (
                    <SelectItem key={timing.value} value={timing.value}>
                      {timing.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          ) : null}

          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={autoMigrateOnExpiry}
              onChange={(e) => setAutoMigrateOnExpiry(e.target.checked)}
            />
            Auto-migrate when grace period ends
          </label>

          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={allowIndefiniteLegacy}
              onChange={(e) => setAllowIndefiniteLegacy(e.target.checked)}
            />
            Allow subscribers to stay on legacy version indefinitely
          </label>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={handlePublish}
            disabled={!version || publishing || !confirmationMatches}
          >
            {publishing ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Publishing…
              </>
            ) : (
              "Publish"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
