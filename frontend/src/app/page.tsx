"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  CheckCircle2,
  Phone,
  Mic,
  Shield,
  Zap,
  Globe,
  CreditCard,
  Users,
  BarChart3,
  Calendar,
  Mail,
  Table,
  Workflow,
  Cloud,
  Key,
  Settings,
  MessageSquare,
  ArrowRight,
  Play,
  Star,
  Building2,
  Headphones,
  Bot,
  Rocket,
  Plug,
  Clock,
  PhoneCall,
} from "lucide-react";

// Client-side only waveform to avoid hydration mismatch
function WaveformVisual() {
  const [heights, setHeights] = useState<number[]>([]);

  useEffect(() => {
    // Generate random heights only on client side after hydration
    setHeights(Array.from({ length: 12 }, () => Math.random() * 40 + 10));
  }, []);

  return (
    <>
      {heights.map((height, i) => (
        <div
          key={i}
          className="w-1 bg-blue-500 rounded-full animate-pulse"
          style={{
            height: `${height}px`,
            animationDelay: `${i * 0.1}s`,
          }}
        />
      ))}
    </>
  );
}

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col font-sans">
      {/* Header */}
      <header className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/80 backdrop-blur-md supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-16 items-center justify-between max-w-7xl mx-auto px-4">
          <div className="flex items-center gap-3">
            <div className="bg-gradient-to-br from-blue-600 to-cyan-600 w-10 h-10 rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/20">
              <Phone className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-bold tracking-tight">VoiceAI</span>
          </div>
          <nav className="hidden md:flex gap-8">
            <a
              href="#features"
              className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
            >
              Features
            </a>
            <a
              href="#how-it-works"
              className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
            >
              How It Works
            </a>
            <a
              href="#pricing"
              className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
            >
              Pricing
            </a>
          </nav>
          <div className="flex items-center gap-3">
            <Link href="/auth/signin">
              <Button variant="ghost" size="sm">
                Sign In
              </Button>
            </Link>
            <Link href="/auth/signup">
              <Button size="sm" className="bg-blue-600 hover:bg-blue-700">
                Get Started Free
              </Button>
            </Link>
          </div>
        </div>
      </header>

      <main className="flex-1">
        {/* Hero Section */}
        <section className="relative overflow-hidden py-20 md:py-32">
          {/* Background Pattern */}
          <div className="absolute inset-0 -z-10">
            <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-blue-100 via-background to-background dark:from-blue-950/30" />
            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[500px] bg-blue-500/10 rounded-full blur-3xl" />
            <div className="absolute bottom-0 right-0 w-[600px] h-[400px] bg-cyan-500/10 rounded-full blur-3xl" />
          </div>

          <div className="container px-4 md:px-6 max-w-7xl mx-auto">
            <div className="grid gap-12 lg:grid-cols-2 lg:gap-16 items-center">
              <div className="flex flex-col justify-center space-y-8">
                <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-blue-100 dark:bg-blue-950/50 text-blue-700 dark:text-blue-300 text-sm font-medium w-fit">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
                  </span>
                  No Coding Required
                </div>

                <div className="space-y-4">
                  <h1 className="text-4xl font-bold tracking-tighter sm:text-5xl xl:text-6xl/none">
                    AI Voice Agents for{" "}
                    <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-cyan-600">
                      Every Business
                    </span>
                  </h1>
                  <p className="max-w-[540px] text-muted-foreground md:text-xl leading-relaxed">
                    Set up intelligent voice agents in minutes — no technical
                    skills needed. Let AI handle your calls 24/7, so your team
                    can focus on what matters most.
                  </p>
                </div>

                <div className="flex flex-col gap-3 sm:flex-row">
                  <Link href="/auth/signup">
                    <Button
                      size="lg"
                      className="bg-blue-600 hover:bg-blue-700 px-8 h-12 text-base"
                    >
                      Start Free Trial
                      <ArrowRight className="ml-2 w-4 h-4" />
                    </Button>
                  </Link>
                  <Button
                    size="lg"
                    variant="outline"
                    className="px-8 h-12 text-base"
                  >
                    <Play className="mr-2 w-4 h-4" />
                    See How It Works
                  </Button>
                </div>

                <div className="flex items-center gap-6 text-sm text-muted-foreground">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-green-500" />
                    <span>Set up in 5 minutes</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-green-500" />
                    <span>No credit card</span>
                  </div>
                </div>
              </div>

              {/* Hero Visual */}
              <div className="relative mx-auto w-full max-w-[560px] lg:max-w-none">
                <div className="relative aspect-square max-w-[500px] mx-auto">
                  {/* Animated Phone Mockup */}
                  <div className="absolute inset-0 bg-gradient-to-br from-blue-600 to-cyan-600 rounded-3xl rotate-6 opacity-20" />
                  <div className="absolute inset-0 bg-background rounded-3xl border border-border shadow-2xl overflow-hidden">
                    {/* Fake UI */}
                    <div className="h-14 bg-muted/50 border-b flex items-center justify-center">
                      <div className="w-20 h-4 bg-muted rounded-full" />
                    </div>
                    <div className="p-4 space-y-3">
                      {/* Agent Card */}
                      <div className="p-4 rounded-xl bg-gradient-to-r from-blue-100 to-cyan-100 dark:from-blue-950/50 dark:to-cyan-950/50 border border-blue-200 dark:border-blue-800">
                        <div className="flex items-center gap-3">
                          <div className="w-12 h-12 rounded-full bg-blue-600 flex items-center justify-center">
                            <Bot className="w-6 h-6 text-white" />
                          </div>
                          <div className="flex-1">
                            <div className="h-4 w-24 bg-blue-200 dark:bg-blue-700 rounded mb-2" />
                            <div className="h-3 w-16 bg-muted rounded" />
                          </div>
                          <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse" />
                        </div>
                      </div>
                      {/* Call Waveform */}
                      <div className="h-24 rounded-xl bg-muted/50 flex items-center justify-center gap-1">
                        <WaveformVisual />
                      </div>
                      {/* Message */}
                      <div className="p-3 rounded-lg bg-green-100 dark:bg-green-950/50 border border-green-200 dark:border-green-800">
                        <div className="flex items-start gap-2">
                          <MessageSquare className="w-4 h-4 text-green-600 mt-0.5" />
                          <div className="h-3 w-48 bg-green-200 dark:bg-green-800 rounded" />
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Trusted By / Social Proof */}
        <section className="py-12 border-y border-border/40">
          <div className="container px-4 max-w-7xl mx-auto">
            <p className="text-center text-sm text-muted-foreground mb-8">
              Trusted by businesses of all sizes
            </p>
            <div className="flex flex-wrap items-center justify-center gap-8 md:gap-16 opacity-60">
              <div className="flex items-center gap-2 text-lg font-semibold">
                <Building2 className="w-6 h-6" />
                <span>Acme Corp</span>
              </div>
              <div className="flex items-center gap-2 text-lg font-semibold">
                <Building2 className="w-6 h-6" />
                <span>TechStart</span>
              </div>
              <div className="flex items-center gap-2 text-lg font-semibold">
                <Building2 className="w-6 h-6" />
                <span>GlobalTech</span>
              </div>
              <div className="flex items-center gap-2 text-lg font-semibold">
                <Building2 className="w-6 h-6" />
                <span>DataFlow</span>
              </div>
            </div>
          </div>
        </section>

        {/* Features Section */}
        <section id="features" className="py-20 md:py-28">
          <div className="container px-4 md:px-6 max-w-7xl mx-auto">
            <div className="flex flex-col items-center justify-center space-y-4 text-center mb-16">
              <div className="inline-flex items-center rounded-full bg-blue-100 dark:bg-blue-950/50 px-4 py-1.5 text-sm font-medium text-blue-700 dark:text-blue-300">
                Features
              </div>
              <h2 className="text-3xl font-bold tracking-tighter md:text-4xl lg:text-5xl">
                Everything you need to automate calls
              </h2>
              <p className="max-w-[700px] text-muted-foreground md:text-xl leading-relaxed">
                Powerful yet simple. Our platform handles all the technical
                complexity so you can focus on your business.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {[
                {
                  title: "Works 24/7",
                  description:
                    "Never miss a call again. Your AI agent answers instantly, day or night, weekends and holidays.",
                  icon: Clock,
                  gradient: "from-blue-500 to-cyan-500",
                },
                {
                  title: "Natural Conversations",
                  description:
                    "AI that sounds human. Uses advanced technology to understand context and respond naturally.",
                  icon: Bot,
                  gradient: "from-blue-500 to-cyan-500",
                },
                {
                  title: "Connects to Your Tools",
                  description:
                    "Works with Gmail, Calendar, and more. Your agent can actually do things — not just talk.",
                  icon: Plug,
                  gradient: "from-orange-500 to-amber-500",
                },
                {
                  title: "Secure & Private",
                  description:
                    "Enterprise-grade security. Your customer data is protected and never shared.",
                  icon: Shield,
                  gradient: "from-green-500 to-emerald-500",
                },
                {
                  title: "Easy Dashboard",
                  description:
                    "Simple web interface. Manage agents, see call history, and track results — no tech skills needed.",
                  icon: BarChart3,
                  gradient: "from-pink-500 to-rose-500",
                },
                {
                  title: "Grows With You",
                  description:
                    "Start small, scale anytime. Add more agents or minutes as your business grows.",
                  icon: Rocket,
                  gradient: "from-indigo-500 to-blue-500",
                },
              ].map((feature, index) => (
                <div
                  key={index}
                  className="group relative p-6 rounded-2xl border border-border/60 bg-background/50 backdrop-blur-sm transition-all hover:border-blue-500/30 hover:shadow-xl hover:shadow-blue-500/5"
                >
                  <div
                    className={`w-12 h-12 rounded-xl bg-gradient-to-br ${feature.gradient} flex items-center justify-center mb-4 shadow-lg`}
                  >
                    <feature.icon className="w-6 h-6 text-white" />
                  </div>
                  <h3 className="text-lg font-bold mb-2">{feature.title}</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {feature.description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Tools Section */}
        <section className="py-20 md:py-28 bg-gradient-to-b from-background to-blue-50/50 dark:to-blue-950/20">
          <div className="container px-4 md:px-6 max-w-7xl mx-auto">
            <div className="grid gap-12 lg:grid-cols-2 items-center">
              <div>
                <div className="inline-flex items-center rounded-full bg-blue-100 dark:bg-blue-950/50 px-4 py-1.5 text-sm font-medium text-blue-700 dark:text-blue-300 mb-6">
                  Works With Your Tools
                </div>
                <h2 className="text-3xl font-bold tracking-tighter md:text-4xl mb-4">
                  Connects to What You Already Use
                </h2>
                <p className="text-muted-foreground md:text-lg mb-8">
                  Your voice agent integrates seamlessly with the tools you use
                  every day. No extra accounts or complicated setup — just
                  connect and go.
                </p>

                <div className="grid grid-cols-2 gap-4">
                  {[
                    { icon: Mail, name: "Gmail", desc: "Send & read emails" },
                    {
                      icon: Calendar,
                      name: "Google Calendar",
                      desc: "Schedule meetings",
                    },
                    {
                      icon: Table,
                      name: "Google Sheets",
                      desc: "Update spreadsheets",
                    },
                    {
                      icon: Calendar,
                      name: "Cal.com",
                      desc: "Handle bookings",
                    },
                  ].map((tool, i) => (
                    <div
                      key={i}
                      className="flex items-center gap-3 p-3 rounded-xl border border-border/60 bg-background/50"
                    >
                      <div className="w-10 h-10 rounded-lg bg-muted flex items-center justify-center">
                        <tool.icon className="w-5 h-5 text-blue-600" />
                      </div>
                      <div>
                        <div className="font-medium text-sm">{tool.name}</div>
                        <div className="text-xs text-muted-foreground">
                          {tool.desc}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="relative">
                <div className="absolute inset-0 bg-gradient-to-br from-blue-600 to-cyan-600 rounded-3xl rotate-3 opacity-10" />
                <div className="relative bg-background border border-border rounded-2xl p-6 shadow-xl">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-10 h-10 rounded-full bg-green-100 dark:bg-green-950 flex items-center justify-center">
                      <CheckCircle2 className="w-5 h-5 text-green-600" />
                    </div>
                    <div>
                      <div className="font-medium">Connected & Ready</div>
                      <div className="text-sm text-muted-foreground">
                        Gmail, Calendar & Sheets linked
                      </div>
                    </div>
                  </div>
                  <div className="space-y-3">
                    <div className="h-2 bg-muted rounded-full overflow-hidden">
                      <div className="h-full w-3/4 bg-green-500 rounded-full" />
                    </div>
                    <div className="flex justify-between text-xs text-muted-foreground">
                      <span>All systems operational</span>
                      <span>Auto-connected</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* How It Works */}
        <section id="how-it-works" className="py-20 md:py-28">
          <div className="container px-4 md:px-6 max-w-7xl mx-auto">
            <div className="flex flex-col items-center justify-center space-y-4 text-center mb-16">
              <div className="inline-flex items-center rounded-full bg-blue-100 dark:bg-blue-950/50 px-4 py-1.5 text-sm font-medium text-blue-700 dark:text-blue-300">
                How It Works
              </div>
              <h2 className="text-3xl font-bold tracking-tighter md:text-4xl">
                Up and running in 3 simple steps
              </h2>
              <p className="max-w-[600px] text-muted-foreground md:text-lg">
                No technical knowledge required. If you can use email, you can
                set this up.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              {[
                {
                  step: "1",
                  title: "Create Your Agent",
                  description:
                    "Give your agent a name and decide what it should do. Our simple setup wizard guides you through.",
                  icon: Settings,
                },
                {
                  step: "2",
                  title: "Connect Your Tools",
                  description:
                    "Link your Google account or other tools with one click. We'll handle the technical stuff.",
                  icon: Zap,
                },
                {
                  step: "3",
                  title: "Start Taking Calls",
                  description:
                    "That's it! Your agent is ready. Point a phone number to it and watch it work.",
                  icon: PhoneCall,
                },
              ].map((item, index) => (
                <div key={index} className="relative">
                  <div className="text-6xl font-bold text-blue-100 dark:text-blue-950/50 absolute -top-4 -left-2">
                    {item.step}
                  </div>
                  <div className="pt-8 pl-4">
                    <div className="w-12 h-12 rounded-xl bg-blue-100 dark:bg-blue-950/50 flex items-center justify-center mb-4">
                      <item.icon className="w-6 h-6 text-blue-600" />
                    </div>
                    <h3 className="text-xl font-bold mb-2">{item.title}</h3>
                    <p className="text-muted-foreground">{item.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Testimonials */}
        <section className="py-20 md:py-28 bg-muted/30">
          <div className="container px-4 md:px-6 max-w-7xl mx-auto">
            <div className="flex flex-col items-center justify-center space-y-4 text-center mb-12">
              <h2 className="text-3xl font-bold tracking-tighter md:text-4xl">
                Loved by business owners
              </h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {[
                {
                  quote:
                    "Set up our customer support agent in under an hour. No developers needed — just me and a cup of coffee.",
                  author: "Sarah Chen",
                  role: "Founder, TechFlow",
                  avatar: "SC",
                },
                {
                  quote:
                    "Finally, technology that doesn't require a tech team. Our front desk now runs on AI and it's working great.",
                  author: "Marcus Johnson",
                  role: "Director, ScaleUp",
                  avatar: "MJ",
                },
                {
                  quote:
                    "We needed something simple for our small team. This delivers — easy to use, works perfectly.",
                  author: "Emily Rodriguez",
                  role: "Owner, DataCorp",
                  avatar: "ER",
                },
              ].map((testimonial, index) => (
                <div
                  key={index}
                  className="p-6 rounded-2xl bg-background border border-border/60"
                >
                  <div className="flex gap-1 mb-4">
                    {[...Array(5)].map((_, i) => (
                      <Star
                        key={i}
                        className="w-4 h-4 fill-yellow-400 text-yellow-400"
                      />
                    ))}
                  </div>
                  <p className="text-muted-foreground mb-6 italic">
                    &ldquo;{testimonial.quote}&rdquo;
                  </p>
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-blue-100 dark:bg-blue-950 flex items-center justify-center font-medium text-blue-600">
                      {testimonial.avatar}
                    </div>
                    <div>
                      <div className="font-medium">{testimonial.author}</div>
                      <div className="text-sm text-muted-foreground">
                        {testimonial.role}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Pricing Section */}
        <section id="pricing" className="py-20 md:py-28">
          <div className="container px-4 md:px-6 max-w-7xl mx-auto">
            <div className="flex flex-col items-center justify-center space-y-4 text-center mb-16">
              <div className="inline-flex items-center rounded-full bg-blue-100 dark:bg-blue-950/50 px-4 py-1.5 text-sm font-medium text-blue-700 dark:text-blue-300">
                Pricing
              </div>
              <h2 className="text-3xl font-bold tracking-tighter md:text-4xl">
                Simple pricing, no surprises
              </h2>
              <p className="max-w-[600px] text-muted-foreground md:text-lg">
                Start free. Upgrade when you&apos;re ready. Cancel anytime.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto">
              {[
                {
                  name: "Starter",
                  price: "$0",
                  description: "Perfect for testing things out.",
                  features: [
                    "1 voice agent",
                    "30 minutes of calls/month",
                    "Basic tools (Gmail, Calendar)",
                    "Email support",
                  ],
                  cta: "Start Free",
                  popular: false,
                },
                {
                  name: "Professional",
                  price: "$99",
                  description: "For growing businesses.",
                  features: [
                    "5 voice agents",
                    "1000 minutes of calls/month",
                    "All tools included",
                    "Priority support",
                    "Call analytics",
                  ],
                  cta: "Start Free Trial",
                  popular: true,
                },
                {
                  name: "Enterprise",
                  price: "Custom",
                  description: "For large organizations.",
                  features: [
                    "Unlimited agents",
                    "Unlimited minutes",
                    "Custom integrations",
                    "24/7 phone support",
                    "Dedicated account manager",
                  ],
                  cta: "Talk to Us",
                  popular: false,
                },
              ].map((plan, index) => (
                <div
                  key={index}
                  className={`relative flex flex-col rounded-2xl border p-8 ${
                    plan.popular
                      ? "border-blue-500 shadow-xl shadow-blue-500/10 bg-background"
                      : "border-border/60 bg-background/50"
                  }`}
                >
                  {plan.popular && (
                    <div className="absolute -top-4 left-1/2 -translate-x-1/2 rounded-full bg-gradient-to-r from-blue-600 to-cyan-600 px-4 py-1 text-sm font-medium text-white">
                      Most Popular
                    </div>
                  )}
                  <h3 className="text-xl font-bold">{plan.name}</h3>
                  <div className="mt-4 flex items-baseline">
                    <span className="text-4xl font-bold">{plan.price}</span>
                    {plan.price !== "Custom" && (
                      <span className="ml-1 text-muted-foreground">/month</span>
                    )}
                  </div>
                  <p className="mt-2 text-sm text-muted-foreground">
                    {plan.description}
                  </p>
                  <ul className="mt-8 space-y-4 flex-1">
                    {plan.features.map((feature, i) => (
                      <li key={i} className="flex items-center text-sm">
                        <CheckCircle2 className="mr-3 h-4 w-4 text-blue-500 flex-shrink-0" />
                        {feature}
                      </li>
                    ))}
                  </ul>
                  <Button
                    className={`mt-8 h-12 ${
                      plan.popular
                        ? "bg-blue-600 hover:bg-blue-700"
                        : ""
                    }`}
                    variant={plan.popular ? "default" : "outline"}
                  >
                    {plan.cta}
                  </Button>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="py-20 md:py-28 bg-gradient-to-br from-blue-600 to-cyan-600">
          <div className="container px-4 md:px-6 max-w-4xl mx-auto text-center">
            <h2 className="text-3xl font-bold tracking-tighter md:text-4xl text-white mb-4">
              Ready to automate your calls?
            </h2>
            <p className="text-blue-100 md:text-lg mb-8 max-w-[600px] mx-auto">
              Join thousands of businesses using AI to handle calls. Set up
              takes minutes — no technical skills required.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link href="/auth/signup">
                <Button
                  size="lg"
                  className="px-8 h-12 text-base bg-white text-blue-600 hover:bg-blue-50"
                >
                  Start Free Trial
                  <ArrowRight className="ml-2 w-4 h-4" />
                </Button>
              </Link>
              <Button
                size="lg"
                variant="outline"
                className="px-8 h-12 text-base border-blue-300 text-white hover:bg-blue-700"
              >
                <Headphones className="mr-2 w-4 h-4" />
                Talk to Sales
              </Button>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-border/40 bg-background py-12">
        <div className="container px-4 md:px-6 max-w-7xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-12">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <div className="bg-blue-100 dark:bg-blue-950 w-8 h-8 rounded-lg flex items-center justify-center">
                  <Phone className="w-4 h-4 text-blue-600" />
                </div>
                <span className="font-bold">VoiceAI</span>
              </div>
              <p className="text-sm text-muted-foreground">
                AI voice agents for every business.
              </p>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Product</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li><a href="#features" className="hover:text-foreground">Features</a></li>
                <li><a href="#pricing" className="hover:text-foreground">Pricing</a></li>
                <li><a href="#" className="hover:text-foreground">Help Center</a></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Company</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li><a href="#" className="hover:text-foreground">About</a></li>
                <li><a href="#" className="hover:text-foreground">Blog</a></li>
                <li><a href="#" className="hover:text-foreground">Contact</a></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Legal</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li><a href="#" className="hover:text-foreground">Privacy</a></li>
                <li><a href="#" className="hover:text-foreground">Terms</a></li>
                <li><a href="#" className="hover:text-foreground">Security</a></li>
              </ul>
            </div>
          </div>
          <div className="pt-8 border-t border-border/40 flex flex-col md:flex-row items-center justify-between gap-4">
            <p className="text-sm text-muted-foreground">
              © 2025 VoiceAI Platform. All rights reserved.
            </p>
            <div className="flex items-center gap-4">
              <Globe className="w-5 h-5 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">English (US)</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
