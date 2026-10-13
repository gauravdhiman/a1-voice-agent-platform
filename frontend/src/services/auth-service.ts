// services/auth-service.ts
import { apiClient, ApiRequestError } from "@/lib/api/client";
import type {
  EmailAvailabilityResult,
  SignInMethod,
  SignUpData,
  SignUpErrorDetails,
  UserProfile,
} from "@/types/auth";

function parseConflictDetail(error: ApiRequestError): SignUpErrorDetails {
  const detail = (error.data as { detail?: unknown } | undefined)?.detail;
  if (detail && typeof detail === "object" && "message" in detail) {
    const payload = detail as {
      message?: string;
      sign_in_methods?: SignInMethod[];
    };
    return {
      message: payload.message || error.message,
      signInMethods: payload.sign_in_methods,
    };
  }

  return { message: error.message };
}

// Auth Service class
class AuthService {
  private baseUrl = "/api/v1/auth";

  async checkEmailAvailability(email: string): Promise<{
    success: boolean;
    error?: string;
    data?: EmailAvailabilityResult;
  }> {
    try {
      const response = await apiClient.get<{
        exists: boolean;
        sign_in_methods: SignInMethod[];
        message?: string;
      }>(
        `${this.baseUrl}/check-email?email=${encodeURIComponent(email.trim())}`,
      );

      const payload = response.data;
      return {
        success: true,
        data: {
          exists: payload.exists,
          signInMethods: payload.sign_in_methods ?? [],
          message: payload.message,
        },
      };
    } catch (error) {
      return {
        success: false,
        error:
          error instanceof Error ? error.message : "Unable to check email.",
      };
    }
  }

  // Sign up via backend (org provisioning + verification gating)
  async signUp(data: SignUpData): Promise<{
    success: boolean;
    error?: string;
    errorDetails?: SignUpErrorDetails;
    emailVerificationRequired?: boolean;
    user?: UserProfile;
    joinedOrganizationId?: string | null;
    joinedOrganizationName?: string | null;
  }> {
    try {
      const response = await apiClient.post<{
        user: UserProfile;
        email_verification_required: boolean;
        access_token?: string | null;
        refresh_token?: string | null;
        expires_in?: number | null;
        joined_organization_id?: string | null;
        joined_organization_name?: string | null;
      }>(`${this.baseUrl}/signup`, {
        email: data.email,
        password: data.password,
        password_confirm: data.passwordConfirm,
        first_name: data.firstName,
        last_name: data.lastName,
        terms_accepted: data.terms_accepted,
        invitation_token: data.invitationToken,
        captcha_token: data.captchaToken,
      });

      const payload = response.data;
      if (!payload?.user) {
        return {
          success: false,
          error: "Failed to create user account.",
        };
      }

      if (
        !payload.email_verification_required &&
        payload.access_token &&
        payload.refresh_token
      ) {
        const { supabase } = await import("@/lib/supabase");
        const { error: sessionError } = await supabase.auth.setSession({
          access_token: payload.access_token,
          refresh_token: payload.refresh_token,
        });
        if (sessionError) {
          return {
            success: false,
            error: sessionError.message,
          };
        }
      }

      return {
        success: true,
        emailVerificationRequired: payload.email_verification_required,
        user: payload.user,
        joinedOrganizationId: payload.joined_organization_id ?? null,
        joinedOrganizationName: payload.joined_organization_name ?? null,
      };
    } catch (error) {
      if (error instanceof ApiRequestError && error.status === 409) {
        const errorDetails = parseConflictDetail(error);
        return {
          success: false,
          error: errorDetails.message,
          errorDetails,
        };
      }

      return {
        success: false,
        error: error instanceof Error ? error.message : "Sign up failed.",
      };
    }
  }

