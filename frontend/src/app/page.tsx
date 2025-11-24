'use client';

import React from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  CheckCircle2,
  BarChart3,
  Users,
  Shield,
  Zap,
  Globe,
} from 'lucide-react';

export default function LandingPage() {

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col font-sans">
      {/* Header */}
      <header className="sticky top-0 z-50 w-full border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-14 items-center justify-between max-w-6xl mx-auto px-4">
          <div className="flex items-center gap-2">
            <div className="bg-primary w-8 h-8 rounded-lg flex items-center justify-center">
              <span className="text-primary-foreground font-bold text-lg">AI</span>
            </div>
            <span className="text-xl font-bold tracking-tight">NeuraSaaS</span>
          </div>
          <nav className="hidden md:flex gap-6">
            <a href="#features" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
              Features
            </a>
            <a href="#pricing" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
              Pricing
            </a>
            <a href="#about" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
              About
            </a>
          </nav>
          <div className="flex items-center gap-4">
            <Link href="/auth/signin">
              <Button variant="ghost" size="sm">
                Sign In
              </Button>
            </Link>
            <Link href="/auth/signup">
              <Button size="sm">Get Started</Button>
            </Link>
          </div>
        </div>
      </header>

      <main className="flex-1">
        {/* Hero Section */}
        <section className="py-16 md:py-24 bg-gradient-to-b from-background to-secondary/20">
          <div className="container px-4 md:px-6 max-w-6xl mx-auto">
            <div className="grid gap-6 lg:grid-cols-[1fr_400px] lg:gap-12 xl:grid-cols-[1fr_600px]">
              <div className="flex flex-col justify-center space-y-4">
                <div className="space-y-2">
                  <h1 className="text-3xl font-bold tracking-tighter sm:text-5xl xl:text-6xl/none">
                    The Complete SaaS Platform for Your Business
                  </h1>
                  <p className="max-w-[600px] text-muted-foreground md:text-xl">
                    Streamline your workflow, manage your team, and scale your business with our all-in-one solution.
                  </p>
                </div>
                <div className="flex flex-col gap-2 min-[400px]:flex-row">
                  <Link href="/auth/signup">
                    <Button size="lg" className="px-8">
                      Start Free Trial
                    </Button>
                  </Link>
                  <Link href="#features">
                    <Button size="lg" variant="outline" className="px-8">
                      Learn More
                    </Button>
                  </Link>
                </div>
                <div className="flex items-center space-x-4 text-sm text-muted-foreground">
                  <div className="flex items-center">
                    <CheckCircle2 className="mr-1 h-4 w-4 text-primary" />
                    <span>No credit card required</span>
                  </div>
                  <div className="flex items-center">
                    <CheckCircle2 className="mr-1 h-4 w-4 text-primary" />
                    <span>14-day free trial</span>
                  </div>
                </div>
              </div>
              <div className="mx-auto flex w-full max-w-[500px] items-center justify-center lg:max-w-none">
                <div className="relative w-full aspect-video overflow-hidden rounded-xl border border-border bg-background shadow-xl">
                  <div className="absolute inset-0 bg-gradient-to-tr from-primary/10 via-background to-background" />
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="text-center space-y-2">
                      <div className="w-16 h-16 bg-primary/20 rounded-2xl mx-auto flex items-center justify-center mb-4">
                        <Zap className="h-8 w-8 text-primary" />
                      </div>
                      <p className="text-sm font-medium text-muted-foreground">Powerful Dashboard Interface</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Features Section */}
        <section id="features" className="py-16 bg-background">
          <div className="container px-4 md:px-6 max-w-6xl mx-auto">
            <div className="flex flex-col items-center justify-center space-y-4 text-center">
              <div className="space-y-2">
                <div className="inline-block rounded-lg bg-secondary px-3 py-1 text-sm text-secondary-foreground">
                  Key Features
                </div>
                <h2 className="text-3xl font-bold tracking-tighter md:text-4xl">
                  Everything you need to succeed
                </h2>
                <p className="max-w-[900px] text-muted-foreground md:text-xl/relaxed lg:text-base/relaxed xl:text-xl/relaxed">
                  Our platform provides comprehensive tools to help you manage every aspect of your business.
                </p>
              </div>
            </div>
            <div className="mx-auto grid max-w-5xl grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3 mt-12">
              {[
                {
                  title: "Analytics",
                  description: "Get detailed insights into your performance with our advanced analytics dashboard.",
                  icon: BarChart3,
                },
                {
                  title: "Team Management",
                  description: "Easily manage your team, assign roles, and track productivity in one place.",
                  icon: Users,
                },
                {
                  title: "Security",
                  description: "Enterprise-grade security to keep your data safe and compliant with regulations.",
                  icon: Shield,
                },
                {
                  title: "Automation",
                  description: "Automate repetitive tasks and workflows to save time and reduce errors.",
                  icon: Zap,
                },
                {
                  title: "Integrations",
                  description: "Connect with your favorite tools and services seamlessly.",
                  icon: Globe,
                },
                {
                  title: "24/7 Support",
                  description: "Our dedicated support team is available around the clock to assist you.",
                  icon: CheckCircle2,
                },
              ].map((feature, index) => (
                <div key={index} className="flex flex-col items-start space-y-2 rounded-lg border border-border p-5 shadow-sm transition-all hover:shadow-md">
                  <div className="p-2 bg-primary/10 rounded-lg">
                    <feature.icon className="h-5 w-5 text-primary" />
                  </div>
                  <h3 className="text-lg font-bold">{feature.title}</h3>
                  <p className="text-sm text-muted-foreground">{feature.description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Pricing Section */}
        <section id="pricing" className="py-16 bg-secondary/30">
          <div className="container px-4 md:px-6 max-w-6xl mx-auto">
            <div className="flex flex-col items-center justify-center space-y-4 text-center">
              <div className="space-y-2">
                <div className="inline-block rounded-lg bg-background px-3 py-1 text-sm border border-border shadow-sm">
                  Pricing
                </div>
                <h2 className="text-3xl font-bold tracking-tighter md:text-4xl">
                  Simple, transparent pricing
                </h2>
                <p className="max-w-[600px] text-muted-foreground md:text-xl/relaxed lg:text-base/relaxed xl:text-xl/relaxed">
                  Choose the plan that&apos; right for your business. No hidden fees.
                </p>
              </div>
            </div>
            <div className="mx-auto grid max-w-4xl grid-cols-1 gap-6 md:grid-cols-3 mt-12 items-start">
              {[
                {
                  name: "Starter",
                  price: "$29",
                  description: "Perfect for small teams just getting started.",
                  features: ["Up to 5 users", "Basic analytics", "Email support", "1GB storage"],
                  cta: "Get Started",
                  popular: false,
                },
                {
                  name: "Pro",
                  price: "$79",
                  description: "For growing businesses that need more power.",
                  features: ["Up to 20 users", "Advanced analytics", "Priority support", "10GB storage", "API access"],
                  cta: "Start Free Trial",
                  popular: true,
                },
                {
                  name: "Enterprise",
                  price: "Custom",
                  description: "Tailored solutions for large organizations.",
                  features: ["Unlimited users", "Custom reporting", "24/7 dedicated support", "Unlimited storage", "SSO & Audit logs"],
                  cta: "Contact Sales",
                  popular: false,
                },
              ].map((plan, index) => (
                <div
                  key={index}
                  className={`flex flex-col rounded-xl border ${plan.popular
                      ? 'border-primary shadow-lg scale-105 bg-background z-10'
                      : 'border-border bg-background/50 shadow-sm'
                    } p-6`}
                >
                  {plan.popular && (
                    <div className="mb-4 inline-block rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary w-fit">
                      Most Popular
                    </div>
                  )}
                  <h3 className="text-xl font-bold">{plan.name}</h3>
                  <div className="mt-4 flex items-baseline text-3xl font-bold">
                    {plan.price}
                    {plan.price !== "Custom" && <span className="ml-1 text-sm font-medium text-muted-foreground">/mo</span>}
                  </div>
                  <p className="mt-2 text-sm text-muted-foreground">{plan.description}</p>
                  <ul className="mt-6 space-y-3 flex-1">
                    {plan.features.map((feature, i) => (
                      <li key={i} className="flex items-center text-sm">
                        <CheckCircle2 className="mr-2 h-4 w-4 text-primary" />
                        {feature}
                      </li>
                    ))}
                  </ul>
                  <Button
                    className={`mt-8 w-full ${plan.popular ? '' : 'variant-outline'}`}
                    variant={plan.popular ? 'default' : 'outline'}
                  >
                    {plan.cta}
                  </Button>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-border bg-background py-6 md:py-0">
        <div className="container flex flex-col items-center justify-between gap-4 md:h-24 md:flex-row max-w-6xl mx-auto px-4">
          <div className="flex flex-col items-center gap-4 px-8 md:flex-row md:gap-2 md:px-0">
            <div className="bg-primary/10 w-8 h-8 rounded-lg flex items-center justify-center">
              <span className="text-primary font-bold text-lg">AI</span>
            </div>
            <p className="text-center text-sm leading-loose text-muted-foreground md:text-left">
              © 2024 NeuraSaaS Inc. All rights reserved.
            </p>
          </div>
          <div className="flex gap-4">
            <Link href="/terms" className="text-sm font-medium hover:underline underline-offset-4">
              Terms
            </Link>
            <Link href="/privacy" className="text-sm font-medium hover:underline underline-offset-4">
              Privacy
            </Link>
            <Link href="/contact" className="text-sm font-medium hover:underline underline-offset-4">
              Contact
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
