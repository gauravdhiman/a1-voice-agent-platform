"use client";

import React from "react";
import { SignInForm } from "@/components/auth/signin-form";
import { ProtectedRoute } from "@/components/auth/protected-route";
import Link from "next/link";
import {
  PhoneCall,
  CalendarCheck,
  TrendingUp,
  CheckCircle2,
} from "lucide-react";
import { SITE_NAME } from "@/lib/site-config";

export default function SignInPage() {
  return (
    <ProtectedRoute reverse>
      <div className="min-h-screen w-full flex">
        {/* Left Side - Brand & Value Statement (Hidden on mobile) */}
        <div className="hidden lg:flex w-1/2 bg-zinc-900 relative flex-col justify-between p-12 text-white">
          <div className="absolute inset-0 bg-[url('https://images.unsplash.com/photo-1556761175-b413da4baf72?q=80&w=2029&auto=format&fit=crop')] opacity-20 bg-cover bg-center" />
          <div className="absolute inset-0 bg-gradient-to-t from-zinc-900 via-zinc-900/80 to-transparent" />

          <div className="relative z-10">
            <Link href="/" className="flex items-center space-x-2">
              <div className="bg-white/10 backdrop-blur-sm w-10 h-10 rounded-lg flex items-center justify-center border border-white/20">
                <span className="text-white font-bold text-xl">AI</span>
              </div>
              <span className="text-xl font-bold tracking-tight">
                {SITE_NAME}
              </span>
            </Link>
          </div>

          <div className="relative z-10 max-w-lg">
            <PhoneCall className="h-10 w-10 text-white/50 mb-6" />
            <h2 className="text-3xl font-bold leading-tight mb-6">
              Every call answered.
              <br />
              Every appointment booked.
            </h2>
            <ul className="space-y-4">
              <li className="flex items-start gap-3">
                <CheckCircle2 className="h-5 w-5 text-blue-400 mt-0.5 flex-shrink-0" />
                <span className="text-white/80">
                  Your calls answered 24x7 - nights, weekends, and holidays.
                </span>
              </li>
              <li className="flex items-start gap-3">
                <CalendarCheck className="h-5 w-5 text-blue-400 mt-0.5 flex-shrink-0" />
                <span className="text-white/80">
                  Appointments booked and synced to your calendar automatically.
                </span>
              </li>
              <li className="flex items-start gap-3">
                <TrendingUp className="h-5 w-5 text-blue-400 mt-0.5 flex-shrink-0" />
                <span className="text-white/80">
                  No missed customers, no lost revenue.
                </span>
              </li>
            </ul>
          </div>

          <div className="relative z-10 text-sm text-white/40">
            &copy; {new Date().getFullYear()} {SITE_NAME}. All rights reserved.
          </div>
        </div>

        {/* Right Side - Form */}
        <div className="flex-1 flex items-center justify-center p-8 bg-background">
          <div className="w-full max-w-md space-y-8">
            <div className="text-center lg:text-left">
              <div className="lg:hidden flex justify-center mb-6">
                <div className="bg-primary w-10 h-10 rounded-lg flex items-center justify-center shadow-md">
                  <span className="text-primary-foreground font-bold text-xl">
                    AI
                  </span>
                </div>
              </div>
              <h1 className="text-3xl font-bold tracking-tight text-foreground">
                Welcome back
              </h1>
              <p className="text-muted-foreground mt-2">
                Sign in to manage your AI front desk, agents, and calls.
              </p>
            </div>

            <SignInForm />

            <div className="text-center text-sm text-muted-foreground">
              Don&apos;t have an account?{" "}
              <Link
                href="/auth/signup"
                className="font-medium text-primary hover:text-primary/80 underline-offset-4 hover:underline transition-colors"
              >
                Sign up for free
              </Link>
            </div>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
