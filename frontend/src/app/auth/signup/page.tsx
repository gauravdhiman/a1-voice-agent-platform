"use client";

import React from "react";
import { SignUpForm } from "@/components/auth/signup-form";
import { ProtectedRoute } from "@/components/auth/protected-route";
import Link from "next/link";
import { Rocket } from "lucide-react";

export default function SignUpPage() {
  return (
    <ProtectedRoute reverse>
      <div className="min-h-screen w-full flex">
        {/* Left Side - Brand & Testimonial (Hidden on mobile) */}
        <div className="hidden lg:flex w-1/2 bg-zinc-900 relative flex-col justify-between p-12 text-white">
          <div className="absolute inset-0 bg-[url('https://images.unsplash.com/photo-1635070041078-e363dbe005cb?q=80&w=2070&auto=format&fit=crop')] opacity-20 bg-cover bg-center" />
          <div className="absolute inset-0 bg-gradient-to-t from-zinc-900 via-zinc-900/80 to-transparent" />

          <div className="relative z-10">
            <Link href="/" className="flex items-center space-x-2">
              <div className="bg-white/10 backdrop-blur-sm w-10 h-10 rounded-lg flex items-center justify-center border border-white/20">
                <span className="text-white font-bold text-xl">AI</span>
              </div>
              <span className="text-xl font-bold tracking-tight">
                NeuraSaaS
              </span>
            </Link>
          </div>

          <div className="relative z-10 max-w-lg">
            <Rocket className="h-10 w-10 text-white/50 mb-6" />
            <h2 className="text-3xl font-bold mb-4">
              Start building the future
            </h2>
            <p className="text-lg text-white/80 leading-relaxed">
              Join thousands of developers and businesses who are already using
              NeuraSaaS to power their next-generation voice applications.
            </p>
            <div className="mt-8 flex gap-4">
              <div className="flex flex-col">
                <span className="text-2xl font-bold">10k+</span>
                <span className="text-sm text-white/60">Active Users</span>
              </div>
              <div className="w-px bg-white/20" />
              <div className="flex flex-col">
                <span className="text-2xl font-bold">99.9%</span>
                <span className="text-sm text-white/60">Uptime</span>
              </div>
            </div>
          </div>

          <div className="relative z-10 text-sm text-white/40">
            &copy; {new Date().getFullYear()} NeuraSaaS Inc. All rights
            reserved.
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
                Create an account
              </h1>
              <p className="text-muted-foreground mt-2">
                Enter your details below to create your account
              </p>
            </div>

            <SignUpForm />

            <div className="text-center text-sm text-muted-foreground">
              Already have an account?{" "}
              <Link
                href="/auth/signin"
                className="font-medium text-primary hover:text-primary/80 underline-offset-4 hover:underline transition-colors"
              >
                Sign in
              </Link>
            </div>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
