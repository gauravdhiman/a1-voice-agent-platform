"use client";

import { ProtectedRoute } from "@/components/auth/protected-route";

export default function OnboardingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
        {children}
      </div>
    </ProtectedRoute>
  );
}
