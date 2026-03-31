"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useOrganization } from "@/contexts/organization-context";
import { organizationService } from "@/services/organization-service";
import { voiceTemplateService } from "@/services/voice-template-service";
import { agentService } from "@/services/agent-service";
import { phoneNumberService } from "@/services/phone-number-service";
import type { VoiceTemplate } from "@/types/voice-template";
import type { AvailablePhoneNumber } from "@/types/phone-number";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
  SheetFooter,
} from "@/components/ui/sheet";
import { TestCallModal } from "@/components/agents/test-call-modal";
import { cn } from "@/lib/utils";
import {
  Building2,
  Mic,
  Phone,
  Plug,
  Zap,
  CheckCircle2,
  ChevronRight,
  ChevronLeft,
  Loader2,
  Search,
  Calendar,
  Check,
  Eye,
} from "lucide-react";
import { toast } from "sonner";

const INDUSTRIES = [
  { value: "dental", label: "Dental / Healthcare" },
  { value: "hvac", label: "HVAC / Heating & Cooling" },
  { value: "salon", label: "Salon & Spa" },
  { value: "real_estate", label: "Real Estate" },
  { value: "plumbing", label: "Plumbing" },
  { value: "electrical", label: "Electrical" },
  { value: "landscaping", label: "Landscaping" },
  { value: "cleaning", label: "Cleaning Services" },
  { value: "roofing", label: "Roofing" },
  { value: "other", label: "Other Home Service" },
];

const STEPS = [
  { id: 1, label: "Business", icon: Building2 },
  { id: 2, label: "Template", icon: Mic },
  { id: 3, label: "Phone", icon: Phone },
  { id: 4, label: "Tools", icon: Plug },
  { id: 5, label: "Test", icon: Zap },
];

interface WizardState {
  // Step 1
  businessName: string;
  industry: string;
  location: string;
  businessDescription: string;
  // Step 2
  selectedTemplate: VoiceTemplate | null;
  // Step 3
  purchasedPhoneNumber: string | null;
  // Step 5
  createdAgentId: string | null;
}

