"use client";

import * as React from "react";
import Link from "next/link";
import { toast } from "sonner";
import {
  Eye,
  EyeOff,
  ExternalLink,
  FileText,
  FolderOpen,
  Loader2,
  Zap,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Switch } from "@/components/ui/switch";
import { cn } from "@/lib/utils";
import { BasicMarkdownRenderer } from "@/components/markdown/basic-markdown-renderer";
import { skillService } from "@/services/skill-service";
import type { OrganizationSkill, SkillFileSummary } from "@/types/skill";
import type { VoiceAgent } from "@/types/agent";

interface ViewingFile {
  filePath: string;
  content: string;
}

interface AgentDetailSkillsTabProps {
  agent: VoiceAgent;
  canEdit: boolean;
}

/** Loads organization skills only when the Skills tab is opened. */
export function AgentDetailSkillsTab({
  agent,
  canEdit,
}: AgentDetailSkillsTabProps) {
  const [orgSkills, setOrgSkills] = React.useState<OrganizationSkill[]>([]);
  const [agentSkillIds, setAgentSkillIds] = React.useState<Set<string>>(
    new Set(),
  );
  const [skillsLoading, setSkillsLoading] = React.useState(true);
  const [skillToggling, setSkillToggling] = React.useState<string | null>(null);
  const [viewingSkill, setViewingSkill] =
    React.useState<OrganizationSkill | null>(null);
  const [viewingSkillFiles, setViewingSkillFiles] = React.useState<
    SkillFileSummary[]
  >([]);
  const [viewingFile, setViewingFile] = React.useState<ViewingFile | null>(
    null,
  );
  const [loadingViewFile, setLoadingViewFile] = React.useState(false);

  React.useEffect(() => {
    let cancelled = false;
    setSkillsLoading(true);
    Promise.all([
      skillService.getOrganizationSkills(agent.organization_id),
      skillService.getAgentSkills(agent.id),
    ])
      .then(([skills, agentSkills]) => {
        if (cancelled) return;
        setOrgSkills(skills.filter((skill) => skill.is_active));
        setAgentSkillIds(
          new Set(agentSkills.map((agentSkill) => agentSkill.skill_id)),
        );
      })
      .catch((error) => {
        if (!cancelled) console.error("Failed to load skills:", error);
      })
      .finally(() => {
        if (!cancelled) setSkillsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [agent.id, agent.organization_id]);

  React.useEffect(() => {
    let cancelled = false;
    if (!viewingSkill) {
      setViewingSkillFiles([]);
      setViewingFile(null);
      return;
    }

    setViewingFile(null);
    skillService
      .getSkillFiles(agent.organization_id, viewingSkill.id)
      .then((files) => {
        if (!cancelled) setViewingSkillFiles(files);
      })
      .catch(() => {
        if (!cancelled) setViewingSkillFiles([]);
      });

    return () => {
      cancelled = true;
    };
  }, [agent.organization_id, viewingSkill]);

  const handleSkillToggle = React.useCallback(
    async (skillId: string, assign: boolean) => {
      setSkillToggling(skillId);
      try {
        if (assign) {
          await skillService.assignSkill(agent.id, skillId);
          setAgentSkillIds((previous) => new Set([...previous, skillId]));
        } else {
          await skillService.unassignSkill(agent.id, skillId);
          setAgentSkillIds((previous) => {
            const next = new Set(previous);
            next.delete(skillId);
            return next;
          });
        }
      } catch {
        toast.error(`Failed to ${assign ? "assign" : "unassign"} skill`);
      } finally {
        setSkillToggling(null);
      }
    },
    [agent.id],
  );

  const showSkill = React.useCallback((skill: OrganizationSkill) => {
    setViewingSkill(skill);
  }, []);

  const loadFile = React.useCallback(
    async (file: SkillFileSummary) => {
      if (!viewingSkill) return;
      setLoadingViewFile(true);
      try {
        const content = await skillService.getSkillFileContent(
          agent.organization_id,
          viewingSkill.slug,
          file.file_path,
        );
        setViewingFile({ filePath: file.file_path, content });
      } catch {
        toast.error("Failed to load file");
      } finally {
        setLoadingViewFile(false);
      }
    },
    [agent.organization_id, viewingSkill],
  );

  const makeSkillVisible = React.useCallback(async () => {
    if (!viewingSkill) return;
    try {
      await skillService.updateSkill(agent.organization_id, viewingSkill.id, {
        is_visible: true,
      });
      toast.success("Skill is now visible in the library");
      const skills = await skillService.getOrganizationSkills(
        agent.organization_id,
      );
      setOrgSkills(skills.filter((skill) => skill.is_active));
      setViewingSkill((current) =>
        current ? { ...current, is_visible: true } : current,
      );
    } catch {
      toast.error("Failed to update visibility");
    }
  }, [agent.organization_id, viewingSkill]);

  return (
    <>
      <Card>
        <CardHeader className="p-5 pb-3">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center space-x-2 text-lg">
                <Zap className="h-5 w-5" />
                <span>Agent Skills</span>
              </CardTitle>
              <CardDescription>
                Assign skills to give this agent domain-specific knowledge and
                procedures. Skills are loaded on-demand during conversations.
              </CardDescription>
            </div>
            {canEdit && agent.organization_id && (
              <Link
                href={`/organization?org_id=${agent.organization_id}&tab=skills`}
                className="inline-flex items-center gap-1 text-sm text-primary hover:text-primary/80 underline underline-offset-2"
              >
                <ExternalLink className="h-3.5 w-3.5" />
                Manage Skills
              </Link>
            )}
          </div>
        </CardHeader>
        <CardContent className="p-5 pt-2">
          {skillsLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin" />
              <span className="ml-2 text-sm text-muted-foreground">
                Loading skills...
              </span>
            </div>
          ) : orgSkills.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Zap className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No skills available for this organization.</p>
              <p className="text-sm mt-1">
                Add skills from Organization Settings to get started.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {orgSkills.map((skill) => {
                const isAssigned = agentSkillIds.has(skill.id);
                const isToggling = skillToggling === skill.id;
                return (
                  <div
                    key={skill.id}
                    className={cn(
                      "flex items-center justify-between p-4 border rounded-lg transition-colors cursor-pointer",
                      isAssigned
                        ? "bg-primary/5 border-primary/20"
                        : "hover:bg-muted/50",
                    )}
                    onClick={() => showSkill(skill)}
                  >
                    <div className="flex items-start gap-3 flex-1 min-w-0">
                      <div onClick={(event) => event.stopPropagation()}>
                        <Switch
                          checked={isAssigned}
                          onCheckedChange={(checked) =>
                            handleSkillToggle(skill.id, checked === true)
                          }
                          disabled={!canEdit || isToggling}
                        />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-sm">
                            {skill.name}
                          </span>
                          <Badge
                            variant={
                              skill.source_skill_id ? "secondary" : "outline"
                            }
                            className="text-xs"
                          >
                            {skill.source_skill_id ? "Platform" : "Custom"}
                          </Badge>
                          {!skill.is_visible && (
                            <Badge
                              variant="outline"
                              className="text-[11px] border-orange-200 text-orange-600 bg-orange-50"
                            >
                              <EyeOff className="h-3 w-3 mr-0.5" /> Hidden
                            </Badge>
                          )}
                        </div>
                        {skill.description && (
                          <p className="text-xs text-muted-foreground mt-0.5 truncate">
                            {skill.description}
                          </p>
                        )}
                      </div>
                    </div>
                    <Eye className="h-4 w-4 text-muted-foreground" />
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      <Sheet
        open={!!viewingSkill}
        onOpenChange={(open) => {
          if (!open) setViewingSkill(null);
        }}
      >
        <SheetContent className="flex flex-col w-full sm:max-w-2xl">
          <SheetHeader className="px-6 pt-6 pb-4 border-b">
            <SheetTitle className="flex items-center gap-2">
              {viewingSkill?.name}
              <Badge
                variant={
                  viewingSkill?.source_skill_id ? "secondary" : "outline"
                }
                className="text-xs"
              >
                {viewingSkill?.source_skill_id ? "Platform" : "Custom"}
              </Badge>
            </SheetTitle>
            {viewingSkill?.description && (
              <SheetDescription>{viewingSkill.description}</SheetDescription>
            )}
          </SheetHeader>

          {viewingSkill && !viewingSkill.is_visible && (
            <div className="px-6 py-2.5 border-b bg-orange-50 flex items-center justify-between gap-3">
              <div className="flex items-center gap-1.5 text-sm text-orange-700">
                <EyeOff className="h-4 w-4" />
                <span>
                  This skill is hidden from your organization library.
                </span>
              </div>
              {canEdit && (
                <Button
                  variant="outline"
                  size="sm"
                  className="h-7 text-xs"
                  onClick={makeSkillVisible}
                >
                  <Eye className="h-3.5 w-3.5 mr-1" />
                  Show in Library
                </Button>
              )}
            </div>
          )}

          {viewingSkillFiles.length > 0 && (
            <div className="px-6 py-2 border-b flex flex-wrap gap-1 bg-muted/20">
              <button
                className={cn(
                  "px-2.5 py-1 rounded text-xs flex items-center gap-1 transition-colors",
                  !viewingFile
                    ? "bg-primary/10 text-primary font-medium"
                    : "text-muted-foreground hover:bg-muted",
                )}
                onClick={() => setViewingFile(null)}
              >
                <FileText className="h-3 w-3" />
                SKILL.md
              </button>
              {(() => {
                const folders: Record<string, SkillFileSummary[]> = {};
                const rootFiles: SkillFileSummary[] = [];
                viewingSkillFiles.forEach((file) => {
                  const parts = file.file_path.split("/");
                  if (parts.length > 1) {
                    const folder = parts[0];
                    if (!folders[folder]) folders[folder] = [];
                    folders[folder].push(file);
                  } else {
                    rootFiles.push(file);
                  }
                });
                return (
                  <>
                    {Object.entries(folders).map(([folder, files]) => (
                      <div key={folder} className="flex items-center gap-0.5">
                        <span className="text-[10px] text-muted-foreground ml-1">
                          <FolderOpen className="h-3 w-3 inline mr-0.5" />
                          {folder}/
                        </span>
                        {files.map((file) => (
                          <button
                            key={file.id}
                            className={cn(
                              "px-2 py-1 rounded text-xs flex items-center gap-1 transition-colors",
                              viewingFile?.filePath === file.file_path
                                ? "bg-primary/10 text-primary font-medium"
                                : "text-muted-foreground hover:bg-muted",
                            )}
                            onClick={() => loadFile(file)}
                          >
                            <FileText className="h-3 w-3" />
                            {file.file_path.split("/").pop()}
                          </button>
                        ))}
                      </div>
                    ))}
                    {rootFiles.map((file) => (
                      <button
                        key={file.id}
                        className={cn(
                          "px-2 py-1 rounded text-xs flex items-center gap-1 transition-colors",
                          viewingFile?.filePath === file.file_path
                            ? "bg-primary/10 text-primary font-medium"
                            : "text-muted-foreground hover:bg-muted",
                        )}
                        onClick={() => loadFile(file)}
                      >
                        <FileText className="h-3 w-3" />
                        {file.file_path}
                      </button>
                    ))}
                  </>
                );
              })()}
            </div>
          )}

          {loadingViewFile ? (
            <div className="flex-1 flex items-center justify-center">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          ) : viewingFile ? (
            <>
              <div className="px-6 py-1.5 border-b bg-muted/30 text-xs text-muted-foreground flex items-center gap-2">
                <FileText className="h-3.5 w-3.5" />
                <code>{viewingFile.filePath}</code>
              </div>
              {viewingFile.filePath.endsWith(".json") ? (
                <div className="flex-1 overflow-y-auto p-5">
                  <pre className="text-xs font-mono bg-muted/50 rounded-lg p-4 overflow-x-auto whitespace-pre">
                    {(() => {
                      try {
                        return JSON.stringify(
                          JSON.parse(viewingFile.content),
                          null,
                          2,
                        );
                      } catch {
                        return viewingFile.content;
                      }
                    })()}
                  </pre>
                </div>
              ) : viewingFile.filePath.match(
                  /\.(py|js|ts|sh|bash|yaml|yml|toml)$/,
                ) ? (
                <div className="flex-1 overflow-y-auto p-5">
                  <pre className="text-xs font-mono bg-muted/50 rounded-lg p-4 overflow-x-auto whitespace-pre">
                    {viewingFile.content}
                  </pre>
                </div>
              ) : (
                <div className="flex-1 overflow-y-auto px-6 py-5 prose prose-sm prose-slate max-w-none">
                  <BasicMarkdownRenderer content={viewingFile.content} />
                </div>
              )}
            </>
          ) : (
            <div className="flex-1 overflow-y-auto px-6 py-5 prose prose-sm prose-slate max-w-none">
              {viewingSkill && (
                <BasicMarkdownRenderer content={viewingSkill.content} />
              )}
            </div>
          )}
        </SheetContent>
      </Sheet>
    </>
  );
}
