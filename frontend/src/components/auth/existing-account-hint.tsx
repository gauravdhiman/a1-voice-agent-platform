/**
 * Inline guidance when a signup email is already registered.
 */

import Link from "next/link";
import { AlertCircle } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import type { SignInMethod } from "@/types/auth";

const METHOD_LABELS: Record<SignInMethod, string> = {
  email: "Email and password",
  google: "Google",
  linkedin: "LinkedIn",
};

interface ExistingAccountHintProps {
  message: string;
  signInMethods?: SignInMethod[];
  email?: string;
}

/**
 * Shows when an email is already registered during signup.
 *
 * Surfaces linked sign-in methods and links to the sign-in page instead of a
 * generic failure message.
 */
export function ExistingAccountHint({
  message,
  signInMethods = [],
  email,
}: ExistingAccountHintProps) {
  const signInHref = email
    ? `/auth/signin?email=${encodeURIComponent(email)}`
    : "/auth/signin";

  return (
    <Alert className="border-amber-200 bg-amber-50 text-amber-950">
      <AlertCircle className="h-4 w-4 text-amber-700" />
      <AlertDescription className="space-y-2">
        <p>{message}</p>
        {signInMethods.length > 0 ? (
          <p className="text-sm">
            Available sign-in methods:{" "}
            {signInMethods.map((method) => METHOD_LABELS[method]).join(" · ")}
          </p>
        ) : null}
        <p className="text-sm">
          <Link href={signInHref} className="font-medium underline underline-offset-4">
            Go to sign in
          </Link>
        </p>
      </AlertDescription>
    </Alert>
  );
}
