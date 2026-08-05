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
import { EmailVerificationBanner } from "@/components/auth/email-verification-banner";
import { ForgotPasswordDialog } from "@/components/auth/forgot-password-dialog";
import { GoogleSignInButton } from "@/components/auth/google-sign-in-button";

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
  const { signIn, signInWithOAuth, signInWithGoogleIdToken } = useAuth();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<SignInData>({
    resolver: zodResolver(signInSchema),
  });

  const handleSignIn = async (data: SignInData) => {
    setIsLoading("password");
    setError("");
    setEmail(data.email);
    setShowVerificationBanner(false);

    try {
      const result = await signIn(data);
      if (result?.error) {
        setError(result.error.message || "Failed to sign in");
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

  const handleGoogleCredential = async (credential: string, nonce: string) => {
    setIsLoading("google");
    setError("");
    try {
      const result = await signInWithGoogleIdToken({
        token: credential,
        nonce,
      });
      if (result?.error) {
        setError(result.error.message || "Failed to sign in with Google");
      }
    } catch (error) {
      console.error("Google sign in error:", error);
      setError(
        error instanceof Error
          ? error.message
          : "An unexpected error occurred. Please try again.",
      );
    } finally {
      setIsLoading(null);
    }
  };

  const handleGoogleError = (message: string) => {
    setError(message);
    setIsLoading(null);
  };

  const handleLinkedInSignIn = async () => {
    setIsLoading("linkedin_oidc");
    setError("");
    try {
      const result = await signInWithOAuth("linkedin_oidc");
      if (result?.error) {
        setError(result.error.message || "Failed to sign in with LinkedIn");
        setIsLoading(null);
      }
      // Note: If successful, OAuth will redirect the user away from this page
    } catch (error) {
      console.error("LinkedIn sign in error:", error);
      setError("An unexpected error occurred. Please try again.");
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
          <GoogleSignInButton
            text="signin_with"
            onCredential={handleGoogleCredential}
            onError={handleGoogleError}
            disabled={!!isLoading}
            className="w-full"
          />

          <Button
            variant="outline"
            onClick={handleLinkedInSignIn}
            disabled={!!isLoading}
            className="w-full flex items-center justify-center cursor-pointer h-11"
          >
            {isLoading === "linkedin_oidc" ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Signing in with LinkedIn...
              </>
            ) : (
              <div className="flex items-center justify-center gap-3">
                <svg className="h-5 w-5" viewBox="0 0 24 24" fill="#0077B5">
                  <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
                </svg>
                <span>Sign in with LinkedIn</span>
              </div>
            )}
          </Button>
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
