"use client";

import React from "react";
import { SignInForm } from "@/components/auth/signin-form";
import { ProtectedRoute } from "@/components/auth/protected-route";
import Link from "next/link";
import { Quote } from "lucide-react";

export default function SignInPage() {
  return (
    <ProtectedRoute reverse>
      <div className="min-h-screen w-full flex">
        {/* Left Side - Brand & Testimonial (Hidden on mobile) */}
        <div className="hidden lg:flex w-1/2 bg-zinc-900 relative flex-col justify-between p-12 text-white">
          <div className="absolute inset-0 bg-[url('https://images.unsplash.com/photo-1557683316-973673baf926?q=80&w=2029&auto=format&fit=crop')] opacity-20 bg-cover bg-center" />
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
            <Quote className="h-10 w-10 text-white/50 mb-6" />
            <blockquote className="text-2xl font-medium leading-relaxed mb-6">
              &quot;This platform has completely transformed how we handle our
              voice AI workflows. The efficiency gains are remarkable.&quot;
            </blockquote>
            <div className="flex items-center space-x-4">
              <div className="h-10 w-10 rounded-full bg-white/20 flex items-center justify-center text-sm font-bold">
                JD
              </div>
              <div>
                <div className="font-semibold">Jane Doe</div>
                <div className="text-sm text-white/60">CTO at TechCorp</div>
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
                Welcome back
              </h1>
              <p className="text-muted-foreground mt-2">
                Enter your credentials to access your account
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
