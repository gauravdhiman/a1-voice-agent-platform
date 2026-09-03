"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { CheckCircle2, Phone } from "lucide-react";
import { SITE_NAME } from "@/lib/site-config";
import { leadService } from "@/services/lead-service";
import { TurnstileWidget } from "@/components/auth/turnstile-widget";

const requestDemoSchema = z.object({
  name: z.string().trim().min(1, "Please tell us your name.").max(120),
  businessName: z.string().trim().max(160).optional(),
  email: z.string().trim().email("Please enter a valid email address."),
  phone: z.string().trim().max(32).optional(),
  vertical: z.string().optional(),
  message: z.string().trim().max(2000).optional(),
});

type RequestDemoValues = z.infer<typeof requestDemoSchema>;

const VERTICALS = [
  { value: "dental", label: "Dental / medical practice" },
  { value: "hvac", label: "HVAC / home services" },
  { value: "restaurant", label: "Restaurant / hospitality" },
  { value: "other", label: "Something else" },
];

/**
 * Public interest form — the front door of the controlled-SaaS funnel.
 *
 * Unauthenticated visitors describe their business; the backend stores the
 * submission privately and the founder follows up with a concierge invite.
 * Never reveals whether an email already exists (fixed success copy).
 */
export default function RequestDemoPage() {
  const [submitted, setSubmitted] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [captchaToken, setCaptchaToken] = useState<string | null>(null);

  const form = useForm<RequestDemoValues>({
    resolver: zodResolver(requestDemoSchema),
    defaultValues: {
      name: "",
      businessName: "",
      email: "",
      phone: "",
      vertical: "",
      message: "",
    },
  });

  async function onSubmit(values: RequestDemoValues) {
    setSubmitError(null);
    const result = await leadService.submitInterestLead({
      name: values.name,
      businessName: values.businessName || undefined,
      email: values.email,
      phone: values.phone || undefined,
      vertical: values.vertical || undefined,
      message: values.message || undefined,
      source: "request-demo",
      captchaToken: captchaToken || undefined,
    });
    if (result.success) {
      const { trackEvent } = await import("@/lib/analytics/posthog");
      trackEvent("interest_submitted", {
        source: "request-demo",
        ...(values.vertical ? { vertical: values.vertical } : {}),
      });
      setSubmitted(true);
    } else {
      setSubmitError(
        result.error || "Could not send your request. Please try again.",
      );
    }
  }

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col font-sans">
      <header className="w-full border-b border-border/40">
        <div className="container flex h-16 items-center max-w-3xl mx-auto px-4">
          <Link href="/" className="flex items-center gap-3">
            <div className="bg-gradient-to-br from-blue-600 to-cyan-600 w-10 h-10 rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/20">
              <Phone className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-bold tracking-tight">{SITE_NAME}</span>
          </Link>
        </div>
      </header>

      <main className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-xl space-y-6">
          <div className="text-center">
            <h1 className="text-3xl font-bold tracking-tight">
              Request a demo
            </h1>
            <p className="text-muted-foreground mt-2">
              Tell us about your business. We will set up your AI front desk
              with you — usually live within 48 hours.
            </p>
          </div>

          <Card>
            <CardContent className="pt-6">
              {submitted ? (
                <div
                  className="text-center py-8 space-y-4"
                  data-testid="request-demo-success"
                >
                  <CheckCircle2 className="w-12 h-12 text-green-500 mx-auto" />
                  <h2 className="text-xl font-semibold">Request received</h2>
                  <p className="text-muted-foreground">
                    Thanks — we will reach out within one business day to
                    schedule your setup call.
                  </p>
                </div>
              ) : (
                <Form {...form}>
                  <form
                    onSubmit={form.handleSubmit(onSubmit)}
                    noValidate
                    className="space-y-4"
                  >
                    {submitError && (
                      <Alert variant="destructive">
                        <AlertDescription>{submitError}</AlertDescription>
                      </Alert>
                    )}
                    <FormField
                      control={form.control}
                      name="name"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Your name</FormLabel>
                          <FormControl>
                            <Input
                              placeholder="Jane Smith"
                              autoComplete="name"
                              {...field}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="businessName"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Business name</FormLabel>
                          <FormControl>
                            <Input
                              placeholder="Bright Smiles Dental"
                              autoComplete="organization"
                              {...field}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <div className="grid gap-4 sm:grid-cols-2">
                      <FormField
                        control={form.control}
                        name="email"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>Work email</FormLabel>
                            <FormControl>
                              <Input
                                type="email"
                                placeholder="you@business.com"
                                autoComplete="email"
                                {...field}
                              />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                      <FormField
                        control={form.control}
                        name="phone"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>
                              Callback number{" "}
                              <span className="text-muted-foreground">
                                (optional)
                              </span>
                            </FormLabel>
                            <FormControl>
                              <Input
                                type="tel"
                                placeholder="(480) 555-0100"
                                autoComplete="tel"
                                {...field}
                              />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                    </div>
                    <FormField
                      control={form.control}
                      name="vertical"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>What kind of business?</FormLabel>
                          <Select
                            onValueChange={field.onChange}
                            defaultValue={field.value}
                          >
                            <FormControl>
                              <SelectTrigger>
                                <SelectValue placeholder="Choose one" />
                              </SelectTrigger>
                            </FormControl>
                            <SelectContent>
                              {VERTICALS.map((option) => (
                                <SelectItem
                                  key={option.value}
                                  value={option.value}
                                >
                                  {option.label}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="message"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>
                            What should the AI handle?{" "}
                            <span className="text-muted-foreground">
                              (optional)
                            </span>
                          </FormLabel>
                          <FormControl>
                            <Textarea
                              placeholder="After-hours calls, appointment booking, missed-call follow-up…"
                              rows={3}
                              {...field}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <Button
                      type="submit"
                      className="w-full bg-blue-600 hover:bg-blue-700 h-12 text-base"
                      disabled={form.formState.isSubmitting}
                    >
                      {form.formState.isSubmitting
                        ? "Sending…"
                        : "Request my demo"}
                    </Button>
                    <TurnstileWidget
                      onVerify={setCaptchaToken}
                      onExpire={() => setCaptchaToken(null)}
                    />
                  </form>
                </Form>
              )}
            </CardContent>
          </Card>

          <p className="text-center text-sm text-muted-foreground">
            Already invited?{" "}
            <Link
              href="/auth/signin"
              className="font-medium text-primary hover:underline underline-offset-4"
            >
              Sign in
            </Link>
          </p>
        </div>
      </main>
    </div>
  );
}
