"use client";

import React, { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { CheckCircle, AlertTriangle, Loader2, Coins } from "lucide-react";
import { toast } from "sonner";
import {
  AvailablePhoneNumber,
  formatPhoneNumber,
  getPhoneNumberTypeLabel,
} from "@/types/phone-number";
import type { PhoneNumber } from "@/types/phone-number";
import { phoneNumberService } from "@/services/phone-number-service";

interface PhoneNumberPurchaseProps {
  organizationId: string;
  creditBalance: number;
  selectedNumber: AvailablePhoneNumber | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onPurchaseSuccess?: (phoneNumber: PhoneNumber) => void | Promise<void>;
}

export function PhoneNumberPurchase({
  organizationId,
  creditBalance,
  selectedNumber,
  open,
  onOpenChange,
  onPurchaseSuccess,
}: PhoneNumberPurchaseProps) {
  const [purchasing, setPurchasing] = useState(false);
  const [acknowledged, setAcknowledged] = useState(false);

  const handlePurchase = async () => {
    if (!selectedNumber) return;

    setPurchasing(true);

    try {
      const response = await phoneNumberService.purchaseNumber(organizationId, {
        phone_number: selectedNumber.phone_number,
        country_code: selectedNumber.country_code,
        phone_number_type: selectedNumber.phone_number_type,
        expected_included_in_plan: selectedNumber.is_included_in_plan ?? false,
      });

      if (response.success) {
        toast.success(
          `Successfully purchased ${formatPhoneNumber(selectedNumber.phone_number)}`,
        );
        setAcknowledged(false);
        await onPurchaseSuccess?.(response.phone_number);
        onOpenChange(false);
      }
    } catch (error) {
      console.error("Error purchasing phone number:", error);
      const errorMessage =
        error instanceof Error
          ? error.message
          : "Failed to purchase phone number";
      toast.error(errorMessage);
    } finally {
      setPurchasing(false);
    }
  };

  const handleClose = () => {
    setAcknowledged(false);
    onOpenChange(false);
  };

  if (!selectedNumber) return null;

  const isIncluded = selectedNumber.is_included_in_plan === true;
  const monthlyCost = selectedNumber.monthly_cost_credits;
  const monthlyDollarEquivalent = (monthlyCost / 40)
    .toFixed(2)
    .replace(/\.00$/, "");
  const canAfford = isIncluded || creditBalance >= monthlyCost;
  const newBalance = creditBalance - monthlyCost;

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-h-[calc(100dvh-2rem)] overflow-y-auto sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Coins className="w-5 h-5" />
            Buy Phone Number
          </DialogTitle>
          <DialogDescription>
            Add a phone number for your organization
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="rounded-lg border bg-muted/30 p-3 sm:p-4">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="min-w-0">
                <div className="font-semibold text-lg">
                  {formatPhoneNumber(selectedNumber.phone_number)}
                </div>
                <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                  <Badge className="shrink-0" variant="outline">
                    {getPhoneNumberTypeLabel(selectedNumber.phone_number_type)}
                  </Badge>
                  {selectedNumber.locality && (
                    <span>{selectedNumber.locality}</span>
                  )}
                </div>
              </div>
              <div className="text-left sm:text-right">
                <div className="whitespace-nowrap font-semibold">
                  {isIncluded
                    ? "Included with your plan"
                    : `${monthlyCost} credits/month · $${monthlyDollarEquivalent} equivalent`}
                </div>
                {!isIncluded ? (
                  <div className="text-xs text-muted-foreground">
                    Charged now and monthly from your shared credit balance
                  </div>
                ) : null}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 text-sm">
            <div className="p-3 border rounded-lg">
              <div className="text-muted-foreground">Current Balance</div>
              <div className="font-semibold">{creditBalance} credits</div>
            </div>
            <div className="p-3 border rounded-lg">
              <div className="text-muted-foreground">After Purchase</div>
              <div className="font-semibold">{newBalance} credits</div>
            </div>
          </div>

          {!canAfford && (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                Insufficient credits. You need{" "}
                {monthlyCost} credits but only have{" "}
                {creditBalance}.
              </AlertDescription>
            </Alert>
          )}

          <Alert>
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>
              {isIncluded
                ? "This is your one included US local number while your paid plan is active. Additional US local numbers cost 80 credits per month ($2 equivalent each) from this same balance, which can leave fewer credits for calls. You can also connect a Twilio number you already own at no platform rental cost."
                : `This number costs ${monthlyCost} credits per month ($${monthlyDollarEquivalent} equivalent). The first rental month is charged now, then it renews monthly from the same balance as calls. If you release the number, it is released immediately and the current period is not refunded.`}
            </AlertDescription>
          </Alert>

          {!isIncluded ? (
            <label className="flex items-start gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={acknowledged}
                onChange={(e) => setAcknowledged(e.target.checked)}
                className="mt-1"
              />
              <span className="text-sm text-muted-foreground">
                I understand the first rental month costs {monthlyCost} credits
                now, then renews monthly from my shared balance and may reduce
                call time.
              </span>
            </label>
          ) : null}
        </div>

        <DialogFooter className="gap-2">
          <Button
            className="w-full sm:w-auto"
            variant="outline"
            onClick={handleClose}
            disabled={purchasing}
          >
            Cancel
          </Button>
          <Button
            className="w-full sm:w-auto"
            onClick={handlePurchase}
            disabled={!canAfford || (!isIncluded && !acknowledged) || purchasing}
          >
            {purchasing ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Purchasing...
              </>
            ) : (
              <>
                <CheckCircle className="w-4 h-4 mr-2" />
                Add Number
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
