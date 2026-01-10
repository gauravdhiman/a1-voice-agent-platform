'use client';

import React, { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Loader2, AlertTriangle } from 'lucide-react';

interface CancelSubscriptionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCancel: () => void;
}

export function CancelSubscriptionDialog({
  open,
  onOpenChange,
  onCancel,
}: CancelSubscriptionDialogProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmationText, setConfirmationText] = useState('');

  const expectedConfirmation = 'Cancel subscription';
  const isConfirmationValid = confirmationText === expectedConfirmation;

  const handleConfirm = async () => {
    if (!isConfirmationValid) return;

    try {
      setLoading(true);
      setError(null);
      await onCancel();
    } catch (err: unknown) {
      const error = err as Error;
      console.error('Error cancelling subscription:', err);
      setError(error.message || 'Failed to cancel subscription');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenChange = (newOpen: boolean) => {
    if (!loading) {
      onOpenChange(newOpen);
      if (!newOpen) {
        setConfirmationText('');
        setError(null);
      }
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-red-600">
            <AlertTriangle className="h-5 w-5" />
            Cancel Subscription
          </DialogTitle>
          <DialogDescription>
            This action will cancel your subscription at the end of your current billing period.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {error && (
            <div className="p-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded-md">
              {error}
            </div>
          )}

          <div className="p-4 bg-red-50 border border-red-200 rounded-md">
            <div className="flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-red-600 mt-0.5 flex-shrink-0" />
              <div className="text-sm text-red-800">
                <p className="font-medium mb-1">Important: Cancellation Details</p>
                <ul className="space-y-1 text-red-700">
                  <li>• Subscription will remain active until end of current billing period</li>
                  <li>• You will not be charged for next billing period</li>
                  <li>• All access to premium features will be removed</li>
                  <li>• You can reactivate subscription anytime before cancellation date</li>
                </ul>
              </div>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="confirmation">
              Type <strong>&quot;{expectedConfirmation}&quot;</strong> to confirm cancellation:
            </Label>
            <Input
              id="confirmation"
              value={confirmationText}
              onChange={(e) => setConfirmationText(e.target.value)}
              placeholder='Cancel subscription'
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
              Keep Subscription
            </Button>
            <Button
              onClick={handleConfirm}
              disabled={loading || !isConfirmationValid}
              variant="destructive"
              className="flex-1"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Cancelling...
                </>
              ) : (
                'Cancel Subscription'
              )}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
