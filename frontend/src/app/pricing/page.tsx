"use client";

import * as React from "react";
import Link from "next/link";
import { Check, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { PublicThemeRoot } from "@/components/public-theme/public-theme-root";
import { PublicHeader } from "@/components/public-theme/public-header";
import { SiteFooter } from "@/components/public-theme/site-footer";
import { cn } from "@/lib/utils";
import styles from "./pricing.module.css";

interface PlanFeature {
  text: string;
  included: boolean;
}

interface Plan {
  name: string;
  slug: string;
  monthlyPrice: number;
  annualPrice: number;
  description: string;
  features: PlanFeature[];
  highlighted?: boolean;
  ctaText: string;
  ctaHref: string;
}

const plans: Plan[] = [
  {
    name: "Free",
    slug: "free",
    monthlyPrice: 0,
    annualPrice: 0,
    description: "Try the platform with a single agent and limited minutes.",
    features: [
      { text: "1 voice agent", included: true },
      { text: "1 team member", included: true },
      { text: "~10 call minutes/month (100 credits)", included: true },
      { text: "Website embed widget", included: true },
      { text: "Call recordings & transcripts", included: true },
      { text: "Phone number purchase", included: false },
      { text: "Premium integrations", included: false },
      { text: "Custom branding", included: false },
    ],
    ctaText: "Start Free",
    ctaHref: "/auth/signup",
  },
  {
    name: "Starter",
    slug: "starter",
    monthlyPrice: 79,
    annualPrice: 790, // 10 months price for 12 months
    description: "For solo owners and small shops handling a steady flow of calls.",
    features: [
      { text: "Unlimited voice agents", included: true },
      { text: "Unlimited team members", included: true },
      { text: "~250 call minutes/month (2,500 credits)", included: true },
      { text: "1 US local number included", included: true },
      { text: "Additional numbers: 80 credits/month each", included: true },
      { text: "Website embed widget", included: true },
      { text: "Call recordings & transcripts", included: true },
      { text: "Custom branding", included: false },
      { text: "Premium integrations (Gmail, Sheets, HubSpot)", included: false },
    ],
    ctaText: "Get Started",
    ctaHref: "/request-demo",
  },
  {
    name: "Pro",
    slug: "pro",
    monthlyPrice: 149,
    annualPrice: 1490, // 10 months price for 12 months
    description: "For busy teams with higher call volumes and custom branding needs.",
    features: [
      { text: "Unlimited voice agents", included: true },
      { text: "Unlimited team members", included: true },
      { text: "~1,000 call minutes/month (10,000 credits)", included: true },
      { text: "1 US local number included", included: true },
      { text: "Additional numbers: 80 credits/month each", included: true },
      { text: "Website embed widget", included: true },
      { text: "Call recordings & transcripts", included: true },
      { text: "Custom branding", included: true },
      { text: "Premium integrations (Gmail, Sheets, HubSpot)", included: false },
    ],
    highlighted: true,
    ctaText: "Get Started",
    ctaHref: "/request-demo",
  },
  {
    name: "Scale",
    slug: "scale",
    monthlyPrice: 299,
    annualPrice: 2990, // 10 months price for 12 months
    description: "For larger, multi-location teams handling high call volumes.",
    features: [
      { text: "Unlimited voice agents", included: true },
      { text: "Unlimited team members", included: true },
      { text: "~2,100 call minutes/month (21,000 credits)", included: true },
      { text: "1 US local number included", included: true },
      { text: "Additional numbers: 80 credits/month each", included: true },
      { text: "Website embed widget", included: true },
      { text: "Call recordings & transcripts", included: true },
      { text: "Custom branding", included: true },
      { text: "Premium integrations (Gmail, Sheets, HubSpot)", included: true },
    ],
    ctaText: "Get Started",
    ctaHref: "/request-demo",
  },
];

export default function PricingPage() {
  const [billingInterval, setBillingInterval] = React.useState<"monthly" | "annual">("monthly");

  return (
    <PublicThemeRoot>
      <div className={styles.page}>
        <PublicHeader />

        <main className={styles.main}>
          <div className={styles.container}>
            {/* Header */}
            <div className={styles.header}>
              <p className={styles.eyebrow}>SIMPLE, TRANSPARENT PRICING</p>
              <h1 className={styles.title}>
                Plans that scale
                <br />
                <span>with your business.</span>
              </h1>
              <p className={styles.description}>
                All plans include call recording, transcripts, and analytics. Scale up or down
                as your needs change. No hidden fees or surprise charges.
              </p>

              {/* Billing Toggle */}
              <div className={styles.billingToggle}>
                <button
                  type="button"
                  onClick={() => setBillingInterval("monthly")}
                  className={cn(
                    styles.billingButton,
                    billingInterval === "monthly" && styles.active,
                  )}
                >
                  Monthly
                </button>
                <button
                  type="button"
                  onClick={() => setBillingInterval("annual")}
                  className={cn(
                    styles.billingButton,
                    billingInterval === "annual" && styles.active,
                  )}
                >
                  Annual
                  <span className={styles.savingsBadge}>Save 2 months</span>
                </button>
              </div>
            </div>

            {/* Plans Grid */}
            <div className={styles.plansGrid}>
              {plans.map((plan) => {
                const price =
                  plan.slug === "free"
                    ? 0
                    : billingInterval === "monthly"
                      ? plan.monthlyPrice
                      : plan.annualPrice;
                const priceLabel = plan.slug === "free" ? "Forever" : `per ${billingInterval === "monthly" ? "month" : "year"}`;

                return (
                  <Card
                    key={plan.slug}
                    className={cn(
                      styles.planCard,
                      plan.highlighted && styles.highlighted,
                    )}
                  >
                    {plan.highlighted && (
                      <div className={styles.highlightBadge}>Most Popular</div>
                    )}
                    <CardHeader>
                      <CardTitle className={styles.planName}>{plan.name}</CardTitle>
                      <CardDescription className={styles.planDescription}>
                        {plan.description}
                      </CardDescription>
                      <div className={styles.priceContainer}>
                        <div className={styles.price}>
                          <span className={styles.currency}>$</span>
                          <span className={styles.amount}>{price}</span>
                        </div>
                        <div className={styles.priceLabel}>{priceLabel}</div>
                      </div>
                    </CardHeader>

                    <CardContent className={styles.features}>
                      <ul className={styles.featureList}>
                        {plan.features.map((feature, index) => (
                          <li
                            key={index}
                            className={cn(
                              styles.feature,
                              !feature.included && styles.excluded,
                            )}
                          >
                            <Check
                              className={cn(
                                styles.checkIcon,
                                !feature.included && styles.excludedIcon,
                              )}
                            />
                            <span>{feature.text}</span>
                          </li>
                        ))}
                      </ul>
                    </CardContent>

                    <CardFooter>
                      <Button
                        asChild
                        size="lg"
                        variant={plan.highlighted ? "default" : "outline"}
                        className={styles.ctaButton}
                      >
                        <Link href={plan.ctaHref}>
                          {plan.ctaText}
                          <ArrowRight className="ml-2 h-4 w-4" />
                        </Link>
                      </Button>
                    </CardFooter>
                  </Card>
                );
              })}
            </div>

            {/* Additional Info */}
            <div className={styles.additionalInfo}>
              <h2 className={styles.infoHeading}>How credits work</h2>
              <div className={styles.infoGrid}>
                <div className={styles.infoCard}>
                  <h3>Call minutes</h3>
                  <p>
                    10 credits = 1 connected minute. Calls are rounded up to the nearest
                    minute. Minimum 10 credits (1 minute) per call.
                  </p>
                </div>
                <div className={styles.infoCard}>
                  <h3>Phone numbers</h3>
                  <p>
                    US local numbers: 80 credits/month rental. Your first number is included
                    on paid plans. Connect your own Twilio number for free.
                  </p>
                </div>
                <div className={styles.infoCard}>
                  <h3>Top-ups available</h3>
                  <p>
                    Need more minutes? Purchase additional credits that never expire, starting
                    at $5 for 200 credits (20 minutes).
                  </p>
                </div>
              </div>
            </div>

            {/* Agency CTA */}
            <div className={styles.agencyCta}>
              <h2>Need something else?</h2>
              <p>
                Multi-location operations, white-label deployment, or custom volume pricing?
                Let&apos;s talk about an enterprise solution.
              </p>
              <Button asChild size="lg" variant="outline">
                <Link href={`mailto:${process.env.NEXT_PUBLIC_SALES_EMAIL || "sales@247ai.live"}`}>
                  Contact Sales
                </Link>
              </Button>
            </div>
          </div>
        </main>

        <SiteFooter />
      </div>
    </PublicThemeRoot>
  );
}
