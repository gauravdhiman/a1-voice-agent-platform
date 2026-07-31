"use client";

import * as React from "react";
import { Loader2, Lock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  publicOrgPageService,
  storeAccessToken,
} from "@/services/public-org-page-service";

/**
 * Passphrase gate shown before listing agents on a protected public org page.
 */
export interface PublicOrgPassphraseGateProps {
  slug: string;
  orgName: string;
  onUnlocked: (accessToken: string) => void;
}

export function PublicOrgPassphraseGate({
  slug,
  orgName,
  onUnlocked,
}: PublicOrgPassphraseGateProps) {
  const [passphrase, setPassphrase] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const { access_token } = await publicOrgPageService.verifyPassphrase(
        slug,
        passphrase,
      );
      storeAccessToken(slug, access_token);
      onUnlocked(access_token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not verify passphrase");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-md rounded-2xl border bg-card p-6 shadow-sm">
      <div className="mb-4 flex items-center gap-2 text-muted-foreground">
        <Lock className="h-5 w-5" />
        <span className="text-sm font-medium">Protected page</span>
      </div>
      <h2 className="text-xl font-semibold">{orgName}</h2>
      <p className="mt-2 text-sm text-muted-foreground">
        Enter the passphrase provided by the organization to view available voice
        agents.
      </p>
      <form onSubmit={(e) => void handleSubmit(e)} className="mt-6 space-y-4">
        <div className="space-y-2">
          <Label htmlFor="public-passphrase">Passphrase</Label>
          <Input
            id="public-passphrase"
            type="password"
            autoComplete="off"
            value={passphrase}
            onChange={(e) => setPassphrase(e.target.value)}
            placeholder="Enter passphrase"
          />
        </div>
        {error ? <p className="text-sm text-destructive">{error}</p> : null}
        <Button type="submit" className="w-full" disabled={loading || !passphrase}>
          {loading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Checking...
            </>
          ) : (
            "Continue"
          )}
        </Button>
      </form>
    </div>
  );
}
