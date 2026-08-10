"use client";

import { useRef, useState } from "react";
import { Coins, Loader2, ShieldCheck } from "lucide-react";
import { toast } from "sonner";

import { billingService } from "@/services/billing-service";
import type { AdminCreditGrantResponse } from "@/types/billing";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

interface AdminCreditGrantProps {
  /** Organization receiving the platform-admin allocation. */
  organizationId: string;
  /** Called after the backend accepts a new or idempotent grant. */
  onGranted?: (result: AdminCreditGrantResponse) => void;
}

/**
 * Platform-admin-only control for adding auditable, non-expiring bonus credits.
 *
 * The component explains the accounting boundary directly in the UI: a grant
 * changes neither the organization's subscribed plan nor its purchased pool.
 * The API repeats the permission check, so hiding this control is only a UX
 * affordance and never the security boundary.
 */
export function AdminCreditGrant({
  organizationId,
  onGranted,
}: AdminCreditGrantProps) {
  const [open, setOpen] = useState(false);
  const [credits, setCredits] = useState("");
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const idempotencyKey = useRef<string | null>(null);

  const parsedCredits = Number(credits);
  const canSubmit =
    Number.isInteger(parsedCredits) &&
    parsedCredits > 0 &&
    parsedCredits <= 10_000_000 &&
    reason.trim().length >= 3 &&
    reason.trim().length <= 500;

  const reset = () => {
    setCredits("");
    setReason("");
    setError(null);
    idempotencyKey.current = null;
  };

  const handleOpenChange = (nextOpen: boolean) => {
    setOpen(nextOpen);
    if (!nextOpen && !submitting) reset();
  };

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);

    try {
      idempotencyKey.current ??= `platform-credit-${organizationId}-${Date.now()}`;
      const result = await billingService.allocateAdminCredits(organizationId, {
        credits: parsedCredits,
        reason: reason.trim(),
        idempotency_key: idempotencyKey.current,
      });
      onGranted?.(result);
      toast.success(
        result.created
          ? `${parsedCredits.toLocaleString()} platform credits allocated`
          : "This credit allocation was already applied",
      );
      setOpen(false);
      reset();
    } catch (submissionError) {
      const message =
        submissionError instanceof Error
          ? submissionError.message
          : "Unable to allocate platform credits";
      setError(message);
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Card className="border-primary/20 bg-primary/[0.02]">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-4">
          <div>
            <CardTitle className="flex items-center gap-2 text-base">
              <ShieldCheck className="h-4 w-4 text-primary" />
              Platform credit allocation
            </CardTitle>
            <CardDescription className="mt-1">
              Add non-expiring bonus credits for a support or business reason.
              This does not change the organization&apos;s plan or purchased
              pool.
            </CardDescription>
          </div>
          <Coins className="h-5 w-5 text-primary" />
        </div>
      </CardHeader>
      <CardContent>
        <Dialog open={open} onOpenChange={handleOpenChange}>
          <DialogTrigger asChild>
            <Button type="button" variant="outline">
              <Coins className="h-4 w-4" />
              Allocate platform credits
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Allocate platform credits</DialogTitle>
              <DialogDescription>
                This allocation is recorded with your identity and reason. It
                will be consumed after plan credits and before purchased
                credits.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="admin-credit-amount">Credit amount</Label>
                <Input
                  id="admin-credit-amount"
                  type="number"
                  min={1}
                  max={10_000_000}
                  step={1}
                  inputMode="numeric"
                  value={credits}
                  onChange={(event) => setCredits(event.target.value)}
                  placeholder="e.g. 500"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="admin-credit-reason">Reason</Label>
                <Textarea
                  id="admin-credit-reason"
                  value={reason}
                  onChange={(event) => setReason(event.target.value)}
                  placeholder="e.g. Support compensation for an outage"
                  maxLength={500}
                />
                <p className="text-xs text-muted-foreground">
                  {reason.length}/500 characters
                </p>
              </div>
              {error && (
                <Alert variant="destructive">
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => handleOpenChange(false)}
                disabled={submitting}
              >
                Cancel
              </Button>
              <Button
                type="button"
                onClick={() => void handleSubmit()}
                disabled={!canSubmit || submitting}
              >
                {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
                Grant credits
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </CardContent>
    </Card>
  );
}
