"use client";

import * as React from "react";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { legalDocService } from "@/services/legal-doc-service";
import type {
  LegalDocumentVersionDetail,
  LegalPublishResult,
} from "@/types/legal-docs";

interface LegalPublishDialogProps {
  version: LegalDocumentVersionDetail;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onPublished: (result: LegalPublishResult) => void;
}

/**
 * Dialog for publishing a draft legal document version. Publishing makes the
 * version the current text and deprecates the previously published version.
 * The "notify users" checkbox is checked by default.
 */
export function LegalPublishDialog({
  version,
  open,
  onOpenChange,
  onPublished,
}: LegalPublishDialogProps) {
  const [notifyUsers, setNotifyUsers] = React.useState(true);
  const [publishing, setPublishing] = React.useState(false);

  React.useEffect(() => {
    if (open) {
      setNotifyUsers(true);
    }
  }, [open, version.id]);

  const handlePublish = async () => {
    try {
      setPublishing(true);
      const result = await legalDocService.publishVersion(version.id, {
        notify_users: notifyUsers,
      });
      toast.success(`Published version ${result.version.version_number}`, {
        description:
          result.notified_count > 0
            ? `Notified ${result.notified_count} users by email.`
            : "No users were notified.",
      });
      onOpenChange(false);
      onPublished(result);
    } catch (error) {
      console.error("Legal publish failed:", error);
      const message =
        error instanceof Error ? error.message : "Failed to publish version";
      toast.error("Failed to publish version", { description: message });
    } finally {
      setPublishing(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Publish legal version</DialogTitle>
          <DialogDescription>
            Publish v{version.version_number} of this document. The previously
            published version becomes deprecated, and the new text becomes the
            version visitors see immediately.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {version.summary_of_changes ? (
            <div className="rounded-md border p-3 text-sm">
              <p className="font-medium">Summary of changes</p>
              <p className="text-muted-foreground">
                {version.summary_of_changes}
              </p>
            </div>
          ) : null}

          <label className="flex items-center gap-2 text-sm">
            <input
              id="notify-users-checkbox"
              type="checkbox"
              checked={notifyUsers}
              onChange={(e) => setNotifyUsers(e.target.checked)}
              disabled={publishing}
            />
            Notify all signed-up users by email
          </label>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={publishing}
          >
            Cancel
          </Button>
          <Button onClick={handlePublish} disabled={publishing}>
            {publishing ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Publishing…
              </>
            ) : (
              "Publish"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
