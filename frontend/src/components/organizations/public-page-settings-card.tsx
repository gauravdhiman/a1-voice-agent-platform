"use client";

import * as React from "react";
import { Copy, ExternalLink, Globe, Loader2, Shield } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { publicOrgPagePath } from "@/lib/organization-slug";
import { organizationService } from "@/services/organization-service";
import type { OrganizationEnhanced, OrganizationUpdate } from "@/types/organization";

/**
 * Org admin controls for the public showcase page at `/o/{slug}`.
 *
 * Uses the organization slug from Organization Info settings — edit the slug
 * there if you want a different public URL.
 */
export interface PublicPageSettingsCardProps {
  organization: OrganizationEnhanced;
  canEdit: boolean;
  onUpdated: () => void;
}

export function PublicPageSettingsCard({
  organization,
  canEdit,
  onUpdated,
}: PublicPageSettingsCardProps) {
  const [enabled, setEnabled] = React.useState(
    organization.public_page_enabled ?? false,
  );
  const [passphraseEnabled, setPassphraseEnabled] = React.useState(
    organization.public_page_passphrase_enabled ?? false,
  );
  const [newPassphrase, setNewPassphrase] = React.useState("");
  const [saving, setSaving] = React.useState(false);

  React.useEffect(() => {
    setEnabled(organization.public_page_enabled ?? false);
    setPassphraseEnabled(organization.public_page_passphrase_enabled ?? false);
  }, [organization]);

  const publicPath = publicOrgPagePath(organization.slug);
  const publicUrl =
    typeof window !== "undefined"
      ? `${window.location.origin}${publicPath}`
      : publicPath;

  const copyUrl = async () => {
    try {
      await navigator.clipboard.writeText(publicUrl);
      toast.success("Public page URL copied");
    } catch {
      toast.error("Could not copy URL");
    }
  };

  const saveSettings = async () => {
    setSaving(true);
    try {
      const payload: OrganizationUpdate = {
        public_page_enabled: enabled,
        public_page_passphrase_enabled: passphraseEnabled,
      };
      if (newPassphrase.trim()) {
        payload.public_page_passphrase = newPassphrase.trim();
      } else if (!passphraseEnabled) {
        payload.public_page_passphrase_enabled = false;
      }

      await organizationService.updateOrganization(organization.id, payload);
      setNewPassphrase("");
      toast.success("Public page settings saved");
      onUpdated();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card>
      <CardHeader className="p-5 pb-3">
        <CardTitle className="flex items-center gap-2 text-lg">
          <Globe className="h-5 w-5" />
          Public organization page
        </CardTitle>
        <CardDescription>
          Share a public page where visitors can talk to agents you explicitly
          publish. The URL uses your organization slug — change it under
          Organization Info if you want something more memorable.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6 p-5 pt-0">
        <div className="flex items-center justify-between gap-4 rounded-lg border p-4">
          <div>
            <p className="font-medium">Enable public page</p>
            <p className="text-sm text-muted-foreground">
              When off, <span className="font-mono">{publicPath}</span> returns
              not found.
            </p>
          </div>
          <Switch
            checked={enabled}
            onCheckedChange={setEnabled}
            disabled={!canEdit || saving}
          />
        </div>

        {enabled ? (
          <>
            <div className="space-y-2">
              <Label>Public URL</Label>
              <div className="flex flex-col gap-2 sm:flex-row">
                <Input readOnly value={publicUrl} className="font-mono text-sm" />
                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    onClick={() => void copyUrl()}
                    aria-label="Copy URL"
                  >
                    <Copy className="h-4 w-4" />
                  </Button>
                  <Button type="button" variant="outline" size="icon" asChild>
                    <a href={publicPath} target="_blank" rel="noopener noreferrer">
                      <ExternalLink className="h-4 w-4" />
                    </a>
                  </Button>
                </div>
              </div>
              <p className="text-sm text-muted-foreground">
                Slug: <span className="font-mono">{organization.slug}</span> —
                edit in the Organization Info tab.
              </p>
            </div>

            <div className="space-y-4 rounded-lg border p-4">
              <div className="flex items-start gap-3">
                <Shield className="mt-0.5 h-5 w-5 text-muted-foreground" />
                <div className="flex-1 space-y-4">
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <p className="font-medium">Passphrase protection</p>
                      <p className="text-sm text-muted-foreground">
                        Require visitors to enter a passphrase before viewing agents.
                      </p>
                    </div>
                    <Switch
                      checked={passphraseEnabled}
                      onCheckedChange={setPassphraseEnabled}
                      disabled={!canEdit || saving}
                    />
                  </div>

                  {passphraseEnabled ? (
                    <div className="space-y-2">
                      <Label htmlFor="public-passphrase-set">
                        {organization.public_page_passphrase_enabled
                          ? "Set new passphrase"
                          : "Passphrase"}
                      </Label>
                      <Input
                        id="public-passphrase-set"
                        type="password"
                        autoComplete="new-password"
                        placeholder={
                          organization.public_page_passphrase_enabled
                            ? "Leave blank to keep current"
                            : "Enter passphrase for visitors"
                        }
                        value={newPassphrase}
                        onChange={(e) => setNewPassphrase(e.target.value)}
                        disabled={!canEdit || saving}
                      />
                    </div>
                  ) : null}
                </div>
              </div>
            </div>
          </>
        ) : null}

        {canEdit ? (
          <Button type="button" onClick={() => void saveSettings()} disabled={saving}>
            {saving ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Saving...
              </>
            ) : (
              "Save public page settings"
            )}
          </Button>
        ) : null}
      </CardContent>
    </Card>
  );
}
