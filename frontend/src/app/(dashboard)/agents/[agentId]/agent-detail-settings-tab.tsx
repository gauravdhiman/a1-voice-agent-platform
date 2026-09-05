"use client";

import * as React from "react";
import { Info, Settings } from "lucide-react";
import { toast } from "sonner";

import { AgentPhoneNumberSelector } from "@/components/agents/agent-phone-number-selector";
import { PresetPicker } from "@/components/agents/preset-picker";
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
import { Textarea } from "@/components/ui/textarea";
import type { VoiceAgent } from "@/types/agent";
import type { PhoneNumberWithAgent } from "@/types/phone-number";

import type { AgentDetailFormState } from "./agent-detail-types";

interface AgentDetailSettingsTabProps {
  agent: VoiceAgent;
  agentForm: AgentDetailFormState;
  setAgentForm: React.Dispatch<React.SetStateAction<AgentDetailFormState>>;
  canEdit: boolean;
  isPlatformAdmin: boolean;
  assignedPhoneNumber: PhoneNumberWithAgent | null;
  setAssignedPhoneNumber: React.Dispatch<
    React.SetStateAction<PhoneNumberWithAgent | null>
  >;
}

/** Agent activation, public-demo settings, phone routing, and voice profile. */
export function AgentDetailSettingsTab({
  agent,
  agentForm,
  setAgentForm,
  canEdit,
  isPlatformAdmin,
  assignedPhoneNumber,
  setAssignedPhoneNumber,
}: AgentDetailSettingsTabProps) {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="p-5 pb-3">
          <CardTitle className="flex items-center space-x-2 text-lg">
            <Settings className="h-5 w-5" />
            <span>Agent Settings</span>
          </CardTitle>
          <CardDescription>
            Control how this agent is used and where it can respond
          </CardDescription>
        </CardHeader>
        <CardContent className="p-5 pt-0 space-y-6">
          <div className="space-y-2">
            <AgentPhoneNumberSelector
              agentId={agent.id}
              organizationId={agent.organization_id}
              canEdit={canEdit}
              onAssignmentChange={setAssignedPhoneNumber}
            />
          </div>

          <div className="border-t pt-5 space-y-6">
            <div className="space-y-2">
              <div className="flex items-center space-x-2">
                <Switch
                  id="active"
                  checked={agentForm.is_active}
                  onCheckedChange={(checked) => {
                    if (checked && !assignedPhoneNumber) {
                      toast.warning(
                        "A phone number is required to activate this agent. Please assign a phone number first.",
                      );
                      return;
                    }
                    setAgentForm({
                      ...agentForm,
                      is_active: checked === true,
                      ...(checked
                        ? {}
                        : { is_published_on_public_page: false }),
                    });
                  }}
                  disabled={!canEdit}
                />
                <Label
                  htmlFor="active"
                  className="text-sm font-normal cursor-pointer"
                >
                  Agent is active and ready to handle calls
                </Label>
              </div>
              {!assignedPhoneNumber && (
                <p className="text-xs text-amber-600 flex items-center gap-1">
                  <Info className="w-3 h-3" />A phone number must be configured
                  before the agent can be activated.
                </p>
              )}
            </div>

            <div className="space-y-2">
              <div className="flex items-center space-x-2">
                <Switch
                  id="public-page-publish"
                  checked={agentForm.is_published_on_public_page}
                  onCheckedChange={(checked) => {
                    if (checked && !agentForm.is_active) {
                      toast.warning(
                        "Only active agents can be published on the public organization page.",
                      );
                      return;
                    }
                    setAgentForm({
                      ...agentForm,
                      is_published_on_public_page: checked === true,
                    });
                  }}
                  disabled={!canEdit || !agentForm.is_active}
                />
                <Label
                  htmlFor="public-page-publish"
                  className="text-sm font-normal cursor-pointer"
                >
                  Publish on public organization page
                </Label>
              </div>
              <p className="text-xs text-muted-foreground">
                When enabled, visitors at your organization&apos;s public URL
                can start a voice call with this agent. Requires the agent to be
                active.
              </p>
            </div>

            <div className="space-y-2">
              <div className="flex items-center space-x-2">
                <Switch
                  id="call-recording"
                  checked={agentForm.call_recording_enabled}
                  onCheckedChange={(checked) =>
                    setAgentForm({
                      ...agentForm,
                      call_recording_enabled: checked === true,
                    })
                  }
                  disabled={!canEdit}
                />
                <Label
                  htmlFor="call-recording"
                  className="text-sm font-normal cursor-pointer"
                >
                  Record calls for this agent
                </Label>
              </div>
              <p className="text-xs text-muted-foreground">
                When enabled, your team can review recordings of this
                agent&apos;s calls. Inform callers and follow applicable consent
                requirements.
              </p>
            </div>

            {isPlatformAdmin && (
              <div className="space-y-3 rounded-md border border-amber-200 bg-amber-50 p-3">
                <div className="flex items-center space-x-2">
                  <Switch
                    id="is-demo"
                    checked={agentForm.is_demo}
                    onCheckedChange={(checked) =>
                      setAgentForm({
                        ...agentForm,
                        is_demo: checked === true,
                        demo_slug: checked ? agentForm.demo_slug : "",
                      })
                    }
                    disabled={!canEdit}
                  />
                  <Label
                    htmlFor="is-demo"
                    className="text-sm font-medium text-amber-900 cursor-pointer"
                  >
                    Demo agent (credit-exempt, public at /demo/&#123;slug&#125;)
                  </Label>
                </div>
                <p className="text-xs text-amber-800">
                  Platform-admin only. Demo agents bypass platform credit and
                  concurrency checks, but can be protected with a trial-call
                  budget and per-call duration cap. Use -1 for unlimited.
                </p>
                {agentForm.is_demo && (
                  <div className="space-y-3 pt-1">
                    <div className="space-y-2">
                      <Label htmlFor="demo-slug" className="text-xs">
                        Demo slug *
                      </Label>
                      <Input
                        id="demo-slug"
                        value={agentForm.demo_slug}
                        onChange={(event) =>
                          setAgentForm({
                            ...agentForm,
                            demo_slug: event.target.value
                              .toLowerCase()
                              .replace(/\s+/g, "-"),
                          })
                        }
                        placeholder="e.g. acme-dental-demo"
                        disabled={!canEdit}
                      />
                      <p className="text-xs text-muted-foreground">
                        Unique across all demo agents. Lowercase letters,
                        numbers, hyphens only. Public page:{" "}
                        <code>/demo/{agentForm.demo_slug || "your-slug"}</code>
                        {agentForm.demo_slug && (
                          <span>
                            {" "}
                            —{" "}
                            <a
                              href={`/demo/${agentForm.demo_slug}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="font-medium text-primary underline underline-offset-4 hover:text-primary/80"
                            >
                              {typeof window !== "undefined"
                                ? `${window.location.origin}/demo/${agentForm.demo_slug}`
                                : `/demo/${agentForm.demo_slug}`}{" "}
                              ↗
                            </a>
                          </span>
                        )}
                      </p>
                    </div>

                    <div className="grid gap-3 sm:grid-cols-2">
                      <div className="space-y-2">
                        <Label
                          htmlFor="demo-calls-remaining"
                          className="text-xs"
                        >
                          Demo calls remaining
                        </Label>
                        <Input
                          id="demo-calls-remaining"
                          type="number"
                          min={-1}
                          step={1}
                          value={agentForm.demo_calls_remaining}
                          onChange={(event) =>
                            setAgentForm({
                              ...agentForm,
                              demo_calls_remaining: Number(event.target.value),
                            })
                          }
                          disabled={!canEdit}
                        />
                        <p className="text-xs text-muted-foreground">
                          0 disables new calls. Use -1 for unlimited calls.
                        </p>
                      </div>
                      <div className="space-y-2">
                        <Label
                          htmlFor="demo-max-call-duration"
                          className="text-xs"
                        >
                          Maximum call duration (minutes)
                        </Label>
                        <Input
                          id="demo-max-call-duration"
                          type="number"
                          min={-1}
                          step={1}
                          value={agentForm.demo_max_call_duration_minutes}
                          onChange={(event) =>
                            setAgentForm({
                              ...agentForm,
                              demo_max_call_duration_minutes: Number(
                                event.target.value,
                              ),
                            })
                          }
                          disabled={!canEdit}
                        />
                        <p className="text-xs text-muted-foreground">
                          Use -1 for unlimited duration. The timer starts when a
                          caller connects.
                        </p>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="public-description" className="text-xs">
                        Public description
                      </Label>
                      <Textarea
                        id="public-description"
                        value={agentForm.public_description}
                        onChange={(event) =>
                          setAgentForm({
                            ...agentForm,
                            public_description: event.target.value,
                          })
                        }
                        placeholder="e.g. This demo agent helps book dental appointments, answers FAQs about cleanings and insurance, and showcases our 24x7 AI voice experience."
                        disabled={!canEdit}
                        rows={3}
                      />
                      <p className="text-xs text-muted-foreground">
                        Shown on{" "}
                        <code>/demo/{agentForm.demo_slug || "your-slug"}</code>{" "}
                        to visitors. If empty, the agent&apos;s mission will be
                        shown.
                      </p>
                    </div>

                    <div className="space-y-2">
                      <Label
                        htmlFor="demo-public-result-url"
                        className="text-xs"
                      >
                        Public result URL (optional)
                      </Label>
                      <Input
                        id="demo-public-result-url"
                        type="url"
                        value={agentForm.demo_public_result_url}
                        onChange={(event) =>
                          setAgentForm({
                            ...agentForm,
                            demo_public_result_url: event.target.value,
                          })
                        }
                        placeholder="https://docs.google.com/spreadsheets/d/..."
                        disabled={!canEdit}
                      />
                      <p className="text-xs text-muted-foreground">
                        After a successful provider handoff, the receipt page
                        shows an <strong>Open result</strong> button to this
                        HTTPS URL. Use only a dedicated public demo view or data
                        store; leave blank to hide the button.
                      </p>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="p-5 pb-3">
          <CardTitle className="text-lg">Voice Profile</CardTitle>
          <CardDescription>
            Choose how this agent sounds when speaking with callers
          </CardDescription>
        </CardHeader>
        <CardContent className="p-5 pt-0">
          <PresetPicker
            organizationId={agent.organization_id}
            usePlatformCredits={agentForm.use_platform_credits}
            value={agentForm.preset_id}
            onChange={(presetId) =>
              setAgentForm({ ...agentForm, preset_id: presetId })
            }
            disabled={!canEdit}
          />
        </CardContent>
      </Card>
    </div>
  );
}
