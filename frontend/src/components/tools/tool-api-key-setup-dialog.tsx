"use client";

import * as React from "react";
import { AlertCircle, KeyRound, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

/** Props for the pre-connection organization API-key dialog. */
export interface ToolApiKeySetupDialogProps {
  /** Whether the dialog is visible. */
  open: boolean;
  /** Called when the dialog should be opened or closed. */
  onOpenChange: (open: boolean) => void;
  /** Human-readable MCP tool name shown in the dialog copy. */
  toolName: string;
  /** Saves the organization key and completes the agent attachment. */
  onConnect: (apiKey: string) => Promise<void>;
  /** Disables the form while the agent-tool attachment is in progress. */
  isConnecting?: boolean;
}

/**
 * Collects an organization API key before attaching an MCP tool that has no
 * platform fallback. The dialog keeps the tool unattached until the key is
 * accepted, so a missing credential cannot become a runtime-only failure.
 */
export function ToolApiKeySetupDialog({
  open,
  onOpenChange,
  toolName,
  onConnect,
  isConnecting = false,
}: ToolApiKeySetupDialogProps) {
  const [apiKey, setApiKey] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const trimmedApiKey = apiKey.trim();

  React.useEffect(() => {
    if (open) {
      setApiKey("");
      setError(null);
    }
  }, [open]);

  const handleConnect = async () => {
    if (!trimmedApiKey || isConnecting) return;

    setError(null);
    try {
      await onConnect(trimmedApiKey);
      onOpenChange(false);
    } catch {
      setError("We could not save this key. Check it and try again.");
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>API key required to connect</DialogTitle>
          <DialogDescription>
            {toolName.replace(/_/g, " ")} does not have a platform key fallback.
            Add your organization key before this MCP can be attached to the
            agent.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="flex gap-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-amber-950 dark:border-amber-800 dark:bg-amber-950/20 dark:text-amber-100">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <p className="text-xs leading-5">
              The organization key is used for this agent&apos;s MCP calls. It
              does not overwrite or remove the platform configuration.
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="organization-api-key">Organization API key</Label>
            <div className="relative">
              <KeyRound className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                id="organization-api-key"
                type="password"
                value={apiKey}
                onChange={(event) => setApiKey(event.target.value)}
                placeholder="Paste your organization API key"
                className="pl-9"
                autoFocus
                disabled={isConnecting}
              />
            </div>
            <p className="text-xs text-muted-foreground">
              Stored securely for this agent and preferred over any platform
              fallback when the tool is called.
            </p>
          </div>

          {error && <p className="text-sm text-destructive">{error}</p>}
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isConnecting}
          >
            Cancel
          </Button>
          <Button onClick={handleConnect} disabled={!trimmedApiKey || isConnecting}>
            {isConnecting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {isConnecting ? "Connecting..." : "Connect MCP tool"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
