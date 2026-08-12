import { ApiResponse } from "@/types";
import { supabase } from "@/lib/supabase";
import {
  getSafeApiErrorMessage,
  redactSensitiveLogMessage,
} from "@/lib/api/error-message";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiRequestError extends Error {
  status: number;
  data?: unknown;

  constructor(message: string, status: number, data?: unknown) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
    this.data = data;
  }
}

class ApiClient {
  private baseURL: string;
  private headers: Record<string, string>;

  constructor() {
    this.baseURL = API_BASE_URL;
    this.headers = {
      "Content-Type": "application/json",
    };
  }

  setAuthToken(token: string) {
    this.headers["Authorization"] = `Bearer ${token}`;
  }

  clearAuthToken() {
    delete this.headers["Authorization"];
  }

  private async getAuthHeaders(): Promise<Record<string, string>> {
    try {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (session?.access_token) {
        return {
          Authorization: `Bearer ${session.access_token}`,
        };
      }
    } catch (error) {
      console.warn("Failed to get auth session:", error);
    }
    return {};
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
    retryCount = 0,
  ): Promise<ApiResponse<T>> {
    const url = `${this.baseURL}${endpoint}`;

    // Get authentication headers
    const authHeaders = await this.getAuthHeaders();

    const config: RequestInit = {
      ...options,
      headers: {
        ...this.headers,
        ...authHeaders,
        ...options.headers,
      },
    };

    try {
      const response = await fetch(url, config);

      // Handle different response types
      let data;
      if (response.status === 204) {
        // No Content — don't try to parse body
        data = null;
      } else {
        const contentType = response.headers.get("content-type");
        if (contentType && contentType.includes("application/json")) {
          data = await response.json();
        } else {
          data = await response.text();
        }
      }

      if (!response.ok) {
        // Handle 401 - attempt token refresh and retry once
        if (response.status === 401 && retryCount === 0) {
          try {
            const {
              data: { session },
              error,
            } = await supabase.auth.refreshSession();

            if (!error && session?.access_token) {
              // Retry with new token
              return this.request<T>(endpoint, options, retryCount + 1);
            } else {
              console.warn("Token refresh failed:", error);
              // Fall through to error handling
            }
          } catch (refreshError) {
            console.warn("Token refresh error:", refreshError);
            // Fall through to error handling
          }
        }

        // Handle specific error cases
        if (response.status === 401) {
          throw new Error("Authentication required. Please sign in.");
        }
        if (response.status === 403) {
          throw new Error(
            "Access denied. You do not have permission to perform this action.",
          );
        }
        const errorMessage = getSafeApiErrorMessage(data);

        throw new ApiRequestError(errorMessage, response.status, data);
      }

      // Handle both wrapped and direct responses
      return data?.data !== undefined ? data : { data, success: true };
    } catch (error) {
      if (error instanceof ApiRequestError) {
        console.error(
          "API request error:",
          redactSensitiveLogMessage(error.message),
        );
      } else if (error instanceof Error) {
        console.error("API request error:", error.message);
      } else {
        console.error("API request error");
      }
      throw error;
    }
  }

  async get<T>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: "GET" });
  }

  /**
   * Fetches an authenticated binary response such as a private call recording.
   *
   * @param endpoint - API endpoint that returns the binary payload
   * @returns Promise resolving to the response Blob
   * @throws {Error} When authentication, network, or API validation fails
   */
  async getBlob(endpoint: string, retryCount = 0): Promise<Blob> {
    const url = `${this.baseURL}${endpoint}`;
    const authHeaders = await this.getAuthHeaders();
    const response = await fetch(url, {
      method: "GET",
      headers: {
        ...authHeaders,
        Accept: "audio/wav, audio/*",
      },
    });

    if (response.status === 401 && retryCount === 0) {
      const {
        data: { session },
        error,
      } = await supabase.auth.refreshSession();
      if (!error && session?.access_token) {
        return this.getBlob(endpoint, retryCount + 1);
      }
    }

    if (!response.ok) {
      if (response.status === 401) {
        throw new Error("Authentication required. Please sign in.");
      }
      if (response.status === 403) {
        throw new Error(
          "Access denied. You do not have permission to perform this action.",
        );
      }
      let detail: unknown;
      try {
        detail = await response.json();
      } catch {
        detail = await response.text();
      }
      throw new ApiRequestError(
        getSafeApiErrorMessage(detail),
        response.status,
        detail,
      );
    }

    return response.blob();
  }

  async post<T>(
    endpoint: string,
    data?: unknown,
    options: Pick<RequestInit, "headers"> = {},
  ): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: "POST",
      body: data ? JSON.stringify(data) : undefined,
      ...options,
    });
  }

  async put<T>(endpoint: string, data?: unknown): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: "PUT",
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async patch<T>(endpoint: string, data?: unknown): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: "PATCH",
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async delete<T>(
    endpoint: string,
    options: Pick<RequestInit, "headers"> = {},
  ): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: "DELETE", ...options });
  }
}

export const apiClient = new ApiClient();
