"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Copy, Code, ExternalLink, Info, Settings, Loader2, AlertTriangle, CheckCircle } from "lucide-react";
import { toast } from "sonner";
import { agentService, type EmbedConfig, type EmbedConfigCreate } from "@/services/agent-service";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

interface EmbedButtonConfigProps {
  agentId: string;
}

export function EmbedButtonConfig({ agentId }: EmbedButtonConfigProps) {
  const [open, setOpen] = useState(false);
  const [showCode, setShowCode] = useState<boolean | null>(null);
  const [justSaved, setJustSaved] = useState(false);
  const queryClient = useQueryClient();

  const { data: config, isLoading } = useQuery({
    queryKey: ["embed-config", agentId],
    queryFn: () => agentService.getEmbedConfig(agentId),
    enabled: open,
  });

  const [formData, setFormData] = useState<EmbedConfigCreate>({
    buttonText: "Call Us",
    buttonColor: "#3b82f6",
    buttonTextColor: "#ffffff",
    buttonBorderRadius: 8,
    buttonSize: "medium",
    buttonPosition: "bottom-right",
    buttonStyle: "filled",
    allowedDomains: [],
    customCss: "",
    isActive: true,
    dailyCallLimit: 100,
  });

  useEffect(() => {
    if (config) {
      setFormData({
        buttonText: config.buttonText ?? "Call Us",
        buttonColor: config.buttonColor ?? "#3b82f6",
        buttonTextColor: config.buttonTextColor ?? "#ffffff",
        buttonBorderRadius: config.buttonBorderRadius ?? 8,
        buttonSize: config.buttonSize ?? "medium",
        buttonPosition: config.buttonPosition ?? "bottom-right",
        buttonStyle: config.buttonStyle ?? "filled",
        allowedDomains: config.allowedDomains ?? [],
        customCss: config.customCss ?? "",
        isActive: config.isActive ?? true,
        dailyCallLimit: config.dailyCallLimit ?? 100,
      });
      if (showCode === null) {
        setShowCode(true);
      }
    } else if (!isLoading && showCode === null) {
      setShowCode(false);
    }
  }, [config, isLoading, showCode]);

  useEffect(() => {
    if (!open) {
      setShowCode(null);
      setJustSaved(false);
    }
  }, [open]);

  const saveMutation = useMutation({
    mutationFn: (data: EmbedConfigCreate) => agentService.createEmbedConfig(agentId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["embed-config", agentId] });
      setJustSaved(true);
      setShowCode(true);
    },
    onError: (error) => {
      toast.error("Failed to save embed configuration");
      console.error(error);
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: () => agentService.deleteEmbedConfig(agentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["embed-config", agentId] });
      toast.success("Embed configuration deleted");
      setOpen(false);
      setShowCode(false);
    },
    onError: (error) => {
      toast.error("Failed to delete embed configuration");
      console.error(error);
    },
  });

  const handleSave = () => {
    saveMutation.mutate(formData);
  };

  const generateEmbedCode = (configData: EmbedConfigCreate | EmbedConfig) => {
    const baseUrl = typeof window !== "undefined" ? window.location.origin : "";
    return `<!-- AI Voice Agent Call Button -->
<script
  src="${baseUrl}/embed/call-button.js"
  data-agent-id="${agentId}"
  data-button-text="${configData.buttonText}"
  data-button-color="${configData.buttonColor}"
  data-button-text-color="${configData.buttonTextColor}"
  data-button-border-radius="${configData.buttonBorderRadius}"
  data-button-size="${configData.buttonSize}"
  data-button-position="${configData.buttonPosition}"
  data-button-style="${configData.buttonStyle || 'filled'}"
></script>`;
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success("Copied to clipboard");
  };

  const effectiveShowCode = showCode ?? false;
  const configForCode = config || formData;

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          <Code className="mr-2 h-4 w-4" />
          Embed Button
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Embed Call Button</DialogTitle>
          <DialogDescription>
            Configure and generate an embeddable call button for your website.
            Visitors can click this button to start a voice call with your agent.
          </DialogDescription>
        </DialogHeader>

        {isLoading && showCode === null ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : effectiveShowCode ? (
          <div className="space-y-4">
            {justSaved && (
              <div className="bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 p-4 rounded-lg">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="h-5 w-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="font-medium text-amber-800 dark:text-amber-200">
                      Configuration updated successfully!
                    </p>
                    <p className="text-sm text-amber-700 dark:text-amber-300 mt-1">
                      Copy the embed code below and paste it on your website to apply the new button styling.
                    </p>
                  </div>
                </div>
              </div>
            )}

            <div className="bg-muted p-4 rounded-lg">
              <div className="flex justify-between items-center mb-2">
                <Label>Embed Code</Label>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => copyToClipboard(generateEmbedCode(configForCode))}
                >
                  <Copy className="h-4 w-4 mr-1" />
                  Copy
                </Button>
              </div>
              <pre className="text-xs bg-background p-3 rounded overflow-x-auto">
                {generateEmbedCode(configForCode)}
              </pre>
            </div>

            <div className="bg-blue-50 dark:bg-blue-950 p-4 rounded-lg">
              <h4 className="font-medium mb-2">Installation Instructions</h4>
              <ol className="text-sm space-y-2 list-decimal list-inside">
                <li>Copy the code above</li>
                <li>Paste it into your website&apos;s HTML, just before the closing &lt;/body&gt; tag</li>
                <li>The button will appear on your website automatically</li>
              </ol>
            </div>

            <Button variant="outline" onClick={() => { setShowCode(false); setJustSaved(false); }}>
              <Settings className="h-4 w-4 mr-2" />
              Edit Configuration
            </Button>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Preview */}
            <div className="border rounded-lg p-6 space-y-4">
              <Label>Live Preview</Label>
              <div className="relative h-40 bg-gray-100 dark:bg-gray-800 rounded">
                <button
                  style={{
                    backgroundColor: formData.buttonStyle === "outline" ? "#ffffff" : formData.buttonColor,
                    color: formData.buttonTextColor,
                    borderRadius: `${formData.buttonBorderRadius}px`,
                    padding: formData.buttonSize === "small" ? "8px 16px" : formData.buttonSize === "large" ? "16px 32px" : "12px 24px",
                    fontSize: formData.buttonSize === "small" ? "14px" : formData.buttonSize === "large" ? "18px" : "16px",
                    position: "absolute",
                    border: formData.buttonStyle === "outline" ? `2px solid ${formData.buttonColor}` : "none",
                    ...((formData.buttonPosition ?? "bottom-right") === "center" ? { top: "50%", left: "50%", transform: "translate(-50%, -50%)" } : {
                      ...((formData.buttonPosition ?? "bottom-right").includes("bottom") ? { bottom: "20px" } : { top: "20px" }),
                      ...((formData.buttonPosition ?? "bottom-right").includes("center") ? { left: "50%", transform: "translateX(-50%)" } : {
                        ...((formData.buttonPosition ?? "bottom-right").includes("right") ? { right: "20px" } : { left: "20px" }),
                      }),
                    }),
                  }}
                  className="font-medium shadow-lg hover:opacity-90 transition-opacity"
                >
                  {formData.buttonText}
                </button>
              </div>
            </div>

            {/* Button Configuration */}
            <div className="space-y-4">
              <h4 className="font-medium">Button Appearance</h4>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="buttonText">Button Text</Label>
                  <Input
                    id="buttonText"
                    value={formData.buttonText}
                    onChange={(e) => setFormData({ ...formData, buttonText: e.target.value })}
                    placeholder="Call Us"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="buttonSize">Button Size</Label>
                  <Select
                    value={formData.buttonSize}
                    onValueChange={(value: "small" | "medium" | "large") =>
                      setFormData({ ...formData, buttonSize: value })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="small">Small</SelectItem>
                      <SelectItem value="medium">Medium</SelectItem>
                      <SelectItem value="large">Large</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <div className="flex items-center gap-1">
                    <Label htmlFor="buttonColor">Primary Color</Label>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Info className="h-3.5 w-3.5 text-muted-foreground cursor-help" />
                      </TooltipTrigger>
                      <TooltipContent>
                        <p>Filled: used as button background</p>
                        <p>Outline: used as button border</p>
                      </TooltipContent>
                    </Tooltip>
                  </div>
                  <div className="flex gap-2">
                    <Input
                      id="buttonColor"
                      type="color"
                      value={formData.buttonColor}
                      onChange={(e) => setFormData({ ...formData, buttonColor: e.target.value })}
                      className="w-12 h-10 p-1"
                    />
                    <Input
                      value={formData.buttonColor}
                      onChange={(e) => setFormData({ ...formData, buttonColor: e.target.value })}
                      placeholder="#3b82f6"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="buttonTextColor">Text Color</Label>
                  <div className="flex gap-2">
                    <Input
                      id="buttonTextColor"
                      type="color"
                      value={formData.buttonTextColor}
                      onChange={(e) => setFormData({ ...formData, buttonTextColor: e.target.value })}
                      className="w-12 h-10 p-1"
                    />
                    <Input
                      value={formData.buttonTextColor}
                      onChange={(e) => setFormData({ ...formData, buttonTextColor: e.target.value })}
                      placeholder="#ffffff"
                    />
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="buttonBorderRadius">Border Radius (px)</Label>
                  <Input
                    id="buttonBorderRadius"
                    type="number"
                    min={0}
                    max={50}
                    value={formData.buttonBorderRadius}
                    onChange={(e) =>
                      setFormData({ ...formData, buttonBorderRadius: parseInt(e.target.value) })
                    }
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="buttonPosition">Position</Label>
                  <Select
                    value={formData.buttonPosition}
                    onValueChange={(value: EmbedConfigCreate["buttonPosition"]) =>
                      setFormData({ ...formData, buttonPosition: value })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="bottom-right">Bottom Right</SelectItem>
                      <SelectItem value="bottom-left">Bottom Left</SelectItem>
                      <SelectItem value="bottom-center">Bottom Center</SelectItem>
                      <SelectItem value="top-right">Top Right</SelectItem>
                      <SelectItem value="top-left">Top Left</SelectItem>
                      <SelectItem value="top-center">Top Center</SelectItem>
                      <SelectItem value="center">Center</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <div className="flex items-center gap-1">
                    <Label htmlFor="buttonStyle">Button Style</Label>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Info className="h-3.5 w-3.5 text-muted-foreground cursor-help" />
                      </TooltipTrigger>
                      <TooltipContent>
                        <p><strong>Filled:</strong> Solid color background</p>
                        <p><strong>Outline:</strong> White background with colored border</p>
                      </TooltipContent>
                    </Tooltip>
                  </div>
                  <Select
                    value={formData.buttonStyle}
                    onValueChange={(value: "filled" | "outline") =>
                      setFormData({ ...formData, buttonStyle: value })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="filled">Filled</SelectItem>
                      <SelectItem value="outline">Outline</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>

            {/* Security Settings */}
            <div className="space-y-4">
              <h4 className="font-medium">Security Settings</h4>

              <div className="space-y-2">
                <div className="flex items-center gap-1">
                  <Label htmlFor="allowedDomains">Allowed Domains (optional)</Label>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Info className="h-3.5 w-3.5 text-muted-foreground cursor-help" />
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>Restrict where the button can be used</p>
                      <p>Enter one domain per line</p>
                      <p>Leave empty to allow all domains</p>
                    </TooltipContent>
                  </Tooltip>
                </div>
                <Textarea
                  id="allowedDomains"
                  placeholder="example.com&#10;www.example.com"
                  value={formData.allowedDomains?.join("\n") || ""}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      allowedDomains: e.target.value.split("\n").filter(Boolean),
                    })
                  }
                />
              </div>

              <div className="space-y-2">
                <div className="flex items-center gap-1">
                  <Label htmlFor="dailyCallLimit">Daily Call Limit</Label>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Info className="h-3.5 w-3.5 text-muted-foreground cursor-help" />
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>Maximum number of calls per day</p>
                      <p>from this embed button</p>
                    </TooltipContent>
                  </Tooltip>
                </div>
                <Input
                  id="dailyCallLimit"
                  type="number"
                  min={1}
                  max={10000}
                  value={formData.dailyCallLimit}
                  onChange={(e) =>
                    setFormData({ ...formData, dailyCallLimit: parseInt(e.target.value) })
                  }
                />
              </div>

              <div className="flex items-center space-x-2">
                <Switch
                  id="isActive"
                  checked={formData.isActive}
                  onCheckedChange={(checked) =>
                    setFormData({ ...formData, isActive: checked })
                  }
                />
                <div className="flex items-center gap-1">
                  <Label htmlFor="isActive">Enable Embed</Label>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Info className="h-3.5 w-3.5 text-muted-foreground cursor-help" />
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>When disabled, the embed button</p>
                      <p>will not work on external websites</p>
                    </TooltipContent>
                  </Tooltip>
                </div>
              </div>
            </div>

            {/* Advanced */}
            <div className="space-y-4">
              <h4 className="font-medium">Advanced</h4>

              <div className="space-y-2">
                <div className="flex items-center gap-1">
                  <Label htmlFor="customCss">Custom CSS (optional)</Label>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Info className="h-3.5 w-3.5 text-muted-foreground cursor-help" />
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>Add custom CSS to style the button</p>
                      <p>Use <code className="text-xs">.ai-call-button</code> selector</p>
                    </TooltipContent>
                  </Tooltip>
                </div>
                <Textarea
                  id="customCss"
                  placeholder=".ai-call-button { ... }"
                  value={formData.customCss || ""}
                  onChange={(e) => setFormData({ ...formData, customCss: e.target.value })}
                />
              </div>
            </div>
          </div>
        )}

        <DialogFooter className="gap-2">
          {!effectiveShowCode && config && (
            <>
              <Button
                variant="outline"
                onClick={() => setShowCode(true)}
              >
                <Code className="h-4 w-4 mr-2" />
                View Embed Code
              </Button>
              <Button
                variant="destructive"
                onClick={() => deleteMutation.mutate()}
                disabled={deleteMutation.isPending}
              >
                Delete
              </Button>
            </>
          )}
          {!effectiveShowCode && (
            <Button
              onClick={handleSave}
              disabled={saveMutation.isPending}
            >
              {saveMutation.isPending ? "Saving..." : config ? "Update Configuration" : "Save & Generate Code"}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
