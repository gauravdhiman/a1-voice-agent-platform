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
import { Loader2, AlertTriangle, Phone } from "lucide-react";
import { phoneNumberService } from "@/services/phone-number-service";
import { PhoneNumberWithAgent, formatPhoneNumber } from "@/types/phone-number";

interface PhoneNumberCancelDialogProps {
  organizationId: string;
  phoneNumber: PhoneNumberWithAgent;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCancelSuccess: (message?: string) => void;
}

function formatMonthlyCreditCost(credits: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(credits / 40);
}

export function PhoneNumberCancelDialog({
  organizationId,
  phoneNumber,
  open,
  onOpenChange,
  onCancelSuccess,
}: PhoneNumberCancelDialogProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmationText, setConfirmationText] = useState("");

  const isCustomerManaged = phoneNumber.management_mode === "customer_managed";
  const expectedConfirmation = isCustomerManaged ? "Disconnect" : "Release";
  const isConfirmationValid = confirmationText === expectedConfirmation;

  const handleCancel = async () => {
    if (!isConfirmationValid) return;

    try {
      setLoading(true);
      setError(null);
      const response = await phoneNumberService.cancelNumber(
        phoneNumber.id,
        organizationId,
      );
      onCancelSuccess(response.message);
    } catch (err: unknown) {
      const error = err as Error;
      console.error("Error cancelling phone number:", err);
      setError(error.message || "Failed to cancel phone number");
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

  const hasAssignedAgent = !!phoneNumber.assigned_agent_id;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-red-600">
            <AlertTriangle className="h-5 w-5" />
            {isCustomerManaged ? "Disconnect Phone Number" : "Release Phone Number"}
          </DialogTitle>
          <DialogDescription>
            {isCustomerManaged
              ? "This disconnects the number from your platform. Twilio ownership and billing remain with you."
              : "This action cannot be undone. The number will be released, calls will stop, you may not be able to get the same number back, and the current billing period is not refunded."}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="flex items-center gap-3 p-3 bg-muted rounded-lg">
            <Phone className="h-5 w-5 text-muted-foreground" />
            <div>
              <div className="font-medium">
                {formatPhoneNumber(phoneNumber.phone_number)}
              </div>
              <div className="text-sm text-muted-foreground">
                {isCustomerManaged
                  ? "Customer-owned Twilio number"
                  : phoneNumber.is_included_in_plan
                    ? "Included with your plan"
                    : `${phoneNumber.monthly_cost_credits} credits/month (${formatMonthlyCreditCost(phoneNumber.monthly_cost_credits)} equivalent)`}
              </div>
            </div>
          </div>

          {hasAssignedAgent && (
            <div className="p-4 bg-amber-50 border border-amber-200 rounded-md">
              <div className="flex items-start gap-3">
                <AlertTriangle className="h-5 w-5 text-amber-600 mt-0.5 flex-shrink-0" />
                <div className="text-sm text-amber-800">
                  <p className="font-medium mb-1">Warning: Assigned Agent</p>
                  <p>
                    This phone number is currently assigned to &quot;
                    {phoneNumber.agent_name}&quot;. Cancelling will remove the
                    phone number from this agent.
                  </p>
                </div>
              </div>
            </div>
          )}

          {error && (
            <div className="p-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded-md">
              {error}
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="confirmation">
              Type <strong>&quot;{expectedConfirmation}&quot;</strong> to confirm
              {isCustomerManaged ? " disconnection" : " release"}:
            </Label>
            <Input
              id="confirmation"
              value={confirmationText}
              onChange={(e) => setConfirmationText(e.target.value)}
              placeholder={expectedConfirmation}
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
              Keep Phone Number
            </Button>
            <Button
              onClick={handleCancel}
              disabled={loading || !isConfirmationValid}
              variant="destructive"
              className="flex-1"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  {isCustomerManaged ? "Disconnecting..." : "Releasing..."}
                </>
              ) : (
                <>
                  <AlertTriangle className="h-4 w-4 mr-2" />
                  {isCustomerManaged ? "Disconnect Number" : "Release Number"}
                </>
              )}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
