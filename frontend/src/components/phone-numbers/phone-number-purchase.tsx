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
        error instanceof Error ? error.message : "Failed to purchase phone number";
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

  const canAfford = creditBalance >= selectedNumber.monthly_cost_credits;
  const newBalance = creditBalance - selectedNumber.monthly_cost_credits;

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Coins className="w-5 h-5" />
            Buy Phone Number
          </DialogTitle>
          <DialogDescription>
            Purchase a new phone number for your organization
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="p-4 border rounded-lg bg-muted/30">
            <div className="flex items-center justify-between">
              <div>
                <div className="font-semibold text-lg">
                  {formatPhoneNumber(selectedNumber.phone_number)}
                </div>
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Badge variant="outline">
                    {getPhoneNumberTypeLabel(selectedNumber.phone_number_type)}
                  </Badge>
                  {selectedNumber.locality && (
                    <span>{selectedNumber.locality}</span>
                  )}
                </div>
              </div>
              <div className="text-right">
                <div className="font-semibold">
                  {selectedNumber.monthly_cost_credits} credits
                </div>
                <div className="text-xs text-muted-foreground">per month</div>
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
                Insufficient credits. You need {selectedNumber.monthly_cost_credits}{" "}
                credits but only have {creditBalance}.
              </AlertDescription>
            </Alert>
          )}

          <Alert>
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>
              By purchasing, you agree to be charged monthly. If you cancel, the
              number will be released immediately and you will not be refunded for
              the current period.
            </AlertDescription>
          </Alert>

          <label className="flex items-start gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={acknowledged}
              onChange={(e) => setAcknowledged(e.target.checked)}
              className="mt-1"
            />
            <span className="text-sm text-muted-foreground">
              I understand that I will be charged {selectedNumber.monthly_cost_credits}{" "}
              credits per month and that if I cancel, the number will be released
              immediately with no refund.
            </span>
          </label>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={purchasing}>
            Cancel
          </Button>
          <Button
            onClick={handlePurchase}
            disabled={!canAfford || !acknowledged || purchasing}
          >
            {purchasing ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Purchasing...
              </>
            ) : (
              <>
                <CheckCircle className="w-4 h-4 mr-2" />
                Purchase Number
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
