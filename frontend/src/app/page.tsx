"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  CheckCircle2,
  Phone,
  Globe,
  Calendar,
  Mail,
  Table,
  Settings,
  MessageSquare,
  ArrowRight,
  Play,
  Building2,
  Headphones,
  Plug,
  Clock,
  PhoneCall,
  CalendarCheck,
  MessageCircle,
  ClipboardList,
  UserCheck,
  BellRing,
  Stethoscope,
  Wrench,
  UtensilsCrossed,
  Scissors,
  Home,
} from "lucide-react";
import { SITE_NAME, SITE_SALES_EMAIL } from "@/lib/site-config";

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
  const scrollToHowItWorks = () => {
    document
      .getElementById("how-it-works")
      ?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col font-sans">
      {/* Header */}
      <header className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/80 backdrop-blur-md supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-16 items-center justify-between max-w-7xl mx-auto px-4">
          <div className="flex items-center gap-3">
            <div className="bg-gradient-to-br from-blue-600 to-cyan-600 w-10 h-10 rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/20">
              <Phone className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-bold tracking-tight">
              {SITE_NAME}
            </span>
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
              href="#industries"
              className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
            >
              Industries
            </a>
            <a
              href="#demos"
              className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
            >
              Live demos
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
            <Link href="/request-demo">
              <Button size="sm" className="bg-blue-600 hover:bg-blue-700">
                Request a Demo
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
                  No coding required - we set it up with you, live in 48 hours
                </div>

                <div className="space-y-4">
                  <h1 className="text-4xl font-bold tracking-tighter sm:text-5xl xl:text-6xl/none">
                    Never miss a call, a booking, or{" "}
                    <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-cyan-600">
                      a customer again.
                    </span>
                  </h1>
                  <p className="max-w-[540px] text-muted-foreground md:text-xl leading-relaxed">
                    {SITE_NAME} is your always-on front desk. It answers every
                    call, books appointments, answers questions, and follows up
                    - so every customer gets a great experience and your team
                    stays focused on the work that grows your business.
                  </p>
                </div>

                <div className="flex flex-col gap-3 sm:flex-row">
                  <Link href="/request-demo">
                    <Button
                      size="lg"
                      className="bg-blue-600 hover:bg-blue-700 px-8 h-12 text-base"
                    >
                      Request a Demo
                      <ArrowRight className="ml-2 w-4 h-4" />
                    </Button>
                  </Link>
                  <Button
                    size="lg"
                    variant="outline"
                    className="px-8 h-12 text-base"
                    onClick={scrollToHowItWorks}
                  >
                    <Play className="mr-2 w-4 h-4" />
                    See How It Works
                  </Button>
                </div>

                <div className="flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-6 text-sm text-muted-foreground">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-green-500" />
                    <span>Answers nights, weekends &amp; busy hours</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-green-500" />
                    <span>Books straight to your calendar</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-green-500" />
                    <span>You approve every word it says</span>
                  </div>
                </div>
              </div>

              {/* Hero Visual - a real business moment: call → booked */}
              <div className="relative mx-auto w-full max-w-[560px] lg:max-w-none">
                <div className="relative max-w-[500px] mx-auto">
                  <div className="absolute inset-0 bg-gradient-to-br from-blue-600 to-cyan-600 rounded-3xl rotate-3 opacity-20" />
                  <div className="relative bg-background border border-border rounded-3xl shadow-2xl overflow-hidden">
                    {/* Call header */}
                    <div className="h-16 bg-muted/50 border-b flex items-center justify-between px-5">
                      <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-full bg-blue-600 flex items-center justify-center">
                          <PhoneCall className="w-4 h-4 text-white" />
                        </div>
                        <div>
                          <div className="text-sm font-semibold">
                            Incoming call
                          </div>
                          <div className="text-xs text-muted-foreground">
                            Maria G. · New patient
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-1.5 text-xs text-green-600 font-medium">
                        <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                        Answered
                      </div>
                    </div>

                    <div className="p-5 space-y-3">
                      {/* Live call waveform */}
                      <div className="h-14 rounded-xl bg-muted/50 flex items-center justify-center gap-1">
                        <WaveformVisual />
                      </div>

                      {/* Conversation snippet */}
                      <div className="p-3 rounded-lg bg-blue-100/60 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-800">
                        <div className="flex items-start gap-2">
                          <MessageSquare className="w-4 h-4 text-blue-600 mt-0.5" />
                          <p className="text-xs text-muted-foreground leading-relaxed">
                            &ldquo;Hi Maria! I can get you in for a cleaning
                            this Thursday at 2:00 PM. Does that work for
                            you?&rdquo;
                          </p>
                        </div>
                      </div>

                      {/* Booking confirmation */}
                      <div className="p-3 rounded-lg bg-green-100/70 dark:bg-green-950/40 border border-green-200 dark:border-green-800">
                        <div className="flex items-center gap-2 text-sm font-medium">
                          <CalendarCheck className="w-4 h-4 text-green-600" />
                          Appointment booked
                        </div>
                        <div className="mt-1 text-xs text-muted-foreground">
                          Thu 2:00 PM · Synced to Google Calendar
                        </div>
                        <div className="mt-1.5 flex items-center gap-2 text-xs text-green-700 dark:text-green-300">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          Confirmation recorded in the demo outcome
                        </div>
                      </div>
                    </div>

                    {/* Outcome strip */}
                    <div className="border-t border-border bg-muted/30 px-5 py-3 flex items-center justify-between text-xs text-muted-foreground">
                      <div className="flex items-center gap-2">
                        <Clock className="w-4 h-4 text-blue-600" />
                        Every call answered, 24x7
                      </div>
                      <div className="flex items-center gap-2">
                        <CheckCircle2 className="w-4 h-4 text-green-600" />
                        No missed customers
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Live demos */}
        <section id="demos" className="border-y border-border/40 bg-slate-950 py-20 text-white md:py-28">
          <div className="container mx-auto max-w-7xl px-4 md:px-6">
            <div className="mx-auto mb-12 max-w-3xl text-center">
              <div className="mb-4 inline-flex items-center rounded-full border border-cyan-400/20 bg-cyan-400/10 px-4 py-1.5 text-sm font-medium text-cyan-200">
                Try it yourself
              </div>
              <h2 className="text-3xl font-bold tracking-tight md:text-4xl">
                See the handoff, not just the conversation
              </h2>
              <p className="mt-4 text-base leading-7 text-slate-300 md:text-lg">
                Talk to a live demo agent, then review the exact fields it
                captured and the business system it updated.
              </p>
            </div>

            <div className="grid gap-6 lg:grid-cols-2">
              <Link
                href="/demo/pleasant-pediatric-appointments"
                className="group rounded-3xl border border-white/10 bg-white/[0.06] p-6 transition hover:-translate-y-1 hover:border-cyan-300/40 hover:bg-white/[0.1] md:p-8"
              >
                <div className="flex items-start justify-between gap-6">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-cyan-400/15 text-cyan-300">
                    <CalendarCheck className="h-6 w-6" />
                  </div>
                  <ArrowRight className="h-5 w-5 text-slate-500 transition group-hover:translate-x-1 group-hover:text-cyan-300" />
                </div>
                <p className="mt-8 text-xs font-semibold uppercase tracking-[0.18em] text-cyan-300">
                  Appointment booking
                </p>
                <h3 className="mt-2 text-2xl font-semibold">Book a dental visit</h3>
                <p className="mt-3 max-w-md leading-7 text-slate-300">
                  Alex checks availability, confirms the appointment, and writes
                  the event to Google Calendar.
                </p>
                <p className="mt-6 text-sm font-medium text-cyan-200">Talk to Alex →</p>
              </Link>

              <Link
                href="/demo/copper-ridge-service-request"
                className="group rounded-3xl border border-white/10 bg-white/[0.06] p-6 transition hover:-translate-y-1 hover:border-orange-300/40 hover:bg-white/[0.1] md:p-8"
              >
                <div className="flex items-start justify-between gap-6">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-orange-400/15 text-orange-300">
                    <Wrench className="h-6 w-6" />
                  </div>
                  <ArrowRight className="h-5 w-5 text-slate-500 transition group-hover:translate-x-1 group-hover:text-orange-300" />
                </div>
                <p className="mt-8 text-xs font-semibold uppercase tracking-[0.18em] text-orange-300">
                  Lead capture
                </p>
                <h3 className="mt-2 text-2xl font-semibold">Request HVAC service</h3>
                <p className="mt-3 max-w-md leading-7 text-slate-300">
                  Jordan gathers the full service request, confirms it with the
                  caller, and records it in Google Sheets for follow-up.
                </p>
                <p className="mt-6 text-sm font-medium text-orange-200">Talk to Jordan →</p>
              </Link>
            </div>
          </div>
        </section>

        {/* Industries Section (replaces fabricated logos/testimonials) */}
        <section
          id="industries"
          className="py-20 md:py-28 border-y border-border/40"
        >
          <div className="container px-4 md:px-6 max-w-7xl mx-auto">
            <div className="flex flex-col items-center justify-center space-y-4 text-center mb-16">
              <div className="inline-flex items-center rounded-full bg-blue-100 dark:bg-blue-950/50 px-4 py-1.5 text-sm font-medium text-blue-700 dark:text-blue-300">
                Industries
              </div>
              <h2 className="text-3xl font-bold tracking-tighter md:text-4xl lg:text-5xl">
                Built for businesses that live on the phone
              </h2>
              <p className="max-w-[700px] text-muted-foreground md:text-xl leading-relaxed">
                If your business takes calls, {SITE_NAME} can answer them for
                you - booking appointments, answering questions, and capturing
                follow-up requests for your team.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {[
                {
                  title: "Dental & medical",
                  description:
                    "Book cleanings, exams, and new-patient intake - even after hours.",
                  icon: Stethoscope,
                  gradient: "from-blue-500 to-cyan-500",
                  href: "/dental",
                },
                {
                  title: "HVAC & home services",
                  description:
                    "Schedule service calls and triage urgent issues before they escalate.",
                  icon: Wrench,
                  gradient: "from-orange-500 to-amber-500",
                  href: "/hvac",
                },
                {
                  title: "Restaurants",
                  description:
                    "Take reservations, party bookings, and special requests without tying up your staff.",
                  icon: UtensilsCrossed,
                  gradient: "from-rose-500 to-pink-500",
                },
                {
                  title: "Salons & spas",
                  description:
                    "Fill your books with appointments and reminders that reduce no-shows.",
                  icon: Scissors,
                  gradient: "from-purple-500 to-fuchsia-500",
                },
                {
                  title: "Real estate & property",
                  description:
                    "Qualify leads and book showings the moment they call - day or night.",
                  icon: Home,
                  gradient: "from-emerald-500 to-teal-500",
                },
                {
                  title: "Every service business",
                  description:
                    "Law, consulting, repair shops, and more - your front desk, always on.",
                  icon: Building2,
                  gradient: "from-indigo-500 to-blue-500",
                },
              ].map((industry, index) => {
                const card = (
                  <>
                    <div
                      className={`w-12 h-12 rounded-xl bg-gradient-to-br ${industry.gradient} flex items-center justify-center mb-4 shadow-lg`}
                    >
                      <industry.icon className="w-6 h-6 text-white" />
                    </div>
                    <h3 className="text-lg font-bold mb-2">{industry.title}</h3>
                    <p className="text-sm text-muted-foreground leading-relaxed">
                      {industry.description}
                    </p>
                    {"href" in industry && industry.href && (
                      <span className="mt-3 inline-flex items-center text-sm font-medium text-blue-600">
                        Learn more
                        <ArrowRight className="ml-1 w-4 h-4" />
                      </span>
                    )}
                  </>
                );
                const className =
                  "group relative p-6 rounded-2xl border border-border/60 bg-background/50 backdrop-blur-sm transition-all hover:border-blue-500/30 hover:shadow-xl hover:shadow-blue-500/5 block";
                return "href" in industry && industry.href ? (
                  <Link
                    key={index}
                    href={industry.href as string}
                    className={className}
                  >
                    {card}
                  </Link>
                ) : (
                  <div key={index} className={className}>
                    {card}
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        {/* Features Section - business outcomes */}
        <section id="features" className="py-20 md:py-28">
          <div className="container px-4 md:px-6 max-w-7xl mx-auto">
            <div className="flex flex-col items-center justify-center space-y-4 text-center mb-16">
              <div className="inline-flex items-center rounded-full bg-blue-100 dark:bg-blue-950/50 px-4 py-1.5 text-sm font-medium text-blue-700 dark:text-blue-300">
                Features
              </div>
              <h2 className="text-3xl font-bold tracking-tighter md:text-4xl lg:text-5xl">
                Everything your front desk should handle - automatically
              </h2>
              <p className="max-w-[700px] text-muted-foreground md:text-xl leading-relaxed">
                {SITE_NAME} takes the work your team does on the phone and does
                it for you, so no customer is ever left waiting.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {[
                {
                  title: "Answer every call, 24x7",
                  description:
                    "Never lose a customer to voicemail. Your agent picks up instantly - nights, weekends, and holidays.",
                  icon: PhoneCall,
                  gradient: "from-blue-500 to-cyan-500",
                },
                {
                  title: "Book & manage appointments",
                  description:
                    "Schedule, reschedule, and cancel bookings over the phone. Everything syncs to your calendar automatically.",
                  icon: CalendarCheck,
                  gradient: "from-blue-500 to-cyan-500",
                },
                {
                  title: "Answer customer questions",
                  description:
                    "Hours, services, pricing, location - your agent answers instantly with your business info.",
                  icon: MessageCircle,
                  gradient: "from-orange-500 to-amber-500",
                },
                {
                  title: "Capture new customers",
                  description:
                    "Collect names, contact details, and preferences from callers - ready for your team when they come in.",
                  icon: ClipboardList,
                  gradient: "from-green-500 to-emerald-500",
                },
                {
                  title: "Follow up & win customers back",
                  description:
                    "Capture callback requests and send your team the context they need to follow up.",
                  icon: BellRing,
                  gradient: "from-pink-500 to-rose-500",
                },
                {
                  title: "Never leaves a caller hanging",
                  description:
                    "When a call needs a person, your agent offers a callback and sends your team the full context.",
                  icon: UserCheck,
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
                  Syncs with the tools you already use
                </h2>
                <p className="text-muted-foreground md:text-lg mb-8">
                  Your agent plugs into the calendar, email, and spreadsheets
                  your business runs on - so bookings land where they should,
                  and your records stay up to date without lifting a finger.
                </p>

                <div className="grid grid-cols-2 gap-4">
                  {[
                    {
                      icon: Mail,
                      name: "Gmail",
                      desc: "Confirmations sent automatically",
                    },
                    {
                      icon: Calendar,
                      name: "Google Calendar",
                      desc: "Bookings land on your calendar",
                    },
                    {
                      icon: Table,
                      name: "Google Sheets",
                      desc: "Customer records updated",
                    },
                    {
                      icon: Calendar,
                      name: "Cal.com",
                      desc: "Bookings synced",
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
                        Calendar, email & records linked
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
                Live in 48 hours - we do the setup with you
              </h2>
              <p className="max-w-[600px] text-muted-foreground md:text-lg">
                No tech skills needed on your side. Request a demo, we
                configure everything around your business, and you approve it
                before it answers a single call.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              {[
                {
                  step: "1",
                  title: "Request a demo",
                  description:
                    "Tell us about your business in 30 seconds - what you offer and what your agent should handle.",
                  icon: Settings,
                },
                {
                  step: "2",
                  title: "We configure it with you",
                  description:
                    "We set up your number, link your calendar, and run test calls until it sounds exactly like your front desk.",
                  icon: Plug,
                },
                {
                  step: "3",
                  title: "Go live in 48 hours",
                  description:
                    "Approve the setup and your agent starts answering - nights, weekends, and every busy hour after.",
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

        {/* Pricing Section - outcome-focused, no hardcoded dollar figures */}
        <section id="pricing" className="py-20 md:py-28 bg-muted/30">
          <div className="container px-4 md:px-6 max-w-7xl mx-auto">
            <div className="flex flex-col items-center justify-center space-y-4 text-center mb-16">
              <div className="inline-flex items-center rounded-full bg-blue-100 dark:bg-blue-950/50 px-4 py-1.5 text-sm font-medium text-blue-700 dark:text-blue-300">
                Pricing
              </div>
              <h2 className="text-3xl font-bold tracking-tighter md:text-4xl">
                Simple pricing that grows with you
              </h2>
              <p className="max-w-[600px] text-muted-foreground md:text-lg">
                Start with a concierge pilot - configured for your business,
                live in 48 hours. Simple monthly plans from $79 as you grow,
                no long-term contracts.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto">
              {[
                {
                  name: "Free to start",
                  description:
                    "Hear a live demo and see what an AI front desk can do for your business.",
                  features: [
                    "1 voice agent",
                    "Concierge setup included",
                    "No credit card to try the demo",
                  ],
                  cta: "Request a Demo",
                  popular: false,
                },
                {
                  name: "For growing teams",
                  description:
                    "More agents and more call capacity as your business picks up.",
                  features: [
                    "Multiple voice agents",
                    "All tools & skills included",
                    "Call analytics & history",
                    "Priority support",
                  ],
                  cta: "Request a Demo",
                  popular: true,
                },
                {
                  name: "For multi-location",
                  description:
                    "Custom plans for businesses that need scale - and a dedicated partner.",
                  features: [
                    "Unlimited agents",
                    "Custom integrations",
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
                  <Link
                    href={
                      plan.cta === "Talk to Us"
                        ? `mailto:${SITE_SALES_EMAIL}`
                        : "/request-demo"
                    }
                    className="mt-8"
                  >
                    <Button
                      className={`h-12 w-full ${
                        plan.popular ? "bg-blue-600 hover:bg-blue-700" : ""
                      }`}
                      variant={plan.popular ? "default" : "outline"}
                    >
                      {plan.cta}
                    </Button>
                  </Link>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="py-20 md:py-28 bg-gradient-to-br from-blue-600 to-cyan-600">
          <div className="container px-4 md:px-6 max-w-4xl mx-auto text-center">
            <h2 className="text-3xl font-bold tracking-tighter md:text-4xl text-white mb-4">
              Ready to never miss another call?
            </h2>
            <p className="text-blue-100 md:text-lg mb-8 max-w-[600px] mx-auto">
              Hear a live demo, then go live in 48 hours with our setup help -
              no coding required.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link href="/request-demo">
                <Button
                  size="lg"
                  className="px-8 h-12 text-base bg-white text-blue-600 hover:bg-blue-50"
                >
                  Request a Demo
                  <ArrowRight className="ml-2 w-4 h-4" />
                </Button>
              </Link>
              <a href={`mailto:${SITE_SALES_EMAIL}`}>
                <Button
                  size="lg"
                  variant="outline"
                  className="h-12 px-8 text-base border-white/30 bg-white/10 text-white backdrop-blur-sm hover:bg-white/20 hover:text-white dark:bg-white/10 dark:hover:bg-white/25"
                >
                  <Headphones className="mr-2 w-4 h-4" />
                  Talk to Sales
                </Button>
              </a>
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
                <span className="font-bold">{SITE_NAME}</span>
              </div>
              <p className="text-sm text-muted-foreground">
                Your AI front desk. Always on.
              </p>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Product</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li>
                  <a href="#features" className="hover:text-foreground">
                    Features
                  </a>
                </li>
                <li>
                  <a href="#industries" className="hover:text-foreground">
                    Industries
                  </a>
                </li>
                <li>
                  <a href="#pricing" className="hover:text-foreground">
                    Pricing
                  </a>
                </li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Company</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li>
                  <a href="#" className="hover:text-foreground">
                    About
                  </a>
                </li>
                <li>
                  <a href="#" className="hover:text-foreground">
                    Blog
                  </a>
                </li>
                <li>
                  <a
                    href={`mailto:${SITE_SALES_EMAIL}`}
                    className="hover:text-foreground"
                  >
                    Contact
                  </a>
                </li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Legal</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li>
                  <a href="#" className="hover:text-foreground">
                    Privacy
                  </a>
                </li>
                <li>
                  <a href="#" className="hover:text-foreground">
                    Terms
                  </a>
                </li>
                <li>
                  <a href="#" className="hover:text-foreground">
                    Security
                  </a>
                </li>
              </ul>
            </div>
          </div>
          <div className="pt-8 border-t border-border/40 flex flex-col md:flex-row items-center justify-between gap-4">
            <p className="text-sm text-muted-foreground">
              © {new Date().getFullYear()} {SITE_NAME}. All rights reserved.
            </p>
            <div className="flex items-center gap-4">
              <Globe className="w-5 h-5 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">
                English (US)
              </span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
