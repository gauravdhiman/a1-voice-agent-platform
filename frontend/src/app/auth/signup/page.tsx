"use client";

import React, { useEffect } from "react";
import { useRouter } from "next/navigation";
import { SignUpForm } from "@/components/auth/signup-form";
import { ProtectedRoute } from "@/components/auth/protected-route";
import Link from "next/link";
import { Zap, CalendarCheck, CreditCard } from "lucide-react";
import { SITE_NAME } from "@/lib/site-config";
import { leadService } from "@/services/lead-service";
import { PublicThemeRoot } from "@/components/public-theme/public-theme-root";
import { PublicHeader } from "@/components/public-theme/public-header";
import { PublicFooter } from "@/components/public-theme/public-footer";
import pt from "@/components/public-theme/public-theme.module.css";

export default function SignUpPage() {
  const router = useRouter();

  useEffect(() => {
    // Controlled-SaaS gate: invited visitors carry ?token= and stay;
    // everyone else is sent to the interest form while open signup
    // is disabled. The backend gate remains authoritative.
    // (window.location avoids a Suspense boundary for search params.)
    const params = new URLSearchParams(window.location.search);
    if (params.get("token")) return;
    leadService.isPublicSignupEnabled().then((open) => {
      if (!open) router.replace("/request-demo");
    });
  }, [router]);

  return (
    <ProtectedRoute reverse>
      <PublicThemeRoot>
        <div className={pt.page}>
          <PublicHeader />
          <div className={pt.split}>
            {/* Left Side - Brand & Value Statement (Hidden on mobile) */}
            <div className={pt.splitPanel}>
              <div className={pt.splitPanelGlow} aria-hidden="true" />
              <div className={pt.splitPanelInner}>
                <p className={pt.eyebrow}>
                  <span className={pt.statusDot} />
                  CONCIERGE SETUP · NO CODING
                </p>
                <h2 style={{ marginTop: 24 }}>
                  Set up your AI front desk in minutes.
                </h2>
                <p
                  style={{
                    fontSize: 15,
                    lineHeight: 1.8,
                    marginTop: 20,
                    maxWidth: 420,
                  }}
                >
                  No code. No IT. No headset. If you can use email, you can
                  launch your first agent - answering calls, booking
                  appointments, and following up with customers, 24x7.
                </p>
                <ul className={pt.splitPoints}>
                  <li>
                    <Zap className="h-5 w-5 flex-shrink-0" />
                    <span>Live in minutes - no technical knowledge needed</span>
                  </li>
                  <li>
                    <CalendarCheck className="h-5 w-5 flex-shrink-0" />
                    <span>Works with Google Calendar, Gmail &amp; more</span>
                  </li>
                  <li>
                    <CreditCard className="h-5 w-5 flex-shrink-0" />
                    <span>Free to start - no credit card required</span>
                  </li>
                </ul>
              </div>

              <div className={pt.splitFoot}>
                &copy; {new Date().getFullYear()} {SITE_NAME}. All rights
                reserved.
              </div>
            </div>

            {/* Right Side - Form */}
            <div className={pt.splitBody}>
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
                    Create your free account
                  </h1>
                  <p className="text-muted-foreground mt-2">
                    Start free - no credit card required. Your first agent can
                    be live in minutes.
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
          <PublicFooter />
        </div>
      </PublicThemeRoot>
    </ProtectedRoute>
  );
}
