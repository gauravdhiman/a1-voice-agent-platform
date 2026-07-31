"use client";

import * as React from "react";
import { Badge } from "@/components/ui/badge";
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
import { cn } from "@/lib/utils";
import { KeyRound, Pencil, Trash2 } from "lucide-react";

/**
 * Props for the LiveKit credential block (API key + secret pair).
 */
export interface LiveKitCredentialRowProps {
  configured: boolean;
  apiKey: string;
  apiSecret: string;
  onApiKeyChange: (value: string) => void;
  onApiSecretChange: (value: string) => void;
  onRemove: () => void | Promise<void>;
  removing?: boolean;
  disabled?: boolean;
  editing: boolean;
  onStartEdit: () => void;
  onCancelEdit: () => void;
  pendingChange?: boolean;
  className?: string;
}

/**
 * LiveKit credentials as a paired key + secret row with the same add/update/remove
 * affordances as single-key providers.
 */
export function LiveKitCredentialRow({
  configured,
  apiKey,
  apiSecret,
  onApiKeyChange,
  onApiSecretChange,
  onRemove,
  removing = false,
  disabled = false,
  editing,
  onStartEdit,
  onCancelEdit,
  pendingChange = false,
  className,
}: LiveKitCredentialRowProps) {
  const [removeDialogOpen, setRemoveDialogOpen] = React.useState(false);

  const handleConfirmRemove = async () => {
    await onRemove();
    setRemoveDialogOpen(false);
  };

  return (
    <>
      <div
        className={cn(
          "rounded-lg border bg-card p-4 space-y-3",
          pendingChange && "border-amber-500/50 bg-amber-500/5",
          className,
        )}
      >
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <KeyRound className="h-4 w-4 text-muted-foreground" />
              <Label className="text-sm font-medium">LiveKit</Label>
              <Badge
                variant={configured ? "default" : "secondary"}
                className={
                  configured
                    ? "bg-green-600 hover:bg-green-600/90"
                    : undefined
                }
              >
                {configured ? "Configured" : "Not configured"}
              </Badge>
              {pendingChange ? (
                <Badge variant="outline" className="border-amber-500 text-amber-700">
                  Unsaved
                </Badge>
              ) : null}
            </div>
            <p className="text-xs text-muted-foreground">
              {configured
                ? "LiveKit API key and secret are stored securely. Update both to replace them or remove to delete."
                : "Add your LiveKit API key and secret for realtime voice rooms."}
            </p>
          </div>

          {!editing ? (
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                size="sm"
                variant="outline"
                disabled={disabled || removing}
                onClick={onStartEdit}
              >
                <Pencil className="mr-1.5 h-3.5 w-3.5" />
                {configured ? "Update credentials" : "Add credentials"}
              </Button>
              {configured ? (
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  className="text-destructive hover:text-destructive"
                  disabled={disabled || removing}
                  onClick={() => setRemoveDialogOpen(true)}
                >
                  <Trash2 className="mr-1.5 h-3.5 w-3.5" />
                  {removing ? "Removing..." : "Remove credentials"}
                </Button>
              ) : null}
            </div>
          ) : (
            <Button
              type="button"
              size="sm"
              variant="ghost"
              disabled={disabled}
              onClick={onCancelEdit}
            >
              Cancel
            </Button>
          )}
        </div>

        {editing ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="livekit-api-key" className="text-xs">
                API key
              </Label>
              <Input
                id="livekit-api-key"
                type="password"
                autoComplete="off"
                value={apiKey}
                disabled={disabled}
                placeholder="LiveKit API key"
                onChange={(event) => onApiKeyChange(event.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="livekit-api-secret" className="text-xs">
                API secret
              </Label>
              <Input
                id="livekit-api-secret"
                type="password"
                autoComplete="off"
                value={apiSecret}
                disabled={disabled}
                placeholder="LiveKit API secret"
                onChange={(event) => onApiSecretChange(event.target.value)}
              />
            </div>
            <p className="text-xs text-muted-foreground sm:col-span-2">
              Click <span className="font-medium">Save credentials</span> below
              when you are ready to apply this change.
            </p>
          </div>
        ) : configured ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div
              className="flex h-10 items-center rounded-md border bg-muted/40 px-3 font-mono text-sm tracking-widest text-muted-foreground"
              aria-label="LiveKit API key stored"
            >
              ••••••••••••
            </div>
            <div
              className="flex h-10 items-center rounded-md border bg-muted/40 px-3 font-mono text-sm tracking-widest text-muted-foreground"
              aria-label="LiveKit API secret stored"
            >
              ••••••••••••
            </div>
          </div>
        ) : null}
      </div>

      <Dialog open={removeDialogOpen} onOpenChange={setRemoveDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Remove LiveKit credentials?</DialogTitle>
            <DialogDescription>
              This deletes the stored LiveKit API key and secret. Realtime voice
              sessions may fail until you add new credentials.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              type="button"
              variant="outline"
              disabled={removing}
              onClick={() => setRemoveDialogOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="destructive"
              disabled={removing}
              onClick={() => void handleConfirmRemove()}
            >
              {removing ? "Removing..." : "Remove credentials"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
