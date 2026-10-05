"use client";

import React, { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2, AlertTriangle } from "lucide-react";
import { format } from "date-fns";

interface CancelSubscriptionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCancel: () => void;
  /** End of current billing period — full access continues until this date. */
  accessUntil?: string | Date | null;
}

/**
 * Confirmation dialog for cancel-at-period-end subscription cancellation.
 *
 * Policy: no refunds; entitlements remain until `accessUntil` (current period end).
 */
export function CancelSubscriptionDialog({
  open,
  onOpenChange,
  onCancel,
  accessUntil,
}: CancelSubscriptionDialogProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmationText, setConfirmationText] = useState("");

  const expectedConfirmation = "Cancel subscription";
  const isConfirmationValid = confirmationText === expectedConfirmation;

  const accessUntilLabel = accessUntil
    ? format(new Date(accessUntil), "MMMM d, yyyy")
    : "the end of your current billing period";

  const handleConfirm = async () => {
    if (!isConfirmationValid) return;

    try {
      setLoading(true);
      setError(null);
      await onCancel();
    } catch (err: unknown) {
      const error = err as Error;
      console.error("Error cancelling subscription:", err);
      setError(error.message || "Failed to cancel subscription");
    } finally {
      setLoading(false);
    }
  };

  const handleOpenChange = (newOpen: boolean) => {
    if (!loading) {
      onOpenChange(newOpen);
      if (!newOpen) {
        setConfirmationText("");
        setError(null);
      }
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-red-600">
            <AlertTriangle className="h-5 w-5" />
            Cancel Subscription
          </DialogTitle>
          <DialogDescription>
            Your subscription will stay active until {accessUntilLabel}. You
            will not be charged again after that date, and no refund is issued
            for the current period.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {error && (
            <div className="p-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded-md">
              {error}
            </div>
          )}

          <div className="p-4 bg-red-50 border border-red-200 rounded-md">
            <div className="flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-red-600 mt-0.5 flex-shrink-0" />
              <div className="text-sm text-red-800">
                <p className="font-medium mb-1">
                  Important: Cancellation Details
                </p>
                <ul className="space-y-1 text-red-700">
                  <li>
                    • Full plan access continues until {accessUntilLabel}
                  </li>
                  <li>• You will not be charged for the next billing period</li>
                  <li>• No refund is issued for the current billing period</li>
                  <li>
                    • After {accessUntilLabel}, your organization moves to the
                    free tier unless you resubscribe
                  </li>
                  <li>
                    • Your included US local number stays included through that
                    date. If you keep it, it renews at 80 credits per month
                    from your shared balance after paid access ends. Release it
                    before its next renewal to avoid that add-on charge.
                  </li>
                  <li>
                    • You can reactivate anytime before {accessUntilLabel}
                  </li>
                </ul>
              </div>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="confirmation">
              Type <strong>&quot;{expectedConfirmation}&quot;</strong> to
              confirm cancellation:
            </Label>
            <Input
              id="confirmation"
              value={confirmationText}
              onChange={(e) => setConfirmationText(e.target.value)}
              placeholder="Cancel subscription"
              disabled={loading}
              className="font-mono"
            />
          </div>

          <div className="flex gap-3 pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={() => handleOpenChange(false)}
              disabled={loading}
              className="flex-1"
            >
              Keep Subscription
            </Button>
            <Button
              onClick={handleConfirm}
              disabled={loading || !isConfirmationValid}
              variant="destructive"
              className="flex-1"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Cancelling...
                </>
              ) : (
                "Cancel Subscription"
              )}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
