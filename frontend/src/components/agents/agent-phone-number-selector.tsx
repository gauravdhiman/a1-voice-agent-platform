"use client";

import * as React from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { cn } from "@/lib/utils";
import { phoneNumberService } from "@/services/phone-number-service";
import { PhoneNumberWebhookDetailsDrawer } from "@/components/phone-numbers/phone-number-webhook-details-drawer";
import type {
  PhoneNumberImportResponse,
  PhoneNumberWithAgent,
} from "@/types/phone-number";
import { formatPhoneNumber } from "@/types/phone-number";
import { Check, Clipboard, ExternalLink, Link2, Loader2, Phone } from "lucide-react";
import { toast } from "sonner";

interface PhoneNumberConnectionDrawerProps {
  /** Organization that owns the customer-managed number. */
  organizationId: string;
  /** Agent that receives calls after the webhook is verified. */
  agentId: string;
  /** Whether the drawer is visible. */
  open: boolean;
  /** Controls drawer visibility. */
  onOpenChange: (open: boolean) => void;
  /** Refreshes the selector after a number is connected. */
  onConnected: (phoneNumber: PhoneNumberWithAgent) => void;
}

/**
 * Right-side instructions drawer for connecting a customer-owned Twilio number.
 *
 * The drawer creates the platform record and then shows the exact, tokenized
 * webhook URLs returned by the API. Tokens are intentionally only displayed in
 * this setup flow because the backend does not store their raw values.
 */
