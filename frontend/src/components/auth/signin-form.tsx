'use client';

import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Eye, EyeOff, Loader2, Mail, Lock } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useAuth } from '@/contexts/auth-context';
import Link from 'next/link';
import { EmailVerificationBanner } from '@/components/auth/email-verification-banner';

const signInSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
  password: z.string().min(1, 'Password is required'),
});

type SignInData = z.infer<typeof signInSchema>;

export function SignInForm() {
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [email, setEmail] = useState<string>('');
  const [showVerificationBanner, setShowVerificationBanner] = useState(false);
  const { signIn, signInWithOAuth } = useAuth();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<SignInData>({
    resolver: zodResolver(signInSchema),
  });

  const handleSignIn = async (data: SignInData) => {
    setIsLoading('password');
    setError('');
    setEmail(data.email);
    setShowVerificationBanner(false);

    try {
      const result = await signIn(data);
      if (result?.error) {
        setError(result.error.message || 'Failed to sign in');
      }
      // Success case handled by global route guard
    } catch (error) {
      console.log('Sign in error:', error);
      // Check if it's an email not confirmed error from Supabase
      if (error && typeof error === 'object' && 'code' in error && typeof error.code === 'string') {
        const errCode = error.code.toLowerCase();
        if (errCode === 'email_not_confirmed') {
          setShowVerificationBanner(true);
          setError(null);
        } else if (errCode === 'invalid_credentials') {
          setError('Invalid credentials. Please try again with the correct credentials.');
        } else {
          setError('An unexpected error occurred. Please try again.');
        }
      } else {
        setError('An unexpected error occurred. Please try again.');
      }
    } finally {
      setIsLoading(null);
    }
  };

  const handleGoogleSignIn = async () => {
    setIsLoading('google');
    setError('');
    try {
      const result = await signInWithOAuth('google');
      if (result?.error) {
        setError(result.error.message || 'Failed to sign in with Google');
        setIsLoading(null);
      }
      // Note: If successful, OAuth will redirect the user away from this page
    } catch (error) {
      console.error('Google sign in error:', error);
      setError('An unexpected error occurred. Please try again.');
      setIsLoading(null);
    }
  };

  const handleLinkedInSignIn = async () => {
    setIsLoading('linkedin_oidc');
    setError('');
    try {
      const result = await signInWithOAuth('linkedin_oidc');
      if (result?.error) {
        setError(result.error.message || 'Failed to sign in with LinkedIn');
        setIsLoading(null);
      }
      // Note: If successful, OAuth will redirect the user away from this page
    } catch (error) {
      console.error('LinkedIn sign in error:', error);
      setError('An unexpected error occurred. Please try again.');
      setIsLoading(null);
    }
  };

  const handleCloseVerificationBanner = () => {
    setShowVerificationBanner(false);
    setEmail('');
  };

  return (
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
              {...register('email')}
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
              type={showPassword ? 'text' : 'password'}
              {...register('password')}
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
            <p className="text-sm text-destructive">{errors.password.message}</p>
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
            <Label htmlFor="remember" className="text-sm font-normal text-muted-foreground cursor-pointer">
              Remember me
            </Label>
          </div>
          <button
            type="button"
            className="text-sm font-medium text-primary hover:text-primary/80 cursor-pointer"
            disabled={!!isLoading}
          >
            Forgot password?
          </button>
        </div>

        <Button type="submit" className="w-full cursor-pointer" disabled={!!isLoading}>
          {isLoading === 'password' ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Signing in...
            </>
          ) : (
            'Sign In'
          )}
        </Button>
      </form>

      <div className="relative my-6">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-border" />
        </div>
        <div className="relative flex justify-center text-sm">
          <span className="px-2 bg-card text-muted-foreground">Or continue with</span>
        </div>
      </div>

      <div className="space-y-4">
        <Button
          variant="outline"
          onClick={handleGoogleSignIn}
          disabled={!!isLoading}
          className="w-full flex items-center justify-center cursor-pointer h-11"
        >
          {isLoading === 'google' ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Signing in with Google...
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
              <span>Sign in with Google</span>
            </div>
          )}
        </Button>

        <Button
          variant="outline"
          onClick={handleLinkedInSignIn}
          disabled={!!isLoading}
          className="w-full flex items-center justify-center cursor-pointer h-11"
        >
          {isLoading === 'linkedin_oidc' ? (
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
          By signing in, you agree to the{' '}
          <Link href="/terms" className="text-primary hover:text-primary/80 hover:underline cursor-pointer">
            Terms of Service
          </Link>{' '}
          and{' '}
          <Link href="/privacy" className="text-primary hover:text-primary/80 hover:underline cursor-pointer">
            Privacy Policy
          </Link>
        </p>
      </div>
    </div>
  );
}
