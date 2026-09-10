"use client";

import * as React from "react";
import { toast } from "sonner";
import {
  Bot,
  ChevronDown,
  Eye,
  EyeOff,
  FileText,
  Info,
  Loader2,
} from "lucide-react";

import { AgentInstructionsHelpText } from "@/components/agents/agent-instructions-help-text";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useAgentSystemPrompt } from "@/hooks/use-agent-queries";
import {
  buildMarkdownFromTemplate,
  DEFAULT_AGENT_INSTRUCTIONS_PLACEHOLDER,
} from "@/lib/agent-instructions";
import { voiceTemplateService } from "@/services/voice-template-service";
import type { VoiceTemplate } from "@/types/voice-template";

import type { AgentDetailFormState } from "./agent-detail-types";

interface AgentDetailPersonaTabProps {
  agentId: string;
  agentForm: AgentDetailFormState;
  setAgentForm: React.Dispatch<React.SetStateAction<AgentDetailFormState>>;
  canEdit: boolean;
}

/**
 * Persona and instruction editing for an agent.
 *
 * This is intentionally a separate client chunk: the template menu is not
 * needed to load or use the other agent tabs. The system prompt preview uses
 * a lightweight raw-Markdown view here so the Mermaid-capable renderer stays
 * out of the first agent route compile.
 */
