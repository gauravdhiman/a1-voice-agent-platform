"use client";

import React, { useState } from "react";
import {
  Card,
  CardContent,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { Loader2, Phone, UserX, UserPlus, Trash2, Plus, Link2 } from "lucide-react";
import { toast } from "sonner";
import {
  AvailablePhoneNumber,
  PhoneNumberWithAgent,
  formatPhoneNumber,
  getPhoneNumberTypeLabel,
  PhoneNumberStatus,
} from "@/types/phone-number";
import { PhoneNumberAssignDialog } from "./phone-number-assign-dialog";
import { PhoneNumberCancelDialog } from "./phone-number-cancel-dialog";
import { PhoneNumberPurchase } from "./phone-number-purchase";
import { PhoneNumberSearch } from "./phone-number-search";
import { PhoneNumberImportDialog } from "./phone-number-import-dialog";
import { PhoneNumberWebhookDetailsDrawer } from "./phone-number-webhook-details-drawer";

interface PhoneNumberDashboardProps {
  organizationId: string;
  phoneNumbers: PhoneNumberWithAgent[];
  creditBalance?: number;
  isLoading?: boolean;
  onRefresh?: () => void;
  /**
   * Whether the current user can manage (add, assign, cancel) phone
   * numbers. Defaults to `true` for back-compat with pre-N1 call
   * sites. The /phone-numbers page is the strict permission gate.
   */
  canManage?: boolean;
}

export function PhoneNumberDashboard({
  organizationId,
  phoneNumbers,
  creditBalance = 0,
  isLoading,
  onRefresh,
  canManage = true,
}: PhoneNumberDashboardProps) {
  const [assignDialogOpen, setAssignDialogOpen] = useState(false);
  const [cancelDialogOpen, setCancelDialogOpen] = useState(false);
  const [searchDialogOpen, setSearchDialogOpen] = useState(false);
  const [purchaseDialogOpen, setPurchaseDialogOpen] = useState(false);
  const [importDialogOpen, setImportDialogOpen] = useState(false);
  const [detailsDialogOpen, setDetailsDialogOpen] = useState(false);
  const [selectedNumber, setSelectedNumber] = useState<PhoneNumberWithAgent | null>(
    null,
  );
  const [selectedDetailsNumber, setSelectedDetailsNumber] =
    useState<PhoneNumberWithAgent | null>(null);
  const [selectedAvailableNumber, setSelectedAvailableNumber] = useState<AvailablePhoneNumber | null>(null);

  const unusedCount = phoneNumbers.filter((n) => !n.assigned_agent_id).length;

  const handleAssign = (number: PhoneNumberWithAgent) => {
    setSelectedNumber(number);
    setAssignDialogOpen(true);
  };

  const handleCancel = (number: PhoneNumberWithAgent) => {
    setSelectedNumber(number);
    setCancelDialogOpen(true);
  };

  const handleDetails = (number: PhoneNumberWithAgent) => {
    setSelectedDetailsNumber(number);
    setDetailsDialogOpen(true);
  };

  const handleAssignSuccess = () => {
    toast.success("Phone number assigned successfully");
    setAssignDialogOpen(false);
    setSelectedNumber(null);
    onRefresh?.();
  };

  const handleCancelSuccess = (message?: string) => {
    toast.success(message || "Phone number released or disconnected successfully");
    setCancelDialogOpen(false);
    setSelectedNumber(null);
    onRefresh?.();
  };

  const handleNumberSelectedFromSearch = (number: AvailablePhoneNumber) => {
    setSelectedAvailableNumber(number);
    setSearchDialogOpen(false);
    setPurchaseDialogOpen(true);
  };

  const handlePurchaseSuccess = () => {
    setPurchaseDialogOpen(false);
    setSelectedAvailableNumber(null);
    onRefresh?.();
  };

  const handleImportSuccess = () => {
    toast.success("Existing number connected");
    onRefresh?.();
  };

  const getStatusBadge = (status: PhoneNumberStatus, hasAgent: boolean) => {
    if (status === "cancelled") {
      return <Badge variant="destructive">Cancelled</Badge>;
    }
    if (status === "verification_required") {
      return <Badge variant="secondary">Verification required</Badge>;
    }
    if (hasAgent) {
      return (
        <Badge className="bg-green-100 text-green-800 border-green-200">
          Active (used)
        </Badge>
      );
    }
    if (status === "release_pending") {
      return <Badge variant="secondary">Release pending</Badge>;
    }
    return <Badge variant="secondary">Unused</Badge>;
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin" />
        <span className="ml-2">Loading phone numbers...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {unusedCount > 0 && (
        <Alert>
          <UserX className="h-4 w-4" />
          <AlertDescription>
            You have {unusedCount} unused phone number
            {unusedCount > 1 ? "s" : ""}. Assign them to agents or consider
            releasing them to stop recurring charges.
          </AlertDescription>
        </Alert>
      )}

      {phoneNumbers.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Phone className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <p className="text-muted-foreground mb-4">No phone numbers yet</p>
            {canManage && (
              <div className="flex justify-center gap-2">
                <Button onClick={() => setSearchDialogOpen(true)}>
                  <Plus className="h-4 w-4 mr-2" />
                  Search & Purchase
                </Button>
                <Button variant="outline" onClick={() => setImportDialogOpen(true)}>
                  <Link2 className="h-4 w-4 mr-2" />
                  Connect Existing
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          <div className="flex justify-end">
            {canManage && (
              <div className="flex gap-2">
                <Button variant="outline" onClick={() => setSearchDialogOpen(true)}>
                  <Plus className="h-4 w-4 mr-2" />
                  Search & Purchase
                </Button>
                <Button variant="outline" onClick={() => setImportDialogOpen(true)}>
                  <Link2 className="h-4 w-4 mr-2" />
                  Connect Existing
                </Button>
              </div>
            )}
          </div>
          {phoneNumbers.map((number) => (
            <Card key={number.id}>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="flex items-center gap-3">
                      <Phone className="w-6 h-6 text-muted-foreground" />
                      <div>
                        <div className="flex items-center gap-2">
                          <div className="font-semibold text-lg">
                            {formatPhoneNumber(number.phone_number)}
                          </div>
                          {number.management_mode === "customer_managed" &&
                            number.status === "verification_required" && (
                              <Button
                                type="button"
                                variant="link"
                                size="sm"
                                className="h-auto p-0 text-xs"
                                onClick={() => handleDetails(number)}
                              >
                                View setup details
                              </Button>
                            )}
                        </div>
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                          <Badge variant="outline">
                            {getPhoneNumberTypeLabel(number.phone_number_type)}
                          </Badge>
                          {getStatusBadge(
                            number.status,
                            !!number.assigned_agent_id,
                          )}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-6">
                    <div className="text-right">
                      <div className="text-sm text-muted-foreground">Monthly</div>
                      <div className="font-semibold">
                        {number.management_mode === "customer_managed"
                          ? "No platform rental"
                          : `${number.monthly_cost_credits} credits`}
                      </div>
                    </div>

                    <div className="text-right min-w-[150px]">
                      {number.assigned_agent_id ? (
                        <>
                          <div className="text-sm text-muted-foreground">
                            Assigned to
                          </div>
                          <div className="font-medium">{number.agent_name}</div>
                        </>
                      ) : (
                        <>
                          <div className="text-sm text-muted-foreground">Status</div>
                          <div className="font-medium text-muted-foreground">
                            Not assigned
                          </div>
                        </>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      {canManage &&
                        !number.assigned_agent_id &&
                        number.status !== "cancelled" && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleAssign(number)}
                          >
                            <UserPlus className="w-4 h-4 mr-1" />
                            Assign
                          </Button>
                        )}

                      {canManage && number.status !== "cancelled" && (
                        <Button
                          size="sm"
                          variant="outline"
                          className="text-red-600 border-red-200 hover:bg-red-50"
                          onClick={() => handleCancel(number)}
                        >
                          <Trash2 className="w-4 h-4 mr-1" />
                          {number.management_mode === "customer_managed"
                            ? "Disconnect"
                            : "Release"}
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {selectedNumber && (
        <PhoneNumberAssignDialog
          organizationId={organizationId}
          phoneNumber={selectedNumber}
          open={assignDialogOpen}
          onOpenChange={setAssignDialogOpen}
          onAssignSuccess={handleAssignSuccess}
        />
      )}

      {selectedNumber && (
        <PhoneNumberCancelDialog
          organizationId={organizationId}
          phoneNumber={selectedNumber}
          open={cancelDialogOpen}
          onOpenChange={setCancelDialogOpen}
          onCancelSuccess={handleCancelSuccess}
        />
      )}

      <Sheet open={searchDialogOpen} onOpenChange={setSearchDialogOpen}>
        <SheetContent className="flex flex-col w-full sm:max-w-xl">
          <SheetHeader className="px-6 pt-6 pb-4 border-b">
            <SheetTitle>Search & Purchase Phone Number</SheetTitle>
            <SheetDescription>Find and select a phone number for your organization</SheetDescription>
          </SheetHeader>
          <div className="flex-1 overflow-y-auto px-6 py-5">
            <PhoneNumberSearch
              creditBalance={creditBalance}
              onNumberSelected={handleNumberSelectedFromSearch}
            />
          </div>
        </SheetContent>
      </Sheet>

      <PhoneNumberPurchase
        organizationId={organizationId}
        creditBalance={creditBalance}
        selectedNumber={selectedAvailableNumber}
        open={purchaseDialogOpen}
        onOpenChange={setPurchaseDialogOpen}
        onPurchaseSuccess={handlePurchaseSuccess}
      />

      <PhoneNumberImportDialog
        organizationId={organizationId}
        open={importDialogOpen}
        onOpenChange={setImportDialogOpen}
        onImportSuccess={handleImportSuccess}
      />

      {selectedDetailsNumber && (
        <PhoneNumberWebhookDetailsDrawer
          organizationId={organizationId}
          phoneNumberId={selectedDetailsNumber.id}
          phoneNumber={selectedDetailsNumber.phone_number}
          open={detailsDialogOpen}
          onOpenChange={setDetailsDialogOpen}
        />
      )}
    </div>
  );
}
