import React, { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Eye, EyeOff, Loader2, Mail, Lock, User, Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useAuth } from "@/contexts/auth-context";
import { useSearchParams } from "next/navigation";

const signUpSchema = z
  .object({
    firstName: z.string().min(1, "First name is required").max(50),
    lastName: z.string().min(1, "Last name is required").max(50),
    email: z.string().email("Please enter a valid email address"),
    password: z
      .string()
      .min(8, "Password must be at least 8 characters")
      .regex(/[A-Z]/, "Must contain uppercase letter")
      .regex(/[a-z]/, "Must contain lowercase letter")
      .regex(/\d/, "Must contain a number")
      .regex(/[!@#$%^&*(),.?":{}|<>]/, "Must contain special character"),
    passwordConfirm: z.string().optional(), // Make it optional
  })
  .refine(
    (data) => {
      // Only validate password match if both password and passwordConfirm have values
      if (!data.password || !data.passwordConfirm) return true;
      return data.password === data.passwordConfirm;
    },
    {
      message: "Passwords don't match",
      path: ["passwordConfirm"],
    },
  );

type SignUpFormData = z.infer<typeof signUpSchema>;

export function SignUpForm() {
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isLoading, setIsLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isSignUpComplete, setIsSignUpComplete] = useState(false);

  const { signUp, signInWithOAuth } = useAuth();
  const searchParams = useSearchParams();
  const invitationToken = searchParams?.get("token");

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
    trigger,
    reset,
  } = useForm<SignUpFormData>({
    resolver: zodResolver(signUpSchema),
    mode: "onChange", // Validate on change
  });

  const password = watch("password");
  const passwordConfirm = watch("passwordConfirm");

  // Trigger validation when passwordConfirm changes, but only if it has a value
  React.useEffect(() => {
    if (passwordConfirm && passwordConfirm.length > 0) {
      trigger("passwordConfirm");
    }
  }, [passwordConfirm, trigger]);

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
    setSuccess(null);

    try {
      const { user, error } = await signUp({
        email: data.email,
        password: data.password,
        passwordConfirm: data.passwordConfirm || "",
        firstName: data.firstName,
        lastName: data.lastName,
        invitationToken: invitationToken || undefined,
      });

      if (error) {
        setError(error.message);
      } else if (user) {
        // Clear the form after successful signup
        reset();
        setIsSignUpComplete(true);

        if (invitationToken) {
          setSuccess(
            "Account created! Please check your email for verification. You will be added to the organization after email confirmation.",
          );
        } else {
          setSuccess(
            "Account created! Please check your email for verification.",
          );
        }
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

  const handleGoogleSignUp = async () => {
    setIsLoading("google");
    setError(null);
    try {
      const result = await signInWithOAuth("google");
      if (result?.error) {
        setError(result.error.message || "Failed to sign up with Google");
        setIsLoading(null);
      }
      // Note: If successful, OAuth will redirect the user away from this page
      // The organization creation will happen in the OAuth callback handler
    } catch (error) {
      console.error("Google sign up error:", error);
      setError("An unexpected error occurred. Please try again.");
      setIsLoading(null);
    }
  };

  const handleLinkedInSignUp = async () => {
    setIsLoading("linkedin_oidc");
    setError(null);
    try {
      const result = await signInWithOAuth("linkedin_oidc");
      if (result?.error) {
        setError(result.error.message || "Failed to sign up with LinkedIn");
        setIsLoading(null);
      }
      // Note: If successful, OAuth will redirect the user away from this page
      // The organization creation will happen in the OAuth callback handler
    } catch (error) {
      console.error("LinkedIn sign up error:", error);
      setError("An unexpected error occurred. Please try again.");
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
              onBlur={() => passwordConfirm && trigger("passwordConfirm")}
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
          disabled={!!isLoading}
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
        <Button
          variant="outline"
          onClick={handleGoogleSignUp}
          disabled={!!isLoading}
          className="w-full flex items-center justify-center cursor-pointer h-11"
        >
          {isLoading === "google" ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Signing up with Google...
            </>
          ) : (
            <div className="flex items-center justify-center gap-3">
              <svg className="h-5 w-5" viewBox="0 0 24 24">
                <path
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  fill="#4285F4"
                />
                <path
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  fill="#34A853"
                />
                <path
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                  fill="#FBBC05"
                />
                <path
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                  fill="#EA4335"
                />
              </svg>
              <span>Sign up with Google</span>
            </div>
          )}
        </Button>

        <Button
          variant="outline"
          onClick={handleLinkedInSignUp}
          disabled={!!isLoading}
          className="w-full flex items-center justify-center cursor-pointer h-11"
        >
          {isLoading === "linkedin_oidc" ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Signing up with LinkedIn...
            </>
          ) : (
            <div className="flex items-center justify-center gap-3">
              <svg className="h-5 w-5" viewBox="0 0 24 24" fill="#0077B5">
                <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
              </svg>
              <span>Sign up with LinkedIn</span>
            </div>
          )}
        </Button>
      </div>
    </div>
  );
}