function StepIndicator({ currentStep }: { currentStep: number }) {
  return (
    <div className="flex items-center justify-center mb-8">
      {STEPS.map((step, index) => {
        const Icon = step.icon;
        const isCompleted = currentStep > step.id;
        const isCurrent = currentStep === step.id;
        return (
          <React.Fragment key={step.id}>
            <div className="flex flex-col items-center">
              <div
                className={cn(
                  "w-10 h-10 rounded-full flex items-center justify-center text-sm font-medium transition-all",
                  isCompleted
                    ? "bg-blue-600 text-white"
                    : isCurrent
                      ? "bg-blue-600 text-white ring-4 ring-blue-100"
                      : "bg-gray-100 text-gray-400",
                )}
              >
                {isCompleted ? <Check className="w-5 h-5" /> : <Icon className="w-4 h-4" />}
              </div>
              <span
                className={cn(
                  "text-xs mt-1 font-medium",
                  isCurrent ? "text-blue-600" : isCompleted ? "text-gray-600" : "text-gray-400",
                )}
              >
                {step.label}
              </span>
            </div>
            {index < STEPS.length - 1 && (
              <div
                className={cn(
                  "flex-1 h-0.5 mx-2 mb-5 transition-all",
                  currentStep > step.id ? "bg-blue-600" : "bg-gray-200",
                )}
              />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

// Step 1: Business Setup
function Step1Business({
  state,
  onChange,
  onNext,
  saving,
}: {
  state: WizardState;
  onChange: (update: Partial<WizardState>) => void;
  onNext: () => void;
  saving: boolean;
}) {
  const canProceed = state.businessName.trim() && state.industry;

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Tell us about your business</h2>
        <p className="text-gray-500 mt-1">This helps personalize your AI voice agent.</p>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Business Name <span className="text-red-500">*</span>
          </label>
          <Input
            placeholder="e.g. Smith Plumbing Co."
            value={state.businessName}
            onChange={(e) => onChange({ businessName: e.target.value })}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Industry <span className="text-red-500">*</span>
          </label>
          <Select value={state.industry} onValueChange={(v) => onChange({ industry: v })}>
            <SelectTrigger>
              <SelectValue placeholder="Select your industry" />
            </SelectTrigger>
            <SelectContent>
              {INDUSTRIES.map((ind) => (
                <SelectItem key={ind.value} value={ind.value}>
                  {ind.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Location
          </label>
          <Input
            placeholder="e.g. Austin, TX"
            value={state.location}
            onChange={(e) => onChange({ location: e.target.value })}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Brief Business Description
          </label>
          <Textarea
            placeholder="Describe your services, hours, and anything the AI should know about your business..."
            value={state.businessDescription}
            onChange={(e) => onChange({ businessDescription: e.target.value })}
            rows={4}
          />
        </div>
      </div>

      <Button
        onClick={onNext}
        disabled={!canProceed || saving}
        className="w-full"
        size="lg"
      >
        {saving ? (
          <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Saving...</>
        ) : (
          <>Continue <ChevronRight className="w-4 h-4 ml-2" /></>
        )}
      </Button>
    </div>
  );
}

// Step 2: Voice Template
function Step2Template({
  state,
  onChange,
  onNext,
  onBack,
}: {
  state: WizardState;
  onChange: (update: Partial<WizardState>) => void;
  onNext: () => void;
  onBack: () => void;
}) {
  const [templates, setTemplates] = useState<VoiceTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [previewTemplate, setPreviewTemplate] = useState<VoiceTemplate | null>(null);

  useEffect(() => {
    voiceTemplateService
      .listTemplates()
      .then(setTemplates)
      .catch(() => toast.error("Failed to load templates"))
      .finally(() => setLoading(false));
  }, []);

  const industryMatch = templates.filter(
    (t) => t.industry === state.industry,
  );
  const otherTemplates = templates.filter(
    (t) => t.industry !== state.industry,
  );
  const sorted = [...industryMatch, ...otherTemplates];

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Pick a voice template</h2>
        <p className="text-gray-500 mt-1">Choose a pre-built AI persona for your industry.</p>
      </div>

      {loading ? (
        <div className="flex justify-center py-10">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        </div>
      ) : (
        <div className="space-y-3 max-h-80 overflow-y-auto pr-1">
          {sorted.map((template) => {
            const isSelected = state.selectedTemplate?.id === template.id;
            const isMatch = template.industry === state.industry;
            return (
              <div
                key={template.id}
                onClick={() => onChange({ selectedTemplate: template })}
                className={cn(
                  "p-4 border-2 rounded-lg cursor-pointer transition-all",
                  isSelected
                    ? "border-blue-500 bg-blue-50"
                    : "border-gray-200 hover:border-blue-200 hover:bg-gray-50",
                )}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-gray-900">{template.name}</span>
                      {isMatch && (
                        <Badge variant="secondary" className="text-xs bg-blue-100 text-blue-700">
                          Recommended
                        </Badge>
                      )}
                      {isSelected && <CheckCircle2 className="w-5 h-5 text-blue-500 ml-auto" />}
                    </div>
                    <p className="text-sm text-gray-500 mt-0.5">{template.description}</p>
                    {template.tone && (
                      <p className="text-xs text-gray-400 mt-1">Tone: {template.tone}</p>
                    )}
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="ml-2 shrink-0"
                    onClick={(e) => {
                      e.stopPropagation();
                      setPreviewTemplate(template);
                    }}
                  >
                    <Eye className="w-4 h-4 mr-1" /> Preview
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      <Sheet open={!!previewTemplate} onOpenChange={(open) => !open && setPreviewTemplate(null)}>
        <SheetContent className="flex flex-col w-full sm:max-w-md">
          <SheetHeader className="px-6 pt-6 pb-4 border-b">
            <SheetTitle>{previewTemplate?.name}</SheetTitle>
            <SheetDescription>Template preview</SheetDescription>
          </SheetHeader>
          <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
            {previewTemplate?.greeting && (
              <div>
                <span className="text-sm font-medium text-gray-800">Greeting</span>
                <p className="mt-1 text-sm text-gray-600 bg-gray-50 rounded-lg p-3">
                  {previewTemplate.greeting.replace("[Business Name]", state.businessName || "Your Business")}
                </p>
              </div>
            )}
            {previewTemplate?.mission && (
              <div>
                <span className="text-sm font-medium text-gray-800">Mission</span>
                <p className="mt-1 text-sm text-gray-600 bg-gray-50 rounded-lg p-3">{previewTemplate.mission}</p>
              </div>
            )}
            {previewTemplate?.tone && (
              <div>
                <span className="text-sm font-medium text-gray-800">Tone</span>
                <p className="mt-1 text-sm text-gray-600 bg-gray-50 rounded-lg p-3">{previewTemplate.tone}</p>
              </div>
            )}
            {previewTemplate?.persona && (
              <div>
                <span className="text-sm font-medium text-gray-800">Persona</span>
                <p className="mt-1 text-sm text-gray-600 bg-gray-50 rounded-lg p-3">{previewTemplate.persona}</p>
              </div>
            )}
            {previewTemplate?.custom_instructions && (
              <div>
                <span className="text-sm font-medium text-gray-800">Custom Instructions</span>
                <p className="mt-1 text-sm text-gray-600 bg-gray-50 rounded-lg p-3 whitespace-pre-line">{previewTemplate.custom_instructions}</p>
              </div>
            )}
          </div>
          <SheetFooter className="px-6 py-4 border-t gap-2">
            <Button variant="outline" onClick={() => setPreviewTemplate(null)}>
              Close
            </Button>
            <Button
              onClick={() => {
                if (previewTemplate) onChange({ selectedTemplate: previewTemplate });
                setPreviewTemplate(null);
              }}
            >
              Select this template
            </Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>

      <div className="flex gap-3">
        <Button variant="outline" onClick={onBack} className="w-32">
          <ChevronLeft className="w-4 h-4 mr-1" /> Back
        </Button>
        <Button
          onClick={onNext}
          disabled={!state.selectedTemplate}
          className="flex-1"
          size="lg"
        >
          Continue <ChevronRight className="w-4 h-4 ml-2" />
        </Button>
      </div>
      {!state.selectedTemplate && (
        <div className="text-center">
          <Button variant="ghost" size="sm" onClick={onNext} className="text-gray-400 hover:text-gray-600">
            <ChevronRight className="w-4 h-4 mr-1" /> Skip template selection
          </Button>
        </div>
      )}
    </div>
  );
}

// Step 3: Phone Number
function Step3Phone({
  state,
  orgId,
  onChange,
  onNext,
  onBack,
}: {
  state: WizardState;
  orgId: string;
  onChange: (update: Partial<WizardState>) => void;
  onNext: () => void;
  onBack: () => void;
}) {
  const [searching, setSearching] = useState(false);
  const [areaCode, setAreaCode] = useState("");
  const [results, setResults] = useState<AvailablePhoneNumber[]>([]);
  const [purchasing, setPurchasing] = useState(false);
  const [selectedNumber, setSelectedNumber] = useState<AvailablePhoneNumber | null>(null);

  const handleSearch = async () => {
    setSearching(true);
    try {
      const response = await phoneNumberService.searchAvailable({
        country_code: "US",
        phone_number_type: "local",
        area_code: areaCode || undefined,
        page_size: 5,
      });
      setResults(response.items);
    } catch {
      toast.error("Failed to search phone numbers");
    } finally {
      setSearching(false);
    }
  };

  const handlePurchase = async () => {
    if (!selectedNumber) return;
    setPurchasing(true);
    try {
      await phoneNumberService.purchaseNumber(orgId, {
        phone_number: selectedNumber.phone_number,
        country_code: selectedNumber.country_code,
        phone_number_type: selectedNumber.phone_number_type,
      });
      onChange({ purchasedPhoneNumber: selectedNumber.phone_number });
      toast.success(`Purchased ${selectedNumber.phone_number}`);
      onNext();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Purchase failed");
    } finally {
      setPurchasing(false);
    }
  };

  if (state.purchasedPhoneNumber) {
    return (
      <div className="space-y-5">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Phone number ready</h2>
        </div>
        <div className="p-4 bg-green-50 border border-green-200 rounded-lg flex items-center gap-3">
          <CheckCircle2 className="w-6 h-6 text-green-600" />
          <div>
            <p className="font-semibold text-green-800">{state.purchasedPhoneNumber}</p>
            <p className="text-sm text-green-600">Your phone number is ready</p>
          </div>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" onClick={onBack} className="w-32">
            <ChevronLeft className="w-4 h-4 mr-1" /> Back
          </Button>
          <Button onClick={onNext} className="flex-1" size="lg">
            Continue <ChevronRight className="w-4 h-4 ml-2" />
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Get a phone number</h2>
        <p className="text-gray-500 mt-1">
          Your AI agent needs a phone number to receive calls. Search for one below, or skip for now.
        </p>
      </div>

      <div className="flex gap-2">
        <Input
          placeholder="Area code (optional)"
          value={areaCode}
          onChange={(e) => setAreaCode(e.target.value)}
          className="w-40"
          maxLength={3}
        />
        <Button onClick={handleSearch} disabled={searching} variant="outline">
          {searching ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4 mr-1" />}
          Search
        </Button>
      </div>

      {results.length > 0 && (
        <div className="space-y-2">
          {results.map((num) => (
            <div
              key={num.phone_number}
              onClick={() => setSelectedNumber(num)}
              className={cn(
                "p-3 border-2 rounded-lg cursor-pointer flex items-center justify-between",
                selectedNumber?.phone_number === num.phone_number
                  ? "border-blue-500 bg-blue-50"
                  : "border-gray-200 hover:border-blue-200",
              )}
            >
              <div>
                <p className="font-medium">{num.phone_number}</p>
                <p className="text-xs text-gray-500">
                  {num.locality ?? num.area_code} · {num.phone_number_type}
                </p>
              </div>
              {selectedNumber?.phone_number === num.phone_number && (
                <CheckCircle2 className="w-5 h-5 text-blue-500" />
              )}
            </div>
          ))}

          {selectedNumber && (
            <Button
              onClick={handlePurchase}
              disabled={purchasing}
              className="w-full mt-2"
            >
              {purchasing ? (
                <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Purchasing...</>
              ) : (
                <>Purchase {selectedNumber.phone_number}</>
              )}
            </Button>
          )}
        </div>
      )}

      <div className="flex gap-3 pt-2">
        <Button variant="outline" onClick={onBack} className="w-32">
          <ChevronLeft className="w-4 h-4 mr-1" /> Back
        </Button>
        <Button variant="outline" onClick={onNext} className="flex-1">
          <ChevronRight className="w-4 h-4 mr-2" /> Skip for now
        </Button>
      </div>
    </div>
  );
}

// Step 4: Connect Tools
function Step4Tools({
  onNext,
  onBack,
}: {
  onNext: () => void;
  onBack: () => void;
}) {
  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Tools (optional)</h2>
        <p className="text-gray-500 mt-1">
          Your agent can connect to tools like Google Calendar to book appointments. You can set these up after completing onboarding.
        </p>
      </div>

      <div className="p-4 border-2 border-gray-200 rounded-lg flex items-center gap-4">
        <div className="w-12 h-12 bg-blue-50 rounded-lg flex items-center justify-center">
          <Calendar className="w-6 h-6 text-blue-600" />
        </div>
        <div className="flex-1">
          <p className="font-semibold text-gray-900">Google Calendar</p>
          <p className="text-sm text-gray-500">Let your agent book appointments in real time</p>
        </div>
      </div>

      <Alert>
        <AlertDescription className="text-sm">
          You can connect tools anytime from the <strong>Settings → Tools</strong> page after completing setup.
        </AlertDescription>
      </Alert>

      <div className="flex gap-3">
        <Button variant="outline" onClick={onBack} className="w-32">
          <ChevronLeft className="w-4 h-4 mr-1" /> Back
        </Button>
        <Button onClick={onNext} className="flex-1" size="lg">
          Continue <ChevronRight className="w-4 h-4 ml-2" />
        </Button>
      </div>
    </div>
  );
}

// Step 5: Test Your Agent
function Step5Test({
  state,
  orgId,
  onChange,
  onComplete,
  onBack,
}: {
  state: WizardState;
  orgId: string;
  onChange: (update: Partial<WizardState>) => void;
  onComplete: () => void;
  onBack: () => void;
}) {
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [agentId, setAgentId] = useState<string | null>(state.createdAgentId);
  const [testCallOpen, setTestCallOpen] = useState(false);
  const [completing, setCompleting] = useState(false);

  // Auto-create the agent when the user arrives at step 5
  useEffect(() => {
    if (agentId || creating || !state.selectedTemplate) return;

    const createAgent = async () => {
      setCreating(true);
      setCreateError(null);
      try {
        const template = state.selectedTemplate!;
        const agentName = `${state.businessName} AI Agent`;
        const greeting = template.greeting?.replace("[Business Name]", state.businessName) ?? undefined;
        const businessContext = state.businessDescription
          ? `Business: ${state.businessName}\nLocation: ${state.location}\n\n${state.businessDescription}`
          : `Business: ${state.businessName}\nLocation: ${state.location}`;

        const agent = await agentService.createAgent({
          organization_id: orgId,
          name: agentName,
          phone_number: state.purchasedPhoneNumber ?? undefined,
          persona: template.persona ?? undefined,
          tone: template.tone ?? undefined,
          mission: template.mission ?? undefined,
          custom_instructions: [
            template.custom_instructions,
            greeting ? `Default greeting: ${greeting}` : null,
            businessContext,
          ]
            .filter(Boolean)
            .join("\n\n") || undefined,
          is_active: true,
        });

        setAgentId(agent.id);
        onChange({ createdAgentId: agent.id });
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Failed to create agent";
        setCreateError(msg);
        toast.error(msg);
      } finally {
        setCreating(false);
      }
    };

    createAgent();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleFinish = async () => {
    setCompleting(true);
    try {
      await organizationService.completeOnboarding(orgId);
      onComplete();
    } catch {
      toast.error("Failed to save progress, but your setup is complete.");
      onComplete();
    } finally {
      setCompleting(false);
    }
  };

  const isReady = !!agentId;

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">
          {creating ? "Almost done — setting up your agent" : isReady ? "Your agent is ready!" : "Test your AI agent"}
        </h2>
        <p className="text-gray-500 mt-1">
          {creating
            ? "Creating your AI agent, this will only take a moment..."
            : isReady
              ? "Make a quick test call from your browser to hear it in action."
              : createError
                ? "There was an issue creating your agent. You can retry or continue to your dashboard."
                : "Your agent will be set up automatically."}
        </p>
      </div>

      <div className="p-6 bg-blue-50 border border-blue-200 rounded-xl text-center space-y-4">
        <div className="w-16 h-16 bg-blue-600 rounded-full flex items-center justify-center mx-auto">
          {creating ? (
            <Loader2 className="w-8 h-8 text-white animate-spin" />
          ) : (
            <Mic className="w-8 h-8 text-white" />
          )}
        </div>
        <div>
          <p className="font-semibold text-gray-900 text-lg">
            {state.selectedTemplate?.name ?? "Your AI Agent"}
          </p>
          <p className="text-sm text-gray-500">
            {state.selectedTemplate ? `${state.businessName} · ${state.selectedTemplate.industry}` : state.businessName}
          </p>
        </div>
        {isReady && (
          <Button
            onClick={() => setTestCallOpen(true)}
            size="lg"
            className="px-8"
          >
            <Phone className="w-4 h-4 mr-2" /> Start test call
          </Button>
        )}
        {creating && (
          <p className="text-sm text-blue-600">Setting up your agent...</p>
        )}
      </div>

      {isReady && (
        <Alert className="border-green-200 bg-green-50">
          <CheckCircle2 className="w-4 h-4 text-green-600" />
          <AlertDescription className="text-green-700 ml-2">
            Agent created successfully! You can test call it or proceed to your dashboard.
            {!state.purchasedPhoneNumber && (
              <span className="block mt-1 text-xs text-green-600">
                Note: no phone number configured — inbound calls will not work until you add one from Settings.
              </span>
            )}
          </AlertDescription>
        </Alert>
      )}

      {createError && (
        <Alert className="border-red-200 bg-red-50">
          <AlertDescription className="text-red-700 ml-2">
            {createError} — you can still continue to your dashboard and set up your agent there.
          </AlertDescription>
        </Alert>
      )}

      <div className="flex gap-3">
        <Button variant="outline" onClick={onBack} className="w-32" disabled={completing || creating}>
          <ChevronLeft className="w-4 h-4 mr-1" /> Back
        </Button>
        <Button onClick={handleFinish} className="flex-1" size="lg" disabled={completing || creating}>
          {completing ? (
            <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Finishing...</>
          ) : (
            <><CheckCircle2 className="w-4 h-4 mr-2" /> Go to Dashboard</>
          )}
        </Button>
      </div>

      {agentId && (
        <TestCallModal
          open={testCallOpen}
          onOpenChange={setTestCallOpen}
          agentId={agentId}
          agentName={state.selectedTemplate?.name ?? "AI Agent"}
        />
      )}
    </div>
  );
}

export default function OnboardingPage() {
  const router = useRouter();
  const { currentOrganization, setCurrentOrganization, refreshOrganizations } = useOrganization();
  const [step, setStep] = useState(1);
  const [saving, setSaving] = useState(false);
  const [wizardState, setWizardState] = useState<WizardState>({
    businessName: currentOrganization?.name ?? "",
    industry: currentOrganization?.industry ?? "",
    location: currentOrganization?.location ?? "",
    businessDescription: "",
    selectedTemplate: null,
    purchasedPhoneNumber: null,
    createdAgentId: null,
  });

  // Redirect if already onboarded (but not during first load)
  useEffect(() => {
    if (currentOrganization?.onboarding_completed) {
      router.replace("/dashboard");
    }
  }, [currentOrganization?.onboarding_completed, router]);

  // Sync business name if org loads after initial render
  useEffect(() => {
    // Only sync if businessName hasn't been set by user yet
    if (currentOrganization) {
      setWizardState((s) => ({
        ...s,
        businessName: s.businessName || currentOrganization.name,
        industry: s.industry || (currentOrganization.industry ?? ""),
        location: s.location || (currentOrganization.location ?? ""),
      }));
    }
  }, [currentOrganization]);

  const updateState = (update: Partial<WizardState>) =>
    setWizardState((s) => ({ ...s, ...update }));

  const handleStep1Next = async () => {
    if (!currentOrganization) return;
    setSaving(true);
    try {
      await organizationService.updateOrganization(currentOrganization.id, {
        name: wizardState.businessName,
        industry: wizardState.industry,
        location: wizardState.location || null,
        business_details: wizardState.businessDescription || null,
      });
      await refreshOrganizations();
      setStep(2);
    } catch {
      toast.error("Failed to save business details");
    } finally {
      setSaving(false);
    }
  };

  const handleComplete = () => {
    // Synchronously mark onboarding complete in context before navigating
    // so the OrganizationCheck guard sees the updated state immediately
    if (currentOrganization) {
      setCurrentOrganization({ ...currentOrganization, onboarding_completed: true });
    }
    router.replace("/dashboard");
  };

  if (!currentOrganization) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-4">
      {/* Header */}
      <div className="text-center mb-8">
        <div className="flex items-center justify-center gap-2 mb-2">
          <div className="bg-gradient-to-br from-blue-600 to-cyan-600 w-10 h-10 rounded-xl flex items-center justify-center">
            <Phone className="w-5 h-5 text-white" />
          </div>
          <span className="text-xl font-bold">VoiceAI</span>
        </div>
        <h1 className="text-3xl font-bold text-gray-900">Welcome! Let&apos;s get you set up</h1>
        <p className="text-gray-500 mt-1">
          You&apos;re {Math.round(((step - 1) / 5) * 100)}% complete · Step {step} of 5
        </p>
      </div>

      {/* Wizard card */}
      <div className="w-full max-w-lg bg-white rounded-2xl shadow-xl p-8">
        <StepIndicator currentStep={step} />

        {step === 1 && (
          <Step1Business
            state={wizardState}
            onChange={updateState}
            onNext={handleStep1Next}
            saving={saving}
          />
        )}
        {step === 2 && (
          <Step2Template
            state={wizardState}
            onChange={updateState}
            onNext={() => setStep(3)}
            onBack={() => setStep(1)}
          />
        )}
        {step === 3 && (
          <Step3Phone
            state={wizardState}
            orgId={currentOrganization.id}
            onChange={updateState}
            onNext={() => setStep(4)}
            onBack={() => setStep(2)}
          />
        )}
        {step === 4 && (
          <Step4Tools
            onNext={() => setStep(5)}
            onBack={() => setStep(3)}
          />
        )}
        {step === 5 && (
          <Step5Test
            state={wizardState}
            orgId={currentOrganization.id}
            onChange={updateState}
            onComplete={handleComplete}
            onBack={() => setStep(4)}
          />
        )}
      </div>

      <p className="text-xs text-gray-400 mt-6">
        You can always update these settings later from your dashboard.
      </p>
    </div>
  );
}
