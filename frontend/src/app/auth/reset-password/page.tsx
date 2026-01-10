"use client";

import React, { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  Eye,
  EyeOff,
  Loader2,
  CheckCircle,
  AlertCircle,
  Lock,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";

const resetPasswordSchema = z
  .object({
    password: z.string().min(8, "Password must be at least 8 characters long"),
    confirmPassword: z.string().min(1, "Please confirm your password"),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords don't match",
    path: ["confirmPassword"],
  });

type ResetPasswordData = z.infer<typeof resetPasswordSchema>;

export default function ResetPasswordPage() {
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const router = useRouter();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ResetPasswordData>({
    resolver: zodResolver(resetPasswordSchema),
  });

  const handleResetPassword = async (data: ResetPasswordData) => {
    setIsLoading(true);
    setError(null);

    try {
      // Use Supabase's updateUser method to reset password
      // Supabase automatically handles the session token that was created during the redirect
      const { error: supabaseError } = await supabase.auth.updateUser({
        password: data.password,
      });

      if (supabaseError) {
        console.error("Supabase password reset error:", supabaseError);
        if (
          supabaseError.message.includes("invalid") ||
          supabaseError.message.includes("expired")
        ) {
          throw new Error("Invalid or expired password reset link");
        } else if (supabaseError.message.includes("Authentication required")) {
          throw new Error("Please sign in to reset your password");
        } else {
          throw new Error(supabaseError.message || "Failed to reset password");
        }
      }

      // Success - password updated
      setSuccess(true);
    } catch (error) {
      console.error("Reset password error:", error);
      setError(
        error instanceof Error ? error.message : "Failed to reset password",
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleBackToSignIn = () => {
    router.push("/auth/signin");
  };

  if (success) {
    return (
      <div className="min-h-screen w-full flex items-center justify-center p-8 bg-background">
        <div className="w-full max-w-md space-y-8 text-center">
          <CheckCircle className="mx-auto h-12 w-12 text-green-500" />
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Password Reset Successful
          </h1>
          <p className="text-muted-foreground">
            Your password has been successfully updated. You can now sign in
            with your new password.
          </p>
          <Button onClick={handleBackToSignIn} className="mt-6">
            Sign In
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen w-full flex items-center justify-center p-8 bg-background">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center">
          <div className="flex justify-center mb-6">
            <div className="bg-primary w-10 h-10 rounded-lg flex items-center justify-center shadow-md">
              <span className="text-primary-foreground font-bold text-xl">
                AI
              </span>
            </div>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">
            Reset Password
          </h1>
          <p className="text-muted-foreground mt-2">
            Enter your new password below
          </p>
        </div>

        <form
          onSubmit={handleSubmit(handleResetPassword)}
          className="space-y-6"
        >
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <div className="space-y-2">
            <Label htmlFor="password">New Password</Label>
            <div className="relative">
              <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <Input
                id="password"
                type={showPassword ? "text" : "password"}
                {...register("password")}
                placeholder="Enter your new password"
                className="pl-10 pr-10"
                disabled={isLoading}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-3 h-4 w-4 text-muted-foreground hover:text-foreground cursor-pointer"
                disabled={isLoading}
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

          <div className="space-y-2">
            <Label htmlFor="confirmPassword">Confirm Password</Label>
            <div className="relative">
              <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <Input
                id="confirmPassword"
                type={showConfirmPassword ? "text" : "password"}
                {...register("confirmPassword")}
                placeholder="Confirm your new password"
                className="pl-10 pr-10"
                disabled={isLoading}
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                className="absolute right-3 top-3 h-4 w-4 text-muted-foreground hover:text-foreground cursor-pointer"
                disabled={isLoading}
              >
                {showConfirmPassword ? <EyeOff /> : <Eye />}
              </button>
            </div>
            {errors.confirmPassword && (
              <p className="text-sm text-destructive">
                {errors.confirmPassword.message}
              </p>
            )}
          </div>

          <Button
            type="submit"
            className="w-full cursor-pointer"
            disabled={isLoading}
          >
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Resetting password...
              </>
            ) : (
              "Reset Password"
            )}
          </Button>
        </form>

        <div className="mt-6 text-center">
          <p className="text-sm text-muted-foreground">
            Remembered your password?{" "}
            <button
              type="button"
              onClick={handleBackToSignIn}
              className="font-medium text-primary hover:text-primary/80 hover:underline cursor-pointer"
            >
              Sign in
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}
