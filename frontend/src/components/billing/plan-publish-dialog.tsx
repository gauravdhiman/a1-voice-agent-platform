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
  const [publishing, setPublishing] = React.useState(false);

  React.useEffect(() => {
    if (open) {
      setMigrationMode("new_signups_only");
      setGracePeriodDays("30");
      setAutoMigrateOnExpiry(false);
      setAllowIndefiniteLegacy(true);
      setStripeTiming("at_period_end");
    }
  }, [open, version?.id]);

  const needsGrace =
    migrationMode === "grace_then_optional" ||
    migrationMode === "grace_then_required";

  const handlePublish = async () => {
    if (!version) return;
    const body: PlanVersionPublishRequest = {
      migration_mode: migrationMode,
      grace_period_days: needsGrace ? Number(gracePeriodDays) || 0 : null,
      auto_migrate_on_expiry: autoMigrateOnExpiry,
      allow_indefinite_legacy: allowIndefiniteLegacy,
      stripe_migration_timing: stripeTiming,
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
      toast.error("Failed to publish plan version");
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
              ? `Publish v${version.version_number}${
                  version.display_label ? ` (${version.display_label})` : ""
                }. Existing subscribers keep their current version unless migration policy requires a change.`
              : "Select a draft version to publish."}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
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
          <Button onClick={handlePublish} disabled={!version || publishing}>
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