function PhoneNumberConnectionDrawer({
  organizationId,
  agentId,
  open,
  onOpenChange,
  onConnected,
}: PhoneNumberConnectionDrawerProps) {
  const [phoneNumber, setPhoneNumber] = React.useState("");
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [result, setResult] = React.useState<PhoneNumberImportResponse | null>(null);
  const [copied, setCopied] = React.useState<"voice" | "status" | null>(null);

  const reset = React.useCallback(() => {
    setPhoneNumber("");
    setLoading(false);
    setError(null);
    setResult(null);
    setCopied(null);
  }, []);

  const handleOpenChange = React.useCallback(
    (nextOpen: boolean) => {
      if (loading) return;
      onOpenChange(nextOpen);
      if (!nextOpen) reset();
    },
    [loading, onOpenChange, reset],
  );

  const handleConnect = React.useCallback(async () => {
    if (!phoneNumber.trim()) {
      setError("Enter the Twilio phone number you already own.");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const imported = await phoneNumberService.importNumber(organizationId, {
        phone_number: phoneNumber.trim(),
        country_code: "US",
        agent_id: agentId,
      });
      setResult(imported);
      onConnected({
        ...imported.phone_number,
        agent_name: null,
      });
    } catch (connectError: unknown) {
      setError(
        connectError instanceof Error
          ? connectError.message
          : "Failed to connect the number",
      );
    } finally {
      setLoading(false);
    }
  }, [agentId, organizationId, onConnected, phoneNumber]);

  const copyUrl = React.useCallback(
    async (kind: "voice" | "status", value: string) => {
      try {
        await navigator.clipboard.writeText(value);
        setCopied(kind);
        window.setTimeout(() => setCopied(null), 1500);
      } catch {
        toast.error("Could not copy the webhook URL");
      }
    },
    [],
  );

  return (
    <Sheet open={open} onOpenChange={handleOpenChange}>
      <SheetContent
        side="right"
        className="flex w-full flex-col overflow-y-auto p-6 sm:max-w-lg"
        data-testid="webhook-help-drawer"
      >
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            <Link2 className="h-5 w-5" />
            Connect a custom number
          </SheetTitle>
          <SheetDescription>
            Connect a Twilio number you already own. We do not purchase, bill,
            or release customer-managed numbers.
          </SheetDescription>
        </SheetHeader>

        {result ? (
          <div className="flex-1 space-y-5">
            <Alert>
              <Phone className="h-4 w-4" />
              <AlertTitle>Save these webhook settings in Twilio</AlertTitle>
              <AlertDescription>{result.message}</AlertDescription>
            </Alert>

            <WebhookUrlRow
              label="Incoming voice URL"
              value={result.voice_url}
              copied={copied === "voice"}
              onCopy={() => copyUrl("voice", result.voice_url)}
            />
            <WebhookUrlRow
              label="Call status callback URL"
              value={result.status_callback}
              copied={copied === "status"}
              onCopy={() => copyUrl("status", result.status_callback)}
            />

            <ol className="list-decimal space-y-2 pl-5 text-sm text-muted-foreground">
              <li>Open the phone number in the Twilio Console.</li>
              <li>Paste the first URL into the incoming voice webhook.</li>
              <li>Paste the second URL into the call status callback.</li>
              <li>Save the Twilio settings and place a test call.</li>
            </ol>
            <a
              className="inline-flex items-center gap-1 text-sm text-primary underline underline-offset-4"
              href="https://www.twilio.com/docs/usage/webhooks"
              target="_blank"
              rel="noreferrer"
            >
              Twilio webhook instructions <ExternalLink className="h-3 w-3" />
            </a>
          </div>
        ) : (
          <div className="flex-1 space-y-5">
            <div className="space-y-2">
              <Label htmlFor="agent-custom-twilio-number">
                Twilio phone number
              </Label>
              <Input
                id="agent-custom-twilio-number"
                value={phoneNumber}
                onChange={(event) => setPhoneNumber(event.target.value)}
                placeholder="+1 (415) 555-0100"
                disabled={loading}
              />
              <p className="text-xs text-muted-foreground">
                Enter the number exactly as it appears in your Twilio account.
                We will show the two URLs to paste after it is connected.
              </p>
            </div>
            {error && (
              <Alert variant="destructive">
                <AlertTitle>Could not connect number</AlertTitle>
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
          </div>
        )}

        <SheetFooter>
          {result ? (
            <Button className="w-full" onClick={() => handleOpenChange(false)}>
              Done
            </Button>
          ) : (
            <Button
              className="w-full"
              onClick={handleConnect}
              disabled={loading}
            >
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Connect number
            </Button>
          )}
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}

interface WebhookUrlRowProps {
  /** Human-readable webhook purpose. */
  label: string;
  /** Tokenized URL returned by the backend. */
  value: string;
  /** Whether the most recent copy action succeeded. */
  copied: boolean;
  /** Copies the URL to the clipboard. */
  onCopy: () => void;
}

/** Displays a copyable webhook URL without truncating the token. */
function WebhookUrlRow({ label, value, copied, onCopy }: WebhookUrlRowProps) {
  return (
    <div className="space-y-2 rounded-md border bg-muted/40 p-3">
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-medium">{label}</span>
        <Button type="button" variant="ghost" size="sm" onClick={onCopy}>
          {copied ? <Check className="mr-1 h-4 w-4" /> : <Clipboard className="mr-1 h-4 w-4" />}
          {copied ? "Copied" : "Copy"}
        </Button>
      </div>
      <code className="block break-all text-xs">{value}</code>
    </div>
  );
}

interface AgentPhoneNumberSelectorProps {
  /** Agent whose inbound number mapping is being edited. */
  agentId: string;
  /** Organization that owns the available numbers. */
  organizationId: string;
  /** Whether the current user may change the mapping. */
  canEdit: boolean;
  /** Notifies the parent when the table-backed assignment changes. */
  onAssignmentChange?: (phoneNumber: PhoneNumberWithAgent | null) => void;
  /** Optional class name for the field wrapper. */
  className?: string;
}

/**
 * Selects an organization-owned number for an agent or opens custom-number
 * setup.  The selector uses ``phone_numbers`` as the source of truth and never
 * writes the normalized ``phone_numbers`` assignment used for routing.
 */
export function AgentPhoneNumberSelector({
  agentId,
  organizationId,
  canEdit,
  onAssignmentChange,
  className,
}: AgentPhoneNumberSelectorProps) {
  const [numbers, setNumbers] = React.useState<PhoneNumberWithAgent[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [numbersLoaded, setNumbersLoaded] = React.useState(false);
  const [updating, setUpdating] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [drawerOpen, setDrawerOpen] = React.useState(false);
  const [detailsOpen, setDetailsOpen] = React.useState(false);

  const loadNumbers = React.useCallback(async () => {
    setError(null);
    try {
      const response = await phoneNumberService.getOrganizationNumbers(
        organizationId,
      );
      setNumbers(response.items);
      setNumbersLoaded(true);
    } catch (loadError: unknown) {
      setError(
        loadError instanceof Error
          ? loadError.message
          : "Failed to load phone numbers",
      );
    }
  }, [organizationId]);

  const loadAssignedNumber = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const assignedNumber = await phoneNumberService.getAgentNumber(
        organizationId,
        agentId,
      );
      setNumbers(assignedNumber ? [assignedNumber] : []);
      setNumbersLoaded(false);
    } catch (loadError: unknown) {
      setError(
        loadError instanceof Error
          ? loadError.message
          : "Failed to load phone number",
      );
    } finally {
      setLoading(false);
    }
  }, [agentId, organizationId]);

  React.useEffect(() => {
    void loadAssignedNumber();
  }, [loadAssignedNumber]);

  const assignedNumber = React.useMemo(
    () => numbers.find((number) => number.assigned_agent_id === agentId) ?? null,
    [agentId, numbers],
  );

  React.useEffect(() => {
    onAssignmentChange?.(assignedNumber);
  }, [assignedNumber, onAssignmentChange]);

  const handleSelection = React.useCallback(
    async (value: string) => {
      if (value === "custom") {
        setDrawerOpen(true);
        return;
      }
      if (value === assignedNumber?.id) return;

      setUpdating(true);
      try {
        if (value === "none") {
          if (assignedNumber) {
            await phoneNumberService.unassignFromAgent(
              assignedNumber.id,
              organizationId,
            );
          }
        } else {
          await phoneNumberService.assignToAgent(
            value,
            { agent_id: agentId },
            organizationId,
          );
        }
        await loadNumbers();
        toast.success(
          value === "none"
            ? "Phone number unassigned from this agent"
            : "Phone number assigned to this agent",
        );
      } catch (assignError: unknown) {
        toast.error(
          assignError instanceof Error
            ? assignError.message
            : "Failed to assign phone number",
        );
      } finally {
        setUpdating(false);
      }
    },
    [agentId, assignedNumber, loadNumbers, organizationId],
  );

  const handleConnected = React.useCallback(
    (phoneNumber: PhoneNumberWithAgent) => {
      setNumbers((current) => [
        ...current.filter((number) => number.id !== phoneNumber.id),
        phoneNumber,
      ]);
      setNumbersLoaded(false);
      onAssignmentChange?.(phoneNumber);
    },
    [onAssignmentChange],
  );

  return (
    <div className={cn("space-y-2", className)}>
      <Label htmlFor="agent-phone-number">Phone number</Label>
      <Select
        value={assignedNumber?.id ?? "none"}
        onValueChange={(value) => void handleSelection(value)}
        onOpenChange={(open) => {
          if (open && !numbersLoaded) {
            void loadNumbers();
          }
        }}
        disabled={!canEdit || loading || updating}
      >
        <SelectTrigger id="agent-phone-number" aria-label="Phone number">
          <SelectValue
            placeholder={loading ? "Loading numbers…" : "Select a number"}
          />
        </SelectTrigger>
        <SelectContent>
          {!numbersLoaded && numbers.length === 0 && (
            <SelectItem value="loading" disabled>
              Loading available numbers…
            </SelectItem>
          )}
          <SelectItem value="none">No phone number</SelectItem>
          {numbers.map((number) => {
            const assignedToAnotherAgent =
              Boolean(number.assigned_agent_id) &&
              number.assigned_agent_id !== agentId;
            return (
              <SelectItem
                key={number.id}
                value={number.id}
                disabled={assignedToAnotherAgent}
              >
                {formatPhoneNumber(number.phone_number)}
                {assignedToAnotherAgent
                  ? ` — assigned to ${number.agent_name ?? "another agent"}`
                  : number.status === "verification_required"
                    ? " — verification required"
                    : ""}
              </SelectItem>
            );
          })}
          <SelectItem value="custom">Connect a custom number…</SelectItem>
        </SelectContent>
      </Select>
      {assignedNumber?.status === "verification_required" ? (
        <div className="space-y-1">
          <p className="text-xs text-amber-600">
            Finish the Twilio webhook setup to activate incoming calls.
          </p>
          {assignedNumber.management_mode === "customer_managed" && (
            <Button
              type="button"
              variant="link"
              size="sm"
              className="h-auto p-0 text-xs"
              onClick={() => setDetailsOpen(true)}
            >
              View setup details
            </Button>
          )}
        </div>
      ) : (
        <p className="text-xs text-muted-foreground">
          Choose a number already owned by your organization or connect one from
          Twilio.
        </p>
      )}
      {error && <p className="text-xs text-destructive">{error}</p>}

      <PhoneNumberConnectionDrawer
        agentId={agentId}
        organizationId={organizationId}
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
        onConnected={handleConnected}
      />
      {assignedNumber?.management_mode === "customer_managed" &&
        assignedNumber.status === "verification_required" && (
          <PhoneNumberWebhookDetailsDrawer
            organizationId={organizationId}
            phoneNumberId={assignedNumber.id}
            phoneNumber={assignedNumber.phone_number}
            open={detailsOpen}
            onOpenChange={setDetailsOpen}
          />
        )}
    </div>
  );
}
