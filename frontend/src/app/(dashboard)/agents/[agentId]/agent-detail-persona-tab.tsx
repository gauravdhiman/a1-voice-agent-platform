"use client";

import * as React from "react";
import { toast } from "sonner";
import {
  Bot,
  ChevronDown,
  Eye,
  FileText,
  Info,
  Loader2,
  Pencil,
} from "lucide-react";

import { AgentInstructionsHelpText } from "@/components/agents/agent-instructions-help-text";
import { BasicMarkdownRenderer } from "@/components/markdown/basic-markdown-renderer";
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
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
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
 * a lightweight Markdown renderer here so the Mermaid-capable renderer stays
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
  const [isEditingInstructions, setIsEditingInstructions] =
    React.useState(false);
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
            <div className="flex items-start justify-between gap-3">
              <div>
                <Label
                  htmlFor={
                    isEditingInstructions ? "instructions_markdown" : undefined
                  }
                  className="text-sm font-medium"
                >
                  Additional Instructions
                </Label>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  {isEditingInstructions ? (
                    <AgentInstructionsHelpText />
                  ) : (
                    "Rendered Markdown used to guide the agent."
                  )}
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                {isEditingInstructions && canEdit && voiceTemplates.length > 0 && (
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="outline" size="sm">
                        <FileText className="mr-1.5 h-3.5 w-3.5" />
                        Insert template
                        <ChevronDown className="ml-1 h-3.5 w-3.5" />
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
                            <div className="text-sm font-medium">
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
                {canEdit && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() =>
                      setIsEditingInstructions((current) => !current)
                    }
                    aria-label={
                      isEditingInstructions
                        ? "Preview instructions"
                        : "Edit instructions"
                    }
                  >
                    {isEditingInstructions ? (
                      <>
                        <Eye className="mr-1.5 h-3.5 w-3.5" />
                        Preview
                      </>
                    ) : (
                      <>
                        <Pencil className="mr-1.5 h-3.5 w-3.5" />
                        Edit
                      </>
                    )}
                  </Button>
                )}
              </div>
            </div>

            {isEditingInstructions ? (
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
            ) : (
              <div className="rounded-lg border bg-muted/20 px-4 py-4">
                {agentForm.instructions_markdown?.trim() ? (
                  <BasicMarkdownRenderer
                    content={agentForm.instructions_markdown}
                    className="prose prose-sm max-w-none dark:prose-invert"
                  />
                ) : (
                  <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-muted-foreground">
                    <div className="flex items-center gap-2">
                      <Info className="h-4 w-4" />
                      <span>No additional instructions yet.</span>
                    </div>
                    {canEdit && (
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => setIsEditingInstructions(true)}
                      >
                        Add instructions
                      </Button>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>

          <Sheet open={showSystemPrompt} onOpenChange={setShowSystemPrompt}>
            <SheetTrigger asChild>
              <Button
                type="button"
                variant="outline"
                className="w-full justify-between"
              >
                <span className="flex items-center gap-2">
                  <Eye className="h-4 w-4" />
                  <span>Preview System Prompt</span>
                </span>
                <span className="text-xs text-muted-foreground">
                  Opens in a side panel
                </span>
              </Button>
            </SheetTrigger>
            <SheetContent
              side="right"
              className="flex w-full flex-col sm:max-w-2xl"
            >
              <SheetHeader className="border-b px-6 pb-4 pt-6">
                <SheetTitle>System prompt preview</SheetTitle>
                <SheetDescription>
                  This is the final prompt the AI receives, including your
                  Markdown instructions, system guardrails, and tool guidelines.
                </SheetDescription>
              </SheetHeader>
              <div className="flex-1 overflow-y-auto px-6 py-5">
                {systemPromptLoading ? (
                  <div className="flex items-center justify-center py-12">
                    <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                    <span className="ml-2 text-sm text-muted-foreground">
                      Generating preview...
                    </span>
                  </div>
                ) : systemPromptPreview ? (
                  <BasicMarkdownRenderer
                    content={systemPromptPreview}
                    className="prose prose-sm max-w-none dark:prose-invert"
                  />
                ) : (
                  <div className="py-12 text-center text-sm text-muted-foreground">
                    Unable to generate preview. Save your instructions first,
                    then check the preview.
                  </div>
                )}
              </div>
            </SheetContent>
          </Sheet>
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
