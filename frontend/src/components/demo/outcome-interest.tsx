"use client";

import React, { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { CheckCircle2 } from "lucide-react";
import { leadService } from "@/services/lead-service";
import { TurnstileWidget } from "@/components/auth/turnstile-widget";

const interestSchema = z.object({
  name: z.string().trim().min(1, "Please tell us your name.").max(120),
  email: z.string().trim().email("Please enter a valid email address."),
  businessName: z.string().trim().max(160).optional(),
});

type InterestValues = z.infer<typeof interestSchema>;

/** Demo slug → vertical mapping for lead attribution. */
const SLUG_VERTICALS: Record<string, string> = {
  "pleasant-pediatric-appointments": "dental",
  "copper-ridge-service-request": "hvac",
};

interface OutcomeInterestProps {
  /** Demo agent slug, recorded with the lead for attribution. */
  demoSlug: string;
}

/**
 * Post-demo interest capture on the outcome page.
 *
 * Posts to the private leads funnel (`source=outcome-form`) with the demo
 * slug attached — this is the form fallback the funnel design calls for:
 * visitors who hung up or would not share details with the bot can still
 * convert here, in browser context, with a real email address.
 */
export function OutcomeInterest({ demoSlug }: OutcomeInterestProps) {
  const [submitted, setSubmitted] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [captchaToken, setCaptchaToken] = useState<string | null>(null);

  const form = useForm<InterestValues>({
    resolver: zodResolver(interestSchema),
    defaultValues: { name: "", email: "", businessName: "" },
  });

  async function onSubmit(values: InterestValues) {
    setSubmitError(null);
    const result = await leadService.submitInterestLead({
      name: values.name,
      email: values.email,
      businessName: values.businessName || undefined,
      source: "outcome-form",
      demoSlug,
      vertical: SLUG_VERTICALS[demoSlug],
      captchaToken: captchaToken || undefined,
    });
    if (result.success) {
      setSubmitted(true);
    } else {
      setSubmitError(
        result.error || "Could not send your request. Please try again.",
      );
    }
  }

  if (submitted) {
    return (
      <div className="text-center py-4 space-y-3" data-testid="outcome-interest-success">
        <CheckCircle2 className="w-10 h-10 text-green-500 mx-auto" />
        <p className="font-semibold text-slate-900">Request received</p>
        <p className="text-sm text-slate-600">
          Thanks — we will reach out within one business day to set this up
          for your business.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div>
        <h3 className="font-semibold text-slate-900">
          Want this answering your business calls?
        </h3>
        <p className="mt-1 text-sm text-slate-600">
          Leave your details and we will configure it for you — usually live
          within 48 hours.
        </p>
      </div>
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} noValidate className="space-y-3">
          {submitError && (
            <Alert variant="destructive">
              <AlertDescription>{submitError}</AlertDescription>
            </Alert>
          )}
          <div className="grid gap-3 sm:grid-cols-2">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Your name</FormLabel>
                  <FormControl>
                    <Input placeholder="Jane Smith" autoComplete="name" {...field} />
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
                  <FormLabel>
                    Business{" "}
                    <span className="text-muted-foreground">(optional)</span>
                  </FormLabel>
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
          </div>
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
          <Button
            type="submit"
            className="w-full shadow-lg shadow-primary/15"
            disabled={form.formState.isSubmitting}
          >
            {form.formState.isSubmitting ? "Sending…" : "Get this for my business"}
          </Button>
          <TurnstileWidget
            onVerify={setCaptchaToken}
            onExpire={() => setCaptchaToken(null)}
          />
        </form>
      </Form>
    </div>
  );
}
