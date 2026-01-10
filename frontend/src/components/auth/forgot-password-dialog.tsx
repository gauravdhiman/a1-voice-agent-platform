"use client";

import React, { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Mail, Loader2, CheckCircle, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { supabase } from "@/lib/supabase";

const forgotPasswordSchema = z.object({
  email: z.string().email("Please enter a valid email address"),
});

type ForgotPasswordData = z.infer<typeof forgotPasswordSchema>;

interface ForgotPasswordDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ForgotPasswordDialog({
  open,
  onOpenChange,
}: ForgotPasswordDialogProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [emailSent, setEmailSent] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<ForgotPasswordData>({
    resolver: zodResolver(forgotPasswordSchema),
  });

  const handleForgotPassword = async (data: ForgotPasswordData) => {
    setIsLoading(true);
    setError(null);
    setSuccess(false);

    try {
      // Use direct Supabase call with clean redirect URL
      // Supabase will handle the token and type parameters internally
      // and redirect to our clean URL: /auth/reset-password
      const redirectUrl = `${window.location.origin}/auth/reset-password`;

      // Send the password reset email using Supabase directly
      const { error: supabaseError } =
        await supabase.auth.resetPasswordForEmail(data.email, {
          redirectTo: redirectUrl,
        });

      if (supabaseError) {
        console.error("Supabase forgot password error:", supabaseError);
        throw new Error(
          supabaseError.message || "Failed to send password reset email",
        );
      }

      // Success - email sent
      setSuccess(true);
      setEmailSent(data.email);
      reset();
    } catch (error) {
      console.error("Forgot password error:", error);
      setError(
        error instanceof Error
          ? error.message
          : "Failed to send password reset email",
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleClose = () => {
    onOpenChange(false);
    setSuccess(false);
    setEmailSent(null);
    setError(null);
    reset();
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Forgot Password</DialogTitle>
          <DialogDescription>
            {success
              ? "Password reset email sent successfully"
              : "Enter your email address to reset your password"}
          </DialogDescription>
        </DialogHeader>

        {!success ? (
          <form
            onSubmit={handleSubmit(handleForgotPassword)}
            className="space-y-6"
          >
            {error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
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
                  disabled={isLoading}
                />
              </div>
              {errors.email && (
                <p className="text-sm text-destructive">
                  {errors.email.message}
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
                  Sending reset email...
                </>
              ) : (
                "Send Reset Email"
              )}
            </Button>
          </form>
        ) : (
          <div className="space-y-6 text-center">
            <div className="flex justify-center">
              <CheckCircle className="h-12 w-12 text-green-500" />
            </div>
            <h3 className="text-lg font-medium">Email Sent!</h3>
            <p className="text-sm text-muted-foreground">
              We&apos;ve sent a password reset link to{" "}
              <span className="font-medium text-foreground">{emailSent}</span>.
              Please check your email and follow the instructions to reset your
              password.
            </p>
            <Button onClick={handleClose} className="w-full cursor-pointer">
              Back to Sign In
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
