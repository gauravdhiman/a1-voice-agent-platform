import React, { useCallback, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Eye, EyeOff, Loader2, Mail, Lock, User, Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useAuth } from "@/contexts/auth-context";
import { useSearchParams, useRouter } from "next/navigation";
import { OAuthRedirectButton } from "@/components/auth/oauth-redirect-button";
import { ExistingAccountHint } from "@/components/auth/existing-account-hint";
import { authService } from "@/services/auth-service";
import {
  signUpSchema,
  type SignUpFormData,
} from "@/lib/auth/signup-schema";
import type { SignInMethod } from "@/types/auth";

export function SignUpForm() {
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isLoading, setIsLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [existingAccountMessage, setExistingAccountMessage] = useState<
    string | null
  >(null);
  const [existingSignInMethods, setExistingSignInMethods] = useState<
    SignInMethod[]
  >([]);
  const [isCheckingEmail, setIsCheckingEmail] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [isSignUpComplete, setIsSignUpComplete] = useState(false);

  const { signUp } = useAuth();
  const searchParams = useSearchParams();
  const router = useRouter();
  const invitationToken = searchParams?.get("token");

  const {
    register,
    handleSubmit,
    formState: { errors, isValid },
    watch,
    trigger,
    reset,
  } = useForm<SignUpFormData>({
    resolver: zodResolver(signUpSchema),
    mode: "onChange",
    reValidateMode: "onChange",
    defaultValues: {
      firstName: "",
      lastName: "",
      email: "",
      password: "",
      passwordConfirm: "",
    },
  });

  const password = watch("password");
  const passwordConfirm = watch("passwordConfirm");
  const emailValue = watch("email");

  const checkEmailAvailability = useCallback(
    async (email: string) => {
      const trimmedEmail = email.trim();
      if (!trimmedEmail || !z.string().email().safeParse(trimmedEmail).success) {
        setExistingAccountMessage(null);
        setExistingSignInMethods([]);
        return;
      }

      setIsCheckingEmail(true);
      try {
        const result = await authService.checkEmailAvailability(trimmedEmail);
        if (result.success && result.data?.exists) {
          setExistingAccountMessage(
            result.data.message ||
              "An account with this email already exists. Please sign in instead.",
          );
          setExistingSignInMethods(result.data.signInMethods);
        } else {
          setExistingAccountMessage(null);
          setExistingSignInMethods([]);
        }
      } finally {
        setIsCheckingEmail(false);
      }
    },
    [],
  );

  // Re-validate confirm password when either password field changes.
  React.useEffect(() => {
    if (passwordConfirm.length > 0) {
      void trigger("passwordConfirm");
    }
  }, [password, passwordConfirm, trigger]);

  const isSubmitDisabled =
    !!isLoading ||
    !!existingAccountMessage ||
    isCheckingEmail ||
    !isValid;

  const getPasswordStrength = (password: string) => {
    let strength = 0;
    if (password?.length >= 8) strength++;
    if (/[A-Z]/.test(password)) strength++;
    if (/[a-z]/.test(password)) strength++;
    if (/\d/.test(password)) strength++;
    if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) strength++;
    return strength;
  };

  const passwordStrength = password ? getPasswordStrength(password) : 0;
  const strengthColors = [
    "bg-red-500",
    "bg-red-400",
    "bg-yellow-500",
    "bg-blue-500",
    "bg-green-500",
  ];
  const strengthLabels = ["Very Weak", "Weak", "Fair", "Good", "Strong"];

  const onSubmit = async (data: SignUpFormData) => {
    setIsLoading("password");
    setError(null);
    setExistingAccountMessage(null);
    setExistingSignInMethods([]);
    setSuccess(null);

    try {
      const { user, emailVerificationRequired, error } = await signUp({
        email: data.email,
        password: data.password,
        passwordConfirm: data.passwordConfirm,
        firstName: data.firstName,
        lastName: data.lastName,
        invitationToken: invitationToken || undefined,
      });

      if (error) {
        const message =
          typeof error === "object" && error !== null && "message" in error
            ? String(error.message)
            : String(error);
        const signInMethods =
          typeof error === "object" &&
          error !== null &&
          "signInMethods" in error &&
          Array.isArray(error.signInMethods)
            ? (error.signInMethods as SignInMethod[])
            : [];

        if (signInMethods.length > 0) {
          setExistingAccountMessage(message);
          setExistingSignInMethods(signInMethods);
          setError(null);
        } else {
          setError(message);
        }
      } else if (user) {
        reset();
        setIsSignUpComplete(true);

        if (emailVerificationRequired) {
          if (invitationToken) {
            setSuccess(
              "Account created! Please check your email for verification. You will be added to the organization after email confirmation.",
            );
          } else {
            setSuccess(
              "Account created! Please check your email for verification.",
            );
          }
          return;
        }

        router.replace("/dashboard");
      } else {
        setError("User details not returned after signup. Please try again.");
      }
    } catch (error) {
      console.error("Sign up error:", error);
      setError("An unexpected error occurred. Please try again.");
    } finally {
      setIsLoading(null);
    }
  };

  return (
    <div className="w-full max-w-md mx-auto">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {invitationToken && !isSignUpComplete && (
          <Alert className="border-primary/20 bg-primary/5">
            <Users className="h-4 w-4 text-primary" />
            <AlertDescription className="text-primary">
              You&apos;ve been invited to join an organization! Create your
              account to get started.
            </AlertDescription>
          </Alert>
        )}

        {existingAccountMessage ? (
          <ExistingAccountHint
            message={existingAccountMessage}
            signInMethods={existingSignInMethods}
            email={emailValue}
          />
        ) : null}

        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {success && (
          <Alert className="border-green-200 bg-green-50 text-green-800">
            <AlertDescription>{success}</AlertDescription>
          </Alert>
        )}

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="firstName">First Name</Label>
            <div className="relative">
              <User className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <Input
                id="firstName"
                {...register("firstName")}
                placeholder="John"
                className="pl-10"
                disabled={!!isLoading}
              />
            </div>
            {errors.firstName && (
              <p className="text-sm text-destructive">
                {errors.firstName.message}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="lastName">Last Name</Label>
            <div className="relative">
              <User className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <Input
                id="lastName"
                {...register("lastName")}
                placeholder="Doe"
                className="pl-10"
                disabled={!!isLoading}
              />
            </div>
            {errors.lastName && (
              <p className="text-sm text-destructive">
                {errors.lastName.message}
              </p>
            )}
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="email">Email Address</Label>
          <div className="relative">
            <Mail className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
            <Input
              id="email"
              type="email"
              {...register("email", {
                onBlur: (event) => {
                  void checkEmailAvailability(event.target.value);
                },
              })}
              placeholder="john@example.com"
              className="pl-10"
              disabled={!!isLoading}
            />
          </div>
          {isCheckingEmail ? (
            <p className="text-xs text-muted-foreground">Checking email...</p>
          ) : null}
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
              placeholder="Create a strong password"
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

          {password && (
            <div className="space-y-2">
              <div className="flex space-x-1">
                {[1, 2, 3, 4, 5].map((level) => (
                  <div
                    key={level}
                    className={`h-1 flex-1 rounded ${
                      passwordStrength >= level
                        ? strengthColors[passwordStrength - 1]
                        : "bg-muted"
                    }`}
                  />
                ))}
              </div>
              <p className="text-xs text-muted-foreground">
                Password strength:{" "}
                {strengthLabels[passwordStrength - 1] || "Very Weak"}
              </p>
            </div>
          )}

          {errors.password && (
            <p className="text-sm text-destructive">
              {errors.password.message}
            </p>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="passwordConfirm">Confirm Password</Label>
          <div className="relative">
            <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
            <Input
              id="passwordConfirm"
              type={showConfirmPassword ? "text" : "password"}
              {...register("passwordConfirm")}
              placeholder="Confirm your password"
              className="pl-10 pr-10"
              disabled={!!isLoading}
              onBlur={() => {
                if (passwordConfirm.length > 0) {
                  void trigger("passwordConfirm");
                }
              }}
            />
            <button
              type="button"
              onClick={() => setShowConfirmPassword(!showConfirmPassword)}
              className="absolute right-3 top-3 h-4 w-4 text-muted-foreground hover:text-foreground cursor-pointer"
              disabled={!!isLoading}
            >
              {showConfirmPassword ? <EyeOff /> : <Eye />}
            </button>
          </div>
          {errors.passwordConfirm && (
            <p className="text-sm text-destructive">
              {errors.passwordConfirm.message}
            </p>
          )}
        </div>

        <Button
          id="create-account-button"
          type="submit"
          className="w-full cursor-pointer"
          disabled={isSubmitDisabled}
          aria-disabled={isSubmitDisabled}
        >
          {isLoading === "password" ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Creating Account...
            </>
          ) : (
            "Create Account"
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
          text="signup_with"
          invitationToken={invitationToken || undefined}
          disabled={!!isLoading}
          className="w-full"
        />

        <OAuthRedirectButton
          provider="linkedin"
          text="signup_with"
          invitationToken={invitationToken || undefined}
          disabled={!!isLoading}
          className="w-full"
        />
      </div>
    </div>
  );
}
