"use client";

import * as React from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { PhoneNumberPurchase } from "@/components/phone-numbers/phone-number-purchase";
import { PhoneNumberSearch } from "@/components/phone-numbers/phone-number-search";
import { billingService } from "@/services/billing-service";
import { phoneNumberService } from "@/services/phone-number-service";
import type {
  AvailablePhoneNumber,
  PhoneNumber,
  PhoneNumberWithAgent,
} from "@/types/phone-number";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";

interface AgentPhoneNumberPurchaseDrawerProps {
  /** Agent that receives the purchased number. */
  agentId: string;
  /** Organization charged for the number rental. */
  organizationId: string;
  /** Whether the drawer is visible. */
  open: boolean;
  /** Controls drawer visibility. */
  onOpenChange: (open: boolean) => void;
  /** Refreshes the selector after the purchase and assignment complete. */
  onPurchased: (phoneNumber: PhoneNumberWithAgent) => void;
}

/**
 * Provides the existing phone-number search and purchase flow in the context
 * of an agent assignment. Billing data is loaded only after the user opens
 * the drawer so the agent detail page does not pay the purchase-flow cost on
 * every visit.
 */
export function AgentPhoneNumberPurchaseDrawer({
  agentId,
  organizationId,
  open,
  onOpenChange,
  onPurchased,
}: AgentPhoneNumberPurchaseDrawerProps) {
  const [creditBalance, setCreditBalance] = React.useState<number | null>(null);
  const [loadingBalance, setLoadingBalance] = React.useState(false);
  const [balanceError, setBalanceError] = React.useState<string | null>(null);
  const [selectedNumber, setSelectedNumber] =
    React.useState<AvailablePhoneNumber | null>(null);
  const [purchaseDialogOpen, setPurchaseDialogOpen] = React.useState(false);

  React.useEffect(() => {
    if (!open) return;

    let cancelled = false;
    setLoadingBalance(true);
    setBalanceError(null);
    void billingService
      .getCreditBalance(organizationId)
      .then((balance) => {
        if (!cancelled) setCreditBalance(balance.total_credits);
      })
      .catch((loadError: unknown) => {
        if (!cancelled) {
          setBalanceError(
            loadError instanceof Error
              ? loadError.message
              : "Unable to load your phone-number balance",
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingBalance(false);
      });

    return () => {
      cancelled = true;
    };
  }, [open, organizationId]);

  const handleOpenChange = React.useCallback(
    (nextOpen: boolean) => {
      onOpenChange(nextOpen);
      if (!nextOpen) {
        setSelectedNumber(null);
        setPurchaseDialogOpen(false);
      }
    },
    [onOpenChange],
  );

  const handlePurchaseSuccess = React.useCallback(
    async (purchasedNumber: PhoneNumber) => {
      try {
        await phoneNumberService.assignToAgent(
          purchasedNumber.id,
          { agent_id: agentId },
          organizationId,
        );
        onPurchased({ ...purchasedNumber, agent_name: null });
        toast.success("Phone number purchased and assigned to this agent");
        handleOpenChange(false);
      } catch (assignError: unknown) {
        toast.error(
          assignError instanceof Error
            ? `Number purchased, but it could not be assigned: ${assignError.message}`
            : "Number purchased, but it could not be assigned to this agent",
        );
      }
    },
    [agentId, handleOpenChange, onPurchased, organizationId],
  );

  return (
    <>
      <Sheet open={open} onOpenChange={handleOpenChange}>
        <SheetContent
          side="right"
          className="flex w-full flex-col overflow-hidden sm:max-w-xl"
          data-testid="agent-phone-number-purchase-drawer"
        >
          <SheetHeader className="border-b px-6 pb-4 pt-6">
            <SheetTitle>Buy a phone number</SheetTitle>
            <SheetDescription>
              Search for an available number. After you purchase it, we&apos;ll
              assign it to this agent automatically.
            </SheetDescription>
          </SheetHeader>
          <div className="min-h-0 flex-1 overflow-y-auto px-6 py-5">
            {loadingBalance ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                <span className="ml-2 text-sm text-muted-foreground">
                  Checking your balance…
                </span>
              </div>
            ) : balanceError ? (
              <Alert variant="destructive">
                <AlertTitle>Could not load phone-number options</AlertTitle>
                <AlertDescription>{balanceError}</AlertDescription>
              </Alert>
            ) : creditBalance !== null ? (
              <PhoneNumberSearch
                organizationId={organizationId}
                creditBalance={creditBalance}
                className="min-h-full"
                onNumberSelected={(number) => {
                  setSelectedNumber(number);
                  setPurchaseDialogOpen(true);
                }}
              />
            ) : null}
          </div>
        </SheetContent>
      </Sheet>

      <PhoneNumberPurchase
        organizationId={organizationId}
        creditBalance={creditBalance ?? 0}
        selectedNumber={selectedNumber}
        open={purchaseDialogOpen}
        onOpenChange={setPurchaseDialogOpen}
        onPurchaseSuccess={handlePurchaseSuccess}
      />
    </>
  );
}
