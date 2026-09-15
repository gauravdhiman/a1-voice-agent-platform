"use client";

import React from "react";
import { SignInForm } from "@/components/auth/signin-form";
import { ProtectedRoute } from "@/components/auth/protected-route";
import Link from "next/link";
import { CalendarCheck, TrendingUp, CheckCircle2 } from "lucide-react";
import { SITE_NAME } from "@/lib/site-config";
import { PublicThemeRoot } from "@/components/public-theme/public-theme-root";
import { PublicHeader } from "@/components/public-theme/public-header";
import { PublicFooter } from "@/components/public-theme/public-footer";
import pt from "@/components/public-theme/public-theme.module.css";

export default function SignInPage() {
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
                  YOUR AI FRONT DESK · ALWAYS ON
                </p>
                <h2 style={{ marginTop: 24 }}>
                  Every call answered.
                  <br />
                  <span>Every appointment booked.</span>
                </h2>
                <ul className={pt.splitPoints}>
                  <li>
                    <CheckCircle2 className="h-5 w-5 flex-shrink-0" />
                    <span>
                      Your calls answered 24x7 - nights, weekends, and holidays.
                    </span>
                  </li>
                  <li>
                    <CalendarCheck className="h-5 w-5 flex-shrink-0" />
                    <span>
                      Appointments booked and synced to your calendar
                      automatically.
                    </span>
                  </li>
                  <li>
                    <TrendingUp className="h-5 w-5 flex-shrink-0" />
                    <span>No missed customers, no lost revenue.</span>
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
          <PublicFooter />
        </div>
      </PublicThemeRoot>
    </ProtectedRoute>
  );
}
