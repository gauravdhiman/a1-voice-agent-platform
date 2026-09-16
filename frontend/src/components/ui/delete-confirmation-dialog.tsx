"use client";

import React, { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2, AlertTriangle } from "lucide-react";

interface DeleteConfirmationDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  itemName: string;
  itemType: string;
  warnings: string[];
  onDelete: () => void;
  /**
   * Optional rich content rendered below the warnings box (e.g. a list of
   * affected agents with navigation links). Kept separate from `warnings`
   * (which stays plain strings rendered as a red bulleted list) so the shared
   * dialog stays text-only for non-link callers (RBAC deletes).
   */
  extraContent?: React.ReactNode;
}

export function DeleteConfirmationDialog({
  open,
  onOpenChange,
  itemName,
  itemType,
  warnings,
  onDelete,
  extraContent,
}: DeleteConfirmationDialogProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmationText, setConfirmationText] = useState("");

  const expectedConfirmation = "Delete";
  const isConfirmationValid = confirmationText === expectedConfirmation;

  const handleDelete = async () => {
    if (!isConfirmationValid) return;

    try {
      setLoading(true);
      setError(null);
      await onDelete();
    } catch (err: unknown) {
      const error = err as Error;
      console.error(`Error deleting ${itemType}:`, err);
      setError(error.message || `Failed to delete ${itemType}`);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenChange = (newOpen: boolean) => {
    if (!loading) {
      onOpenChange(newOpen);
      if (!newOpen) {
        setConfirmationText("");
        setError(null);
      }
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 status-text-danger">
            <AlertTriangle className="h-5 w-5" />
            Delete {itemType}
          </DialogTitle>
          <DialogDescription>
            This action cannot be undone. This will permanently delete{" "}
            {itemType}
            {itemName && ` "${itemName}"`} and remove all associated data.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {error && (
            <div className="status-callout danger p-3 text-sm">{error}</div>
          )}

          {warnings.length > 0 && (
            <div className="status-callout danger p-4">
              <div className="flex items-start gap-3">
                <AlertTriangle className="h-5 w-5 status-text-danger mt-0.5 flex-shrink-0" />
                <div className="text-sm">
                  <p className="font-medium mb-1">
                    Warning: This action is irreversible
                  </p>
                  <ul className="space-y-1">
                    {warnings.map((warning, index) => (
                      <li key={index}>• {warning}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )}

          {extraContent && (
            <div className="text-sm text-foreground">{extraContent}</div>
          )}

          <div className="space-y-2">
            <Label htmlFor="confirmation">
              Type <strong>&quot;{expectedConfirmation}&quot;</strong> to
              confirm deletion:
            </Label>
            <Input
              id="confirmation"
              value={confirmationText}
              onChange={(e) => setConfirmationText(e.target.value)}
              placeholder="Delete"
              disabled={loading}
              className="font-mono"
            />
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
              onClick={handleDelete}
              disabled={loading || !isConfirmationValid}
              variant="destructive"
              className="flex-1"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Deleting...
                </>
              ) : (
                `Delete ${itemType}`
              )}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
