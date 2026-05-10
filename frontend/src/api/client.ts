/**
 * API Client - Centralized HTTP client with JWT handling
 *
 * Security: Token stored in memory only (not localStorage) to prevent XSS theft.
 * On 401 response: clears token and redirects to login.
 */

// Module-level variables - shared across all imports, gone on page refresh
let _token: string | null = null;
let _onUnauthorized: (() => void) | null = null;

/**
 * Register a callback to handle 401 unauthorized responses.
 * The AuthContext will use this to redirect to login.
 */
export function setOnUnauthorized(callback: () => void): void {
  _onUnauthorized = callback;
}

/**
 * Store the JWT token in memory after successful login.
 */
export function setToken(token: string): void {
  _token = token;
}

/**
 * Clear the token from memory (logout or 401 response).
 */
export function clearToken(): void {
  _token = null;
}

/**
 * Get the current token (for debugging, rarely needed directly).
 */
export function getToken(): string | null {
  return _token;
}

/**
 * Central API request function.
 *
 * - Automatically attaches Authorization header if token exists
 * - Handles 401 by clearing token and triggering logout redirect
 * - All API calls go through this function for consistency
 */

export async function apiRequest(
  path: string,
  options: RequestInit = {}
): Promise<Response | undefined> {
  // Build headers with Content-Type and optional Authorization
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> || {}),
  };

  // Attach JWT token if we have one
  if (_token) {
    headers["Authorization"] = `Bearer ${_token}`;
  }

  // Make the request
  const response = await fetch(`/api${path}`, {
    ...options,
    headers,
  });

  // Handle 401 Unauthorized - token expired or invalid
  if (response.status === 401) {
    clearToken();

    // Notify the app (AuthContext) to redirect to login
    if (_onUnauthorized) {
      _onUnauthorized();
    }

    return undefined; // Caller should stop processing
  }

  return response;
}