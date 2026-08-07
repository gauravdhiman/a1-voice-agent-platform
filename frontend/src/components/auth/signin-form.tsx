"use client";

import React, { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Eye, EyeOff, Loader2, Mail, Lock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useAuth } from "@/contexts/auth-context";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { EmailVerificationBanner } from "@/components/auth/email-verification-banner";
import { ForgotPasswordDialog } from "@/components/auth/forgot-password-dialog";
import { OAuthRedirectButton } from "@/components/auth/oauth-redirect-button";

const signInSchema = z.object({
  email: z.string().email("Please enter a valid email address"),
  password: z.string().min(1, "Password is required"),
});

type SignInData = z.infer<typeof signInSchema>;

export function SignInForm() {
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [email, setEmail] = useState<string>("");
  const [showVerificationBanner, setShowVerificationBanner] = useState(false);
  const [showForgotPasswordDialog, setShowForgotPasswordDialog] =
    useState(false);
  const { signIn } = useAuth();
  const searchParams = useSearchParams();
  const prefilledEmail = searchParams?.get("email") || "";

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<SignInData>({
    resolver: zodResolver(signInSchema),
    defaultValues: {
      email: prefilledEmail,
      password: "",
    },
  });

  const handleSignIn = async (data: SignInData) => {
    setIsLoading("password");
    setError("");
    setEmail(data.email);
    setShowVerificationBanner(false);

    try {
      const result = await signIn(data);
      if (result?.error) {
        const err = result.error as Error & { code?: string };
        if (err.code === "email_not_confirmed") {
          setShowVerificationBanner(true);
          setError(null);
        } else {
          setError(err.message || "Failed to sign in");
        }
      }
      // Success case handled by global route guard
    } catch (error) {
      console.log("Sign in error:", error);
      // Check if it's an email not confirmed error from Supabase
      if (
        error &&
        typeof error === "object" &&
        "code" in error &&
        typeof error.code === "string"
      ) {
        const errCode = error.code.toLowerCase();
        if (errCode === "email_not_confirmed") {
          setShowVerificationBanner(true);
          setError(null);
        } else if (errCode === "invalid_credentials") {
          setError(
            "Invalid credentials. Please try again with the correct credentials.",
          );
        } else {
          setError("An unexpected error occurred. Please try again.");
        }
      } else {
        setError("An unexpected error occurred. Please try again.");
      }
    } finally {
      setIsLoading(null);
    }
  };

  const handleCloseVerificationBanner = () => {
    setShowVerificationBanner(false);
    setEmail("");
  };

  return (
    <>
      <div className="w-full max-w-md mx-auto">
        {showVerificationBanner && email && (
          <EmailVerificationBanner
            email={email}
            onClose={handleCloseVerificationBanner}
          />
        )}

        <form onSubmit={handleSubmit(handleSignIn)} className="space-y-6">
          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <div className="space-y-2">
            <Label htmlFor="email">Email Address</Label>
            <div className="relative">
              <Mail className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <Input
                id="email"
                type="email"
                {...register("email")}
                placeholder="john@example.com"
                className="pl-10"
                disabled={!!isLoading}
              />
            </div>
            {errors.email && (
              <p className="text-sm text-destructive">{errors.email.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <div className="relative">
              <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <Input
                id="password"
                type={showPassword ? "text" : "password"}
                {...register("password")}
                placeholder="Enter your password"
                className="pl-10 pr-10"
                disabled={!!isLoading}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-3 h-4 w-4 text-muted-foreground hover:text-foreground cursor-pointer"
                disabled={!!isLoading}
              >
                {showPassword ? <EyeOff /> : <Eye />}
              </button>
            </div>
            {errors.password && (
              <p className="text-sm text-destructive">
                {errors.password.message}
              </p>
            )}
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <input
                id="remember"
                type="checkbox"
                className="h-4 w-4 text-primary focus:ring-primary border-input rounded bg-background"
                disabled={!!isLoading}
              />
              <Label
                htmlFor="remember"
                className="text-sm font-normal text-muted-foreground cursor-pointer"
              >
                Remember me
              </Label>
            </div>
            <button
              type="button"
              className="text-sm font-medium text-primary hover:text-primary/80 cursor-pointer"
              disabled={!!isLoading}
              onClick={() => setShowForgotPasswordDialog(true)}
            >
              Forgot password?
            </button>
          </div>

          <Button
            type="submit"
            className="w-full cursor-pointer"
            disabled={!!isLoading}
          >
            {isLoading === "password" ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Signing in...
              </>
            ) : (
              "Sign In"
            )}
          </Button>
        </form>

        <div className="relative my-6">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-border" />
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="px-2 bg-card text-muted-foreground">
              Or continue with
            </span>
          </div>
        </div>

        <div className="space-y-4">
          <OAuthRedirectButton
            provider="google"
            text="signin_with"
            disabled={!!isLoading}
            className="w-full"
          />

          <OAuthRedirectButton
            provider="linkedin"
            text="signin_with"
            disabled={!!isLoading}
            className="w-full"
          />
        </div>

        <div className="mt-6 text-center">
          <p className="text-sm text-muted-foreground">
            By signing in, you agree to the{" "}
            <Link
              href="/terms"
              className="text-primary hover:text-primary/80 hover:underline cursor-pointer"
            >
              Terms of Service
            </Link>{" "}
            and{" "}
            <Link
              href="/privacy"
              className="text-primary hover:text-primary/80 hover:underline cursor-pointer"
            >
              Privacy Policy
            </Link>
          </p>
        </div>
      </div>

      {/* Forgot Password Dialog */}
      <ForgotPasswordDialog
        open={showForgotPasswordDialog}
        onOpenChange={setShowForgotPasswordDialog}
      />
    </>
  );
}
