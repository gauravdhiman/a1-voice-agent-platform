"use client";

import * as React from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { phoneNumberService } from "@/services/phone-number-service";
import { formatPhoneNumber } from "@/types/phone-number";
import { Check, Clipboard, ExternalLink, Loader2, Phone } from "lucide-react";
import { toast } from "sonner";

interface PhoneNumberWebhookDetailsDrawerProps {
  /** Organization that owns the customer-managed number. */
  organizationId: string;
  /** Phone-number record awaiting webhook verification. */
  phoneNumberId: string;
  /** E.164 number displayed in the drawer heading. */
  phoneNumber: string;
  /** Whether the drawer is visible. */
  open: boolean;
  /** Controls drawer visibility. */
  onOpenChange: (open: boolean) => void;
}

/**
 * Loads and displays the persisted webhook URLs for a customer-owned number.
 *
 * The API only permits this while verification is pending. The token is
 * encrypted at rest and removed after the first valid verification callback.
 */
export function PhoneNumberWebhookDetailsDrawer({
  organizationId,
  phoneNumberId,
  phoneNumber,
  open,
  onOpenChange,
}: PhoneNumberWebhookDetailsDrawerProps) {
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [details, setDetails] = React.useState<
    Awaited<ReturnType<typeof phoneNumberService.getVerificationDetails>> | null
  >(null);
  const [copied, setCopied] = React.useState<"voice" | "status" | null>(null);

  React.useEffect(() => {
    if (!open) return;

    let cancelled = false;
    setLoading(true);
    setError(null);
    setDetails(null);
    setCopied(null);

    phoneNumberService
      .getVerificationDetails(organizationId, phoneNumberId)
      .then((response) => {
        if (!cancelled) setDetails(response);
      })
      .catch((loadError: unknown) => {
        if (!cancelled) {
          setError(
            loadError instanceof Error
              ? loadError.message
              : "Could not load verification details",
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [open, organizationId, phoneNumberId]);

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
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="flex w-full flex-col overflow-y-auto p-6 sm:max-w-lg"
        data-testid="phone-number-verification-details-drawer"
      >
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            <Phone className="h-5 w-5" />
            Finish setup for {formatPhoneNumber(phoneNumber)}
          </SheetTitle>
          <SheetDescription>
            Copy these two URLs into your Twilio phone-number settings to
            activate incoming calls.
          </SheetDescription>
        </SheetHeader>

        <div className="flex-1 space-y-5">
          {loading && (
            <div className="flex items-center gap-2 py-8 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading setup details…
            </div>
          )}

          {error && (
            <Alert variant="destructive">
              <AlertTitle>Setup details unavailable</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {details && (
            <>
              <Alert>
                <Phone className="h-4 w-4" />
                <AlertTitle>Save these webhook settings in Twilio</AlertTitle>
                <AlertDescription>{details.message}</AlertDescription>
              </Alert>

              <WebhookUrlRow
                label="Incoming voice URL"
                value={details.voice_url}
                copied={copied === "voice"}
                onCopy={() => copyUrl("voice", details.voice_url)}
              />
              <WebhookUrlRow
                label="Call status callback URL"
                value={details.status_callback}
                copied={copied === "status"}
                onCopy={() => copyUrl("status", details.status_callback)}
              />

              <ol className="list-decimal space-y-2 pl-5 text-sm text-muted-foreground">
                <li>Open this phone number in the Twilio Console.</li>
                <li>Paste the incoming voice URL into the voice webhook.</li>
                <li>Paste the status callback URL into call status callbacks.</li>
                <li>Save the settings and place a test call.</li>
              </ol>
              <a
                className="inline-flex items-center gap-1 text-sm text-primary underline underline-offset-4"
                href="https://www.twilio.com/docs/usage/webhooks"
                target="_blank"
                rel="noreferrer"
              >
                Twilio webhook instructions <ExternalLink className="h-3 w-3" />
              </a>
            </>
          )}
        </div>

        <SheetFooter>
          <Button className="w-full" onClick={() => onOpenChange(false)}>
            Done
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}

interface WebhookUrlRowProps {
  /** Human-readable webhook purpose. */
  label: string;
  /** Tokenized URL returned by the API. */
  value: string;
  /** Whether the most recent copy action succeeded. */
  copied: boolean;
  /** Copies the URL to the clipboard. */
  onCopy: () => void;
}

/** Displays a copyable webhook URL without truncating its token. */
function WebhookUrlRow({ label, value, copied, onCopy }: WebhookUrlRowProps) {
  return (
    <div className="space-y-2 rounded-md border bg-muted/40 p-3">
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-medium">{label}</span>
        <Button type="button" variant="ghost" size="sm" onClick={onCopy}>
          {copied ? (
            <Check className="mr-1 h-4 w-4" />
          ) : (
            <Clipboard className="mr-1 h-4 w-4" />
          )}
          {copied ? "Copied" : "Copy"}
        </Button>
      </div>
      <code className="block break-all text-xs">{value}</code>
    </div>
  );
}
