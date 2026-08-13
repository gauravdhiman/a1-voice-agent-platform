"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { Loader2, UserPlus, Phone } from "lucide-react";
import { toast } from "sonner";
import { phoneNumberService } from "@/services/phone-number-service";
import { agentService } from "@/services/agent-service";
import { VoiceAgent } from "@/types/agent";
import { PhoneNumberWithAgent, formatPhoneNumber } from "@/types/phone-number";

interface PhoneNumberAssignDialogProps {
  organizationId: string;
  phoneNumber: PhoneNumberWithAgent;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onAssignSuccess: () => void;
}

export function PhoneNumberAssignDialog({
  organizationId,
  phoneNumber,
  open,
  onOpenChange,
  onAssignSuccess,
}: PhoneNumberAssignDialogProps) {
  const [agents, setAgents] = useState<VoiceAgent[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [fetchingAgents, setFetchingAgents] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open && agents.length > 0 && phoneNumber.assigned_agent_id) {
      setSelectedAgentId(phoneNumber.assigned_agent_id);
    }
  }, [open, agents, phoneNumber.assigned_agent_id]);

  const fetchAgents = useCallback(async () => {
    try {
      setFetchingAgents(true);
      const orgAgents = await agentService.getOrgAgents(organizationId);
      // Phone assignment is now owned by phone_numbers. A legacy
      // voice_agents.phone_number value must not hide otherwise valid agents.
      setAgents(orgAgents);
    } catch (err) {
      console.error("Error fetching agents:", err);
      toast.error("Failed to load agents");
    } finally {
      setFetchingAgents(false);
    }
  }, [organizationId]);

  useEffect(() => {
    if (open && organizationId) {
      void fetchAgents();
    }
  }, [fetchAgents, open, organizationId]);

  const handleAssign = async () => {
    if (!selectedAgentId) {
      setError("Please select an agent");
      return;
    }

    try {
      setLoading(true);
      setError(null);
      await phoneNumberService.assignToAgent(
        phoneNumber.id,
        { agent_id: selectedAgentId },
        organizationId,
      );
      onAssignSuccess();
    } catch (err: unknown) {
      const error = err as Error;
      console.error("Error assigning phone number:", err);
      setError(error.message || "Failed to assign phone number");
    } finally {
      setLoading(false);
    }
  };

  const handleOpenChange = (newOpen: boolean) => {
    if (!loading) {
      onOpenChange(newOpen);
      if (!newOpen) {
        setSelectedAgentId("");
        setError(null);
      }
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-[450px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <UserPlus className="h-5 w-5" />
            Assign Phone Number
          </DialogTitle>
          <DialogDescription>
            Select an agent to assign {formatPhoneNumber(phoneNumber.phone_number)} to.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="flex items-center gap-3 p-3 bg-muted rounded-lg">
            <Phone className="h-5 w-5 text-muted-foreground" />
            <div>
              <div className="font-medium">
                {formatPhoneNumber(phoneNumber.phone_number)}
              </div>
              <div className="text-sm text-muted-foreground">
                {phoneNumber.monthly_cost_credits} credits/month
              </div>
            </div>
          </div>

          {error && (
            <div className="p-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded-md">
              {error}
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="agent-select">Select Agent</Label>
            {fetchingAgents ? (
              <div className="flex items-center justify-center py-4">
                <Loader2 className="h-5 w-5 animate-spin" />
                <span className="ml-2">Loading agents...</span>
              </div>
            ) : agents.length === 0 ? (
              <div className="text-center py-4 text-muted-foreground">
                <p>No available agents</p>
                <p className="text-sm">
                  Create an agent first to assign this phone number
                </p>
              </div>
            ) : (
              <Select
                value={selectedAgentId}
                onValueChange={setSelectedAgentId}
                disabled={loading}
              >
                <SelectTrigger id="agent-select">
                  <SelectValue placeholder="Select an agent" />
                </SelectTrigger>
                <SelectContent>
                  {agents.map((agent) => (
                    <SelectItem key={agent.id} value={agent.id}>
                      <div className="flex flex-col">
                        <span>{agent.name}</span>
                        {agent.description && (
                          <span className="text-xs text-muted-foreground">
                            {agent.description}
                          </span>
                        )}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>

          <div className="flex gap-3 pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={() => handleOpenChange(false)}
              disabled={loading}
              className="flex-1"
            >
              Cancel
            </Button>
            <Button
              onClick={handleAssign}
              disabled={loading || !selectedAgentId || agents.length === 0}
              className="flex-1"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Assigning...
                </>
              ) : (
                <>
                  <UserPlus className="h-4 w-4 mr-2" />
                  Assign
                </>
              )}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