export function AgentDetailPersonaTab({
  agentId,
  agentForm,
  setAgentForm,
  canEdit,
}: AgentDetailPersonaTabProps) {
  const [voiceTemplates, setVoiceTemplates] = React.useState<VoiceTemplate[]>(
    [],
  );
  const [pendingTemplate, setPendingTemplate] =
    React.useState<VoiceTemplate | null>(null);
  const [showSystemPrompt, setShowSystemPrompt] = React.useState(false);
  const { data: systemPromptPreview, isLoading: systemPromptLoading } =
    useAgentSystemPrompt(agentId, showSystemPrompt);

  React.useEffect(() => {
    let cancelled = false;
    voiceTemplateService
      .listTemplates()
      .then((templates) => {
        if (!cancelled) setVoiceTemplates(templates);
      })
      .catch(() => {
        // Templates are optional; the editor remains fully usable without them.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const insertTemplate = React.useCallback(
    (template: VoiceTemplate) => {
      const markdown = buildMarkdownFromTemplate(template);
      setAgentForm((current) => ({
        ...current,
        persona: template.persona || current.persona,
        tone: template.tone || current.tone,
        instructions_markdown: markdown,
      }));
      toast.success(`"${template.name}" template inserted`);
      setPendingTemplate(null);
    },
    [setAgentForm],
  );

  return (
    <>
      <Card data-tour="agent-detail-persona">
        <CardHeader className="p-5 pb-3">
          <CardTitle className="flex items-center space-x-2 text-lg">
            <Bot className="h-5 w-5" />
            <span>Agent Persona</span>
          </CardTitle>
          <CardDescription>
            Define how your agent represents your business and communicates with
            callers
          </CardDescription>
        </CardHeader>
        <CardContent className="p-5 pt-0 space-y-4">
          <div className="bg-blue-50 border border-blue-200 rounded-md p-3 flex items-start gap-2">
            <p className="text-sm text-blue-800">
              The information you provide here helps the AI agent represent your
              business accurately when speaking with callers.
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="name">Name</Label>
            <Input
              id="name"
              value={agentForm.name}
              onChange={(event) =>
                setAgentForm({ ...agentForm, name: event.target.value })
              }
              disabled={!canEdit}
            />
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="agent-role">Agent Role</Label>
              <Input
                id="agent-role"
                value={agentForm.persona}
                onChange={(event) =>
                  setAgentForm({ ...agentForm, persona: event.target.value })
                }
                placeholder="Front Desk Coordinator"
                disabled={!canEdit}
              />
              <p className="text-xs text-muted-foreground">
                The character or job title this agent represents.
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="communication-style">Communication Style</Label>
              <Input
                id="communication-style"
                value={agentForm.tone}
                onChange={(event) =>
                  setAgentForm({ ...agentForm, tone: event.target.value })
                }
                placeholder="Warm, professional, and reassuring"
                disabled={!canEdit}
              />
              <p className="text-xs text-muted-foreground">
                How the agent should communicate with callers.
              </p>
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <Label
                  htmlFor="instructions_markdown"
                  className="text-sm font-medium"
                >
                  Additional Instructions
                </Label>
                <p className="text-xs text-muted-foreground mt-0.5">
                  <AgentInstructionsHelpText />
                </p>
              </div>
              {canEdit && voiceTemplates.length > 0 && (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" size="sm">
                      <FileText className="w-3.5 h-3.5 mr-1.5" />
                      Insert template
                      <ChevronDown className="w-3.5 h-3.5 ml-1" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-64">
                    {voiceTemplates.map((template) => (
                      <DropdownMenuItem
                        key={template.id}
                        onClick={() => {
                          if (agentForm.instructions_markdown?.trim()) {
                            setPendingTemplate(template);
                            return;
                          }
                          insertTemplate(template);
                        }}
                      >
                        <div>
                          <div className="font-medium text-sm">
                            {template.name}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {template.industry}
                          </div>
                        </div>
                      </DropdownMenuItem>
                    ))}
                  </DropdownMenuContent>
                </DropdownMenu>
              )}
            </div>
            <Textarea
              id="instructions_markdown"
              value={agentForm.instructions_markdown}
              onChange={(event) =>
                setAgentForm({
                  ...agentForm,
                  instructions_markdown: event.target.value,
                })
              }
              placeholder={DEFAULT_AGENT_INSTRUCTIONS_PLACEHOLDER}
              className="min-h-[400px] font-mono text-sm"
              disabled={!canEdit}
            />
          </div>

          <div className="border rounded-lg overflow-hidden">
            <button
              type="button"
              onClick={() => setShowSystemPrompt((current) => !current)}
              className="w-full px-4 py-3 bg-slate-50 hover:bg-slate-100 transition-colors flex items-center justify-between text-left"
            >
              <div className="flex items-center gap-2">
                {showSystemPrompt ? (
                  <EyeOff className="h-4 w-4 text-slate-600" />
                ) : (
                  <Eye className="h-4 w-4 text-slate-600" />
                )}
                <span className="font-medium text-sm">
                  Preview System Prompt
                </span>
              </div>
              <span className="text-xs text-muted-foreground">
                {showSystemPrompt ? "Click to hide" : "Click to view"}
              </span>
            </button>

            {showSystemPrompt && (
              <div className="p-4 bg-slate-50 border-t">
                <p className="text-sm text-muted-foreground mb-3">
                  This is the final system prompt the AI receives — your
                  markdown instructions plus system guardrails and tool
                  guidelines.
                </p>
                {systemPromptLoading ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                    <span className="ml-2 text-sm text-muted-foreground">
                      Generating preview...
                    </span>
                  </div>
                ) : systemPromptPreview ? (
                  <div className="bg-white border rounded-md p-4 overflow-x-auto">
                    <div className="mb-2 flex items-center gap-2 text-xs text-muted-foreground">
                      <Info className="h-3.5 w-3.5" />
                      <span>Raw compiled Markdown</span>
                    </div>
                    <pre className="whitespace-pre-wrap break-words text-xs leading-relaxed text-slate-700">
                      {systemPromptPreview}
                    </pre>
                  </div>
                ) : (
                  <div className="text-center py-8 text-muted-foreground text-sm">
                    Unable to generate preview. Save your instructions first,
                    then check the preview.
                  </div>
                )}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      <Dialog
        open={!!pendingTemplate}
        onOpenChange={(open) => !open && setPendingTemplate(null)}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Replace current instructions?</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            Inserting the{" "}
            <span className="font-medium text-foreground">
              {pendingTemplate?.name}
            </span>{" "}
            template will replace your current agent instructions. This action
            cannot be undone.
          </p>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button variant="outline" onClick={() => setPendingTemplate(null)}>
              Cancel
            </Button>
            <Button
              onClick={() => {
                if (pendingTemplate) insertTemplate(pendingTemplate);
              }}
            >
              Replace instructions
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
