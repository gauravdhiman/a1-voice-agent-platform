"use client";

import { useEffect, useState } from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Loader2, Link2, Phone } from "lucide-react";
import { toast } from "sonner";
import { agentService } from "@/services/agent-service";
import { phoneNumberService } from "@/services/phone-number-service";
import type { VoiceAgent } from "@/types/agent";
import type { PhoneNumberImportResponse } from "@/types/phone-number";

interface PhoneNumberImportDialogProps {
  organizationId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onImportSuccess: () => void;
}

/** Connects an existing Twilio number and optionally assigns it to an agent. */
export function PhoneNumberImportDialog({
  organizationId,
  open,
  onOpenChange,
  onImportSuccess,
}: PhoneNumberImportDialogProps) {
  const [phoneNumber, setPhoneNumber] = useState("");
  const [selectedAgentId, setSelectedAgentId] = useState("");
  const [agents, setAgents] = useState<VoiceAgent[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingAgents, setLoadingAgents] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PhoneNumberImportResponse | null>(null);

  useEffect(() => {
    if (!open || !organizationId) return;
    setLoadingAgents(true);
    agentService
      .getOrgAgents(organizationId)
      .then(setAgents)
      .catch(() => toast.error("Failed to load agents"))
      .finally(() => setLoadingAgents(false));
  }, [open, organizationId]);

  const handleImport = async () => {
    if (!phoneNumber.trim()) {
      setError("Enter the existing Twilio phone number.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const imported = await phoneNumberService.importNumber(organizationId, {
        phone_number: phoneNumber.trim(),
        country_code: "US",
        ...(selectedAgentId ? { agent_id: selectedAgentId } : {}),
      });
      setResult(imported);
      onImportSuccess();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to connect number");
    } finally {
      setLoading(false);
    }
  };

  const handleOpenChange = (nextOpen: boolean) => {
    if (loading) return;
    onOpenChange(nextOpen);
    if (!nextOpen) {
      setPhoneNumber("");
      setSelectedAgentId("");
      setError(null);
      setResult(null);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-[520px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Link2 className="h-5 w-5" />
            Connect Existing Number
          </DialogTitle>
          <DialogDescription>
            Connect a Twilio number you already own. We will not buy, bill, or
            release this number.
          </DialogDescription>
        </DialogHeader>

        {result ? (
          <div className="space-y-4">
            <Alert>
              <Phone className="h-4 w-4" />
              <AlertTitle>Number saved — finish verification</AlertTitle>
              <AlertDescription>{result.message}</AlertDescription>
            </Alert>
            <div className="space-y-3 text-sm">
              <p className="font-medium">
                In Twilio, set both webhooks to these URLs:
              </p>
              <div className="rounded-md border bg-muted p-3 break-all">
                <div className="font-medium">Incoming voice</div>
                <code>{result.voice_url}</code>
              </div>
              <div className="rounded-md border bg-muted p-3 break-all">
                <div className="font-medium">Call status callback</div>
                <code>{result.status_callback}</code>
              </div>
              <p className="text-muted-foreground">
                Place a test call after saving them. The number becomes active
                automatically after the first verified webhook.
              </p>
            </div>
            <Button className="w-full" onClick={() => handleOpenChange(false)}>
              Done
            </Button>
          </div>
        ) : (
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label htmlFor="existing-twilio-number">Twilio phone number</Label>
              <Input
                id="existing-twilio-number"
                value={phoneNumber}
                onChange={(event) => setPhoneNumber(event.target.value)}
                placeholder="+1 (415) 555-0100"
                disabled={loading}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="existing-number-agent">Assign to agent (optional)</Label>
              <Select
                value={selectedAgentId}
                onValueChange={setSelectedAgentId}
                disabled={loading || loadingAgents}
              >
                <SelectTrigger id="existing-number-agent">
                  <SelectValue placeholder="Assign later" />
                </SelectTrigger>
                <SelectContent>
                  {agents.map((agent) => (
                    <SelectItem key={agent.id} value={agent.id}>
                      {agent.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {error && <p className="text-sm text-red-600">{error}</p>}
            <div className="flex gap-3 pt-2">
              <Button
                variant="outline"
                className="flex-1"
                onClick={() => handleOpenChange(false)}
                disabled={loading}
              >
                Cancel
              </Button>
              <Button className="flex-1" onClick={handleImport} disabled={loading}>
                {loading ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Link2 className="h-4 w-4 mr-2" />
                )}
                Connect Number
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
