"use client";

import React, { useState } from "react";
import Link from "next/link";
import { CheckCircle2 } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { TurnstileWidget } from "@/components/auth/turnstile-widget";
import { PublicFooter } from "@/components/public-theme/public-footer";
import { PublicHeader } from "@/components/public-theme/public-header";
import { PublicThemeRoot } from "@/components/public-theme/public-theme-root";
import { leadService } from "@/services/lead-service";
import { SITE_NAME } from "@/lib/site-config";
import pt from "@/components/public-theme/public-theme.module.css";

const BUSINESS_TYPES = [
  ["dental", "Dental / medical practice"],
  ["hvac", "HVAC / home services"],
  ["plumbing", "Plumbing / emergency home services"],
  ["auto-repair", "Independent auto repair"],
  ["veterinary", "Veterinary clinic"],
  ["restaurant", "Restaurant / hospitality"],
  ["other", "Something else"],
] as const;

/** Public contact form for pricing questions and tailored-plan requests. */
export default function ContactPage() {
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [captchaToken, setCaptchaToken] = useState<string | null>(null);
  const [returnToBilling, setReturnToBilling] = useState("/");

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitError(null);
    setSubmitting(true);
    const values = new FormData(event.currentTarget);
    const result = await leadService.submitInterestLead({
      name: String(values.get("name") ?? "").trim(),
      businessName: String(values.get("businessName") ?? "").trim() || undefined,
      email: String(values.get("email") ?? "").trim(),
      phone: String(values.get("phone") ?? "").trim() || undefined,
      vertical: String(values.get("vertical") ?? "") || undefined,
      message: String(values.get("message") ?? "").trim() || undefined,
      source: "contact-us",
      captchaToken: captchaToken || undefined,
    });
    setSubmitting(false);

    if (result.success) {
      const organizationId = new URLSearchParams(window.location.search).get("org_id");
      if (
        organizationId &&
        /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(
          organizationId,
        )
      ) {
        setReturnToBilling(
          `/organization/billing?org_id=${encodeURIComponent(organizationId)}&tab=plans`,
        );
      }
      setSubmitted(true);
      return;
    }
    setSubmitError(result.error || "Could not send your message. Please try again.");
  }

  return (
    <PublicThemeRoot>
      <div className={pt.page}>
        <PublicHeader />
        <main className="mx-auto w-full max-w-3xl px-5 py-12 sm:py-16">
          <div className="mb-8 space-y-3 text-center">
            <p className="text-sm font-semibold uppercase tracking-wide text-primary">
              Contact {SITE_NAME}
            </p>
            <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
              Talk with our team
            </h1>
            <p className="mx-auto max-w-2xl text-muted-foreground">
              Tell us what you need. Our platform team will follow up about
              pricing, setup, or a plan tailored to your organization.
            </p>
          </div>

          <Card>
            <CardContent className="p-5 sm:p-8">
              {submitted ? (
                <div className="space-y-4 py-8 text-center" data-testid="contact-success">
                  <CheckCircle2 className="mx-auto h-12 w-12 text-green-600" />
                  <h2 className="text-xl font-semibold">Message received</h2>
                  <p className="text-muted-foreground">
                    Thanks for contacting us. Our team will follow up within one
                    business day.
                  </p>
                  <Button asChild variant="outline">
                    <Link href={returnToBilling}>
                      {returnToBilling === "/" ? "Return home" : "Return to billing"}
                    </Link>
                  </Button>
                </div>
              ) : (
                <form onSubmit={onSubmit} className="space-y-5">
                  {submitError ? (
                    <Alert variant="destructive">
                      <AlertDescription>{submitError}</AlertDescription>
                    </Alert>
                  ) : null}

                  <div className="grid gap-5 sm:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="contact-name">Your name</Label>
                      <Input id="contact-name" name="name" autoComplete="name" maxLength={120} required />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="contact-business">Business name</Label>
                      <Input id="contact-business" name="businessName" autoComplete="organization" maxLength={160} />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="contact-email">Work email</Label>
                      <Input id="contact-email" name="email" type="email" autoComplete="email" required />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="contact-phone">Phone number (optional)</Label>
                      <Input id="contact-phone" name="phone" type="tel" autoComplete="tel" maxLength={32} />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="contact-vertical">Business type</Label>
                    <select
                      id="contact-vertical"
                      name="vertical"
                      defaultValue=""
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    >
                      <option value="">Choose one (optional)</option>
                      {BUSINESS_TYPES.map(([value, label]) => (
                        <option key={value} value={value}>{label}</option>
                      ))}
                    </select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="contact-message">How can we help?</Label>
                    <Textarea
                      id="contact-message"
                      name="message"
                      rows={5}
                      maxLength={2000}
                      placeholder="Tell us about your call volume, locations, or the features you need."
                    />
                  </div>

                  <TurnstileWidget
                    onVerify={setCaptchaToken}
                    onExpire={() => setCaptchaToken(null)}
                  />
                  <Button type="submit" className="w-full" disabled={submitting}>
                    {submitting ? "Sending…" : "Send message"}
                  </Button>
                </form>
              )}
            </CardContent>
          </Card>
        </main>
        <PublicFooter />
      </div>
    </PublicThemeRoot>
  );
}