  async signIn(data: { email: string; password: string }): Promise<{
    success: boolean;
    error?: string;
    code?: string;
  }> {
    try {
      const response = await apiClient.post<{
        access_token?: string;
        refresh_token?: string;
      }>(`${this.baseUrl}/signin`, {
        email: data.email,
        password: data.password,
      });

      const { access_token, refresh_token } = response.data;
      if (access_token && refresh_token) {
        const { supabase } = await import("@/lib/supabase");
        const { error: sessionError } = await supabase.auth.setSession({
          access_token,
          refresh_token,
        });
        if (sessionError) {
          return { success: false, error: sessionError.message };
        }
      }

      return { success: true };
    } catch (error) {
      if (error instanceof ApiRequestError) {
        const detail = (error.data as { detail?: unknown } | undefined)?.detail;
        if (detail && typeof detail === "object" && detail !== null) {
          const payload = detail as { message?: string; code?: string };
          return {
            success: false,
            error: payload.message || error.message,
            code: payload.code,
          };
        }
        return { success: false, error: error.message };
      }
      return {
        success: false,
        error: error instanceof Error ? error.message : "Sign in failed.",
      };
    }
  }

  async resendVerificationEmail(email: string): Promise<{
    success: boolean;
    error?: string;
    message?: string;
  }> {
    try {
      const response = await apiClient.post<{ message: string }>(
        `${this.baseUrl}/resend-verification`,
        { email },
      );
      return { success: true, message: response.data.message };
    } catch (error) {
      return {
        success: false,
        error:
          error instanceof Error ? error.message : "Failed to resend email.",
      };
    }
  }

  async verifyEmail(token: string): Promise<{
    success: boolean;
    error?: string;
    message?: string;
  }> {
    try {
      const response = await apiClient.post<{
        success: boolean;
        message: string;
      }>(`${this.baseUrl}/verify-email`, { token });
      return {
        success: response.data.success,
        message: response.data.message,
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : "Verification failed.",
      };
    }
  }

  // Process invitation to add user to organization
  async processInvitation(
    token: string,
    userId: string,
  ): Promise<{
    success: boolean;
    error?: string;
    data?: unknown;
  }> {
    try {
      const response = await apiClient.post(
        `${this.baseUrl}/process-invitation`,
        {
          token,
          user_id: userId,
        },
      );

      return {
        success: true,
        data: response.data,
      };
    } catch (error) {
      const errorMessage = (error as Error).message;
      return {
        success: false,
        error: errorMessage,
      };
    }
  }

  // Get current user profile
  async getCurrentUser(orgId?: string | null): Promise<{
    success: boolean;
    error?: string;
    user?: UserProfile;
  }> {
    try {
      // Forward the current org id so the backend can resolve the
      // permissions object for the right org context. When orgId is
      // undefined or null, the backend returns an empty permissions map
      // (no org context to resolve against).
      const url = orgId
        ? `${this.baseUrl}/me?org_id=${encodeURIComponent(orgId)}`
        : `${this.baseUrl}/me`;
      const response = await apiClient.get<UserProfile>(url);

      return {
        success: true,
        user: response.data,
      };
    } catch (error) {
      const errorMessage = (error as Error).message;
      return {
        success: false,
        error: errorMessage,
      };
    }
  }

  // Refresh auth token
  async refreshToken(refreshToken: string): Promise<{
    success: boolean;
    error?: string;
    data?: unknown;
  }> {
    try {
      const response = await apiClient.post(`${this.baseUrl}/refresh`, {
        refresh_token: refreshToken,
      });

      return {
        success: true,
        data: response.data,
      };
    } catch (error) {
      const errorMessage = (error as Error).message;
      return {
        success: false,
        error: errorMessage,
      };
    }
  }

  // Sign out
  async signOut(): Promise<{
    success: boolean;
    error?: string;
  }> {
    try {
      await apiClient.post(`${this.baseUrl}/signout`);

      return {
        success: true,
      };
    } catch (error) {
      const errorMessage = (error as Error).message;
      return {
        success: false,
        error: errorMessage,
      };
    }
  }
}

// Export singleton instance
export const authService = new AuthService();
