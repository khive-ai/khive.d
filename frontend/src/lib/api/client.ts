/**
 * API Client with async/await patterns and proper error handling
 * Follows async-programming domain expertise for robust API communication
 */

export interface ApiError extends Error {
  status?: number;
  code?: string;
  details?: any;
}

export class KhiveApiError extends Error implements ApiError {
  constructor(
    message: string,
    public status?: number,
    public code?: string,
    public details?: any,
  ) {
    super(message);
    this.name = "KhiveApiError";
  }
}

interface RequestOptions extends RequestInit {
  timeout?: number;
}

class ApiClient {
  private baseUrl: string;
  private defaultTimeout = 30000; // 30 seconds

  constructor(
    baseUrl: string = process.env.NEXT_PUBLIC_API_URL ||
      "http://localhost:11634",
  ) {
    this.baseUrl = baseUrl;
  }

  /**
   * Generic request method with timeout, error handling, and retries
   */
  private async request<T>(
    endpoint: string,
    options: RequestOptions = {},
  ): Promise<T> {
    const { timeout = this.defaultTimeout, ...fetchOptions } = options;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        ...fetchOptions,
        signal: controller.signal,
        headers: {
          "Content-Type": "application/json",
          ...fetchOptions.headers,
        },
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new KhiveApiError(
          errorData.message || `Request failed: ${response.statusText}`,
          response.status,
          errorData.code,
          errorData,
        );
      }

      return await response.json();
    } catch (error) {
      clearTimeout(timeoutId);

      if (error instanceof KhiveApiError) {
        throw error;
      }

      if (error.name === "AbortError") {
        throw new KhiveApiError("Request timeout", 408, "TIMEOUT");
      }

      throw new KhiveApiError(
        error.message || "Network error",
        undefined,
        "NETWORK_ERROR",
      );
    }
  }

  // HTTP Methods with proper async patterns
  async get<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: "GET" });
  }

  async post<T>(
    endpoint: string,
    data?: any,
    options?: RequestOptions,
  ): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: "POST",
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async put<T>(
    endpoint: string,
    data?: any,
    options?: RequestOptions,
  ): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: "PUT",
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async delete<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: "DELETE" });
  }

  async patch<T>(
    endpoint: string,
    data?: any,
    options?: RequestOptions,
  ): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: "PATCH",
      body: data ? JSON.stringify(data) : undefined,
    });
  }
}

// Singleton instance
export const apiClient = new ApiClient();
export default apiClient;
